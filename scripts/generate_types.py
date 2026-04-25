"""Generate `web/lib/types.generated.ts` from the Pydantic schemas.

Usage (from project root):

    python scripts/generate_types.py
    # or
    make types

This is the only direction the generator runs: Pydantic is the single source
of truth; the TypeScript file is a derived artifact and should be committed
to git so CI / contributors get type-safety without needing the toolchain.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pydantic2ts import generate_typescript_defs  # noqa: E402

OUTPUT = ROOT / "web" / "lib" / "types.generated.ts"
JSON2TS_BIN = ROOT / "web" / "node_modules" / ".bin" / "json2ts"


def main() -> int:
    if not JSON2TS_BIN.exists():
        print(
            f"❌ json2ts binary not found at {JSON2TS_BIN}\n"
            "   Run `cd web && npm install` first.",
            file=sys.stderr,
        )
        return 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # pydantic2ts wants either a dotted import path OR a filesystem path to a
    # python file. Pass the package's __init__.py so all re-exported models
    # are discovered in one pass.
    generate_typescript_defs(
        module=str(ROOT / "schemas" / "__init__.py"),
        output=str(OUTPUT),
        json2ts_cmd=str(JSON2TS_BIN),
    )

    print(f"✅ Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
