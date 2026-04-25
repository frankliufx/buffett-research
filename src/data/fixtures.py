"""Offline fixture loader.

Sandbox / CI / demo mode. Activated when env `USE_FIXTURES=1` is set.

Each network-bound fetcher in `src/data/*` checks `is_fixture_mode()` at
the top and short-circuits to fixture data when on. This means:
- Sandbox demo: 4 cards render fully populated (proven below)
- CI tests: deterministic, network-free, fast
- Production: env unset → fetchers go through real source chain

Fixture file: `data/fixtures/cn_a_share.json` (5 stocks, hand-curated).
"""

from __future__ import annotations

import json
import logging
import os
import random
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures"


def is_fixture_mode() -> bool:
    """True when env `USE_FIXTURES=1` is set."""
    return os.getenv("USE_FIXTURES", "").strip() in ("1", "true", "True", "yes")


@lru_cache(maxsize=1)
def _load_a_share() -> dict:
    path = _FIXTURES_DIR / "cn_a_share.json"
    if not path.exists():
        logger.warning("fixture file missing: %s", path)
        return {"stocks": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("fixture load failed: %s", e)
        return {"stocks": {}}


def _normalize_code(symbol: str) -> str:
    """Strip prefixes/suffixes → 6-digit A-share code."""
    s = symbol.lower().replace("sh", "").replace("sz", "").split(".")[0].strip()
    return s.zfill(6)[-6:]


def get_a_share_stock(symbol: str) -> Optional[dict]:
    """Lookup a single A-share fixture entry by symbol. Returns None if not curated."""
    code = _normalize_code(symbol)
    return _load_a_share().get("stocks", {}).get(code)


def all_a_share_codes() -> list[str]:
    """List all curated A-share codes (used to seed the concept_map fixture)."""
    return list(_load_a_share().get("stocks", {}).keys())


# ── Helpers used by the patched fetchers ─────────────────────────────────────


def _seeded_history(code: str, days: int, target_5d_sum: Optional[float],
                    target_20d_sum: Optional[float]) -> list[dict]:
    """Generate a plausible daily-history series whose 5d / 20d sums roughly
    match the curated targets. Deterministic from the code (so the chart
    looks the same on every reload)."""
    rng = random.Random(int(code))
    today = date.today()

    # Distribute 20d total across 20 days with small noise
    series: list[float] = []
    if target_20d_sum is not None and days >= 20:
        avg = target_20d_sum / 20
        for _ in range(20):
            series.append(avg + rng.gauss(0, abs(avg) * 0.6))
        # Adjust so last 5 sum approximates target_5d_sum
        if target_5d_sum is not None:
            current_5d = sum(series[-5:])
            delta = (target_5d_sum - current_5d) / 5
            series[-5:] = [v + delta for v in series[-5:]]
    elif target_5d_sum is not None:
        avg = target_5d_sum / 5
        series = [avg + rng.gauss(0, abs(avg) * 0.6) for _ in range(5)]
    else:
        series = [rng.gauss(0, 1e7) for _ in range(min(20, days))]

    # Pad earlier days with smaller noise so we have `days` total
    while len(series) < days:
        series.insert(0, rng.gauss(0, abs(series[0]) * 0.4 if series else 5e6))
    series = series[-days:]

    out: list[dict] = []
    for i, val in enumerate(series):
        d = today - timedelta(days=days - 1 - i)
        out.append({"date": d.isoformat(), "net_inflow_yuan": round(val)})
    return out


def synthesize_capital_history(code: str, days: int = 30) -> tuple[list[dict], list[dict]]:
    """Return (northbound_history, main_history) lists shaped to land at
    the curated 5d/20d totals. Used by cn_capital_flow fixture path."""
    fx = get_a_share_stock(code) or {}
    cap = fx.get("capital_flow", {}) or {}
    nb = _seeded_history(
        code,
        days,
        cap.get("northbound_5d_yuan"),
        cap.get("northbound_20d_yuan"),
    )
    main = _seeded_history(
        code + "0",  # different seed
        days,
        cap.get("main_5d_yuan"),
        None,
    )
    return nb, main


def synthesize_price_history(code: str, days: int = 90) -> Optional[Any]:
    """Build a pandas DataFrame with OHLCV around the curated quote price.

    Returns None if pandas isn't available (lets caller fall back to None
    gracefully — fragments handle empty df).
    """
    try:
        import pandas as pd
    except ImportError:
        return None
    fx = get_a_share_stock(code) or {}
    quote = fx.get("quote", {})
    last = float(quote.get("price", 100.0))
    if last <= 0:
        last = 100.0

    rng = random.Random(hash(code) & 0xFFFFFFFF)
    today = date.today()
    rows = []
    price = last * 0.85  # start ~15% below current → trend up
    for i in range(days):
        # Random walk with slight upward drift
        chg = rng.gauss(0.0015, 0.018)
        price *= (1 + chg)
        op = price * (1 + rng.gauss(0, 0.005))
        cl = price
        hi = max(op, cl) * (1 + abs(rng.gauss(0, 0.006)))
        lo = min(op, cl) * (1 - abs(rng.gauss(0, 0.006)))
        vol = int(abs(rng.gauss(2e7, 5e6)))
        d = today - timedelta(days=days - 1 - i)
        rows.append({
            "Open": round(op, 2),
            "High": round(hi, 2),
            "Low": round(lo, 2),
            "Close": round(cl, 2),
            "Volume": vol,
        })
    # Anchor the last close to the curated price for visual consistency
    rows[-1]["Close"] = round(last, 2)
    df = pd.DataFrame(rows)
    df.index = pd.to_datetime([today - timedelta(days=days - 1 - i) for i in range(days)])
    return df
