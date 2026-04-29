"""Batch ingest fundamentals into Postgres/Redis via DB-first repository.

Usage:
    python scripts/batch_ingest.py            # ingest config.yaml watchlist
    python scripts/batch_ingest.py --force    # bypass freshness window, re-fetch all
    python scripts/batch_ingest.py --file path/to/symbols.json

Symbols file format (JSON):
    [{"symbol": "AAPL", "market": "us"}, ...]

Behavior:
    - Sequential calls (avoids upstream rate limits)
    - Per-symbol logging: ok / cached / fail
    - Records audit trail in fetch_audit table
    - Continues on failure; final summary at end
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.db.repository import get_or_fetch_fundamentals  # noqa: E402
from src.db.session import db_available  # noqa: E402
from src.db.cache import cache_available  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("batch_ingest")


@dataclass(frozen=True)
class Target:
    symbol: str
    market: str
    name: str = ""


@dataclass
class Result:
    target: Target
    status: str  # "ok" | "empty" | "fail"
    elapsed_ms: int
    error: str = ""


def load_watchlist(config_path: Path) -> list[Target]:
    cfg = yaml.safe_load(config_path.read_text())
    wl = cfg.get("watchlist", {}) or {}
    out: list[Target] = []
    for market, items in wl.items():
        for item in items or []:
            out.append(Target(symbol=item["symbol"], market=market, name=item.get("name", "")))
    return out


def load_from_file(path: Path) -> list[Target]:
    raw = json.loads(path.read_text())
    return [Target(symbol=r["symbol"], market=r["market"], name=r.get("name", "")) for r in raw]


def ingest_one(target: Target, force: bool) -> Result:
    started = time.perf_counter()
    try:
        data = get_or_fetch_fundamentals(target.symbol, target.market, force_refresh=force)
        elapsed = int((time.perf_counter() - started) * 1000)
        if not data:
            return Result(target, "empty", elapsed)
        return Result(target, "ok", elapsed)
    except Exception as exc:  # noqa: BLE001 — top-level batch driver
        elapsed = int((time.perf_counter() - started) * 1000)
        return Result(target, "fail", elapsed, error=repr(exc))


def run(targets: Iterable[Target], force: bool, sleep_ms: int) -> list[Result]:
    results: list[Result] = []
    for i, t in enumerate(targets, start=1):
        r = ingest_one(t, force)
        results.append(r)
        marker = {"ok": "✓", "empty": "∅", "fail": "✗"}[r.status]
        log.info("[%d] %s %s/%s (%dms)%s", i, marker, t.market, t.symbol,
                 r.elapsed_ms, f" — {r.error}" if r.error else "")
        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000.0)
    return results


def summarize(results: list[Result]) -> int:
    counts = {"ok": 0, "empty": 0, "fail": 0}
    for r in results:
        counts[r.status] += 1
    total = len(results)
    log.info("=" * 50)
    log.info("Summary: %d total | ok=%d empty=%d fail=%d",
             total, counts["ok"], counts["empty"], counts["fail"])
    if counts["fail"]:
        log.info("Failures:")
        for r in results:
            if r.status == "fail":
                log.info("  %s/%s: %s", r.target.market, r.target.symbol, r.error)
    return 0 if counts["fail"] == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--file", type=Path, help="JSON file of {symbol,market} entries")
    p.add_argument("--force", action="store_true", help="bypass DB freshness window")
    p.add_argument("--sleep-ms", type=int, default=200, help="delay between calls")
    args = p.parse_args()

    if not db_available():
        log.error("DB not reachable. Check SSH tunnel.")
        return 2
    if not cache_available():
        log.warning("Redis not reachable; continuing (will use Postgres only)")

    if args.file:
        targets = load_from_file(args.file)
        src = str(args.file)
    else:
        targets = load_watchlist(ROOT / "config.yaml")
        src = "config.yaml watchlist"

    log.info("Loaded %d symbols from %s (force=%s)", len(targets), src, args.force)
    results = run(targets, args.force, args.sleep_ms)
    return summarize(results)


if __name__ == "__main__":
    sys.exit(main())
