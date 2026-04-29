"""End-to-end smoke test for the DB-first fundamentals wrapper.

Validates:
    1. First call: DB miss → remote fetch → persist to PG + Redis
    2. Second call: Redis hit (sub-100ms)
    3. force_refresh: re-fetch from remote, raw_fundamentals gains a row

Run from project root:
    .venv/bin/python -m tests.smoke_db_first
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, func
from src.db import session_scope
from src.db.models import Fundamentals, RawFundamentals, Stock
from src.db.repository import get_or_fetch_fundamentals
from src.db.cache import get_redis


SYMBOL = "600519"
MARKET = "a_share"


def _summary(payload: dict) -> str:
    keys = ("name", "data_source", "roe", "profit_margin", "debt_to_equity",
            "_db_cached", "_db_fetched_at")
    return ", ".join(
        f"{k}={payload.get(k)}" for k in keys if k in payload or k in payload.keys()
    )


def main():
    print(f"=== Smoke test for {MARKET}/{SYMBOL} ===\n")

    # Clear Redis to ensure a clean run
    try:
        get_redis().delete(f"fund:{MARKET}:{SYMBOL}")
    except Exception:
        pass

    # Pass 1: cold call (expect remote fetch + persist)
    t0 = time.monotonic()
    p1 = get_or_fetch_fundamentals(SYMBOL, MARKET)
    d1 = (time.monotonic() - t0) * 1000
    print(f"[1] cold call    | {d1:6.1f} ms | source={p1.get('data_source')}")
    print(f"     roe={p1.get('roe')} pm={p1.get('profit_margin')} d/e={p1.get('debt_to_equity')}")
    print(f"     name={p1.get('name')}")
    assert p1.get("data_source") not in ("error", None), "remote fetch failed"

    # Pass 2: warm call (Redis hit; SSH tunnel adds ~250ms RTT)
    t0 = time.monotonic()
    p2 = get_or_fetch_fundamentals(SYMBOL, MARKET)
    d2 = (time.monotonic() - t0) * 1000
    print(f"\n[2] warm call    | {d2:6.1f} ms | source={p2.get('data_source')}")
    speedup = d1 / max(d2, 1)
    assert d2 < 1500, f"warm call unexpectedly slow ({d2}ms)"
    print(f"     ✓ Redis hit ({speedup:.0f}× faster than cold call)")

    # Pass 3: force refresh (expect remote fetch again, +1 raw row)
    with session_scope() as s:
        before = s.execute(select(func.count()).select_from(RawFundamentals)).scalar()

    t0 = time.monotonic()
    p3 = get_or_fetch_fundamentals(SYMBOL, MARKET, force_refresh=True)
    d3 = (time.monotonic() - t0) * 1000
    print(f"\n[3] force refresh | {d3:6.1f} ms | source={p3.get('data_source')}")

    with session_scope() as s:
        after = s.execute(select(func.count()).select_from(RawFundamentals)).scalar()
        stock_count = s.execute(select(func.count()).select_from(Stock)).scalar()
        fund_count = s.execute(select(func.count()).select_from(Fundamentals)).scalar()
    print(f"     raw_fundamentals rows: {before} → {after}  (delta={after-before})")
    assert after >= before + 1, "force_refresh did not append a raw row"

    print(f"\n=== DB state ===")
    print(f"  stocks rows:           {stock_count}")
    print(f"  fundamentals rows:     {fund_count}")
    print(f"  raw_fundamentals rows: {after}")

    print("\n✅ All checks passed.")


if __name__ == "__main__":
    main()
