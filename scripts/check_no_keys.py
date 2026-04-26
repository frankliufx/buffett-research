"""Pre-commit / CI guard against committing real API keys.

Scans every file staged for commit (or, when run standalone, every tracked
file) for patterns that look like real provider keys. Exits non-zero on any
hit. Hook this into git pre-commit:

    # .git/hooks/pre-commit (excerpt)
    python scripts/check_no_keys.py --staged || exit 1

The patterns below are conservative: Anthropic / OpenAI / OpenRouter / DeepSeek
share recognizable prefixes. Adjust as needed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    # Anthropic — sk-ant-…  (long base64-like)
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{40,}"), "Anthropic"),
    # OpenAI / OpenRouter — sk-… / sk-or-…  (also long)
    (re.compile(r"sk-or-[A-Za-z0-9_-]{20,}"), "OpenRouter"),
    (re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}"), "OpenAI project key"),
    # Generic OpenAI-compat (≥48 chars after sk-)
    (re.compile(r"sk-[A-Za-z0-9]{48,}"), "OpenAI / generic"),
    # DeepSeek — 32-hex tokens commonly look like md5
    # (skipped — too false-positive-prone)
]

# Files we *expect* to contain example/placeholder keys (don't fail on these)
ALLOWED = {
    "config.example.yaml",
    "users.yaml.example",
    "scripts/check_no_keys.py",
    "src/keyring.py",
    ".streamlit/secrets.toml.example",
}

# Safe prefixes / explicit examples
SAFE_TOKENS = {
    "sk-ant-EXAMPLE",
    "sk-ant-your-key-here",
    "sk-EXAMPLE",
    "sk-or-EXAMPLE",
    "sk-or-your-key-here",
    "sk-proj-EXAMPLE",
}


def _is_safe(text: str) -> bool:
    s = text.strip()
    return any(s.startswith(prefix) for prefix in SAFE_TOKENS)


def _files(staged: bool) -> list[Path]:
    if staged:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], text=True,
        )
        return [Path(line) for line in out.splitlines() if line]
    out = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(line) for line in out.splitlines() if line]


def scan(files: list[Path]) -> list[tuple[Path, int, str, str]]:
    hits: list[tuple[Path, int, str, str]] = []
    for f in files:
        if str(f) in ALLOWED:
            continue
        if not f.exists() or f.is_dir():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for pat, label in PATTERNS:
                m = pat.search(line)
                if not m or _is_safe(m.group()):
                    continue
                hits.append((f, line_no, label, m.group()[:18] + "…"))
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true",
                         help="Only scan files staged for commit (use in pre-commit hook)")
    args = parser.parse_args(argv)

    files = _files(staged=args.staged)
    hits = scan(files)
    if not hits:
        print(f"✓ no API key leaks found in {len(files)} file(s)")
        return 0
    print(f"✗ Possible API key(s) committed in {len(hits)} place(s):")
    for f, ln, label, snippet in hits:
        print(f"  {f}:{ln}  [{label}]  {snippet}")
    print("\nIf this is a real key: rotate it immediately at the provider, then")
    print("remove from history (git rebase / BFG) before pushing.")
    print("If this is an example/placeholder: add it to SAFE_TOKENS in scripts/check_no_keys.py.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
