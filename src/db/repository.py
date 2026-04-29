"""Repository layer — DB-first wrappers around remote fetchers.

The wrapper composes 3 layers (Redis hot cache → Postgres → remote fetch),
preserving the existing fetcher contracts so call sites need at most a one-line change.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .cache import cache_available, get_redis
from .models import Fundamentals, RawFundamentals, Stock
from .session import db_available, session_scope

logger = logging.getLogger(__name__)

REDIS_TTL_SECONDS = 300                         # 5 min hot cache
DB_FRESH_HOURS = int(os.environ.get("DB_FRESH_HOURS", "24"))


# ----------------------------------------------------------------------------
# stock master
# ----------------------------------------------------------------------------

def get_or_create_stock(symbol: str, market: str, name: Optional[str] = None) -> int:
    """Return stock.id, inserting a row if it doesn't exist."""
    with session_scope() as s:
        existing = s.execute(
            select(Stock).where(Stock.symbol == symbol, Stock.market == market, Stock.is_active == True)  # noqa: E712
        ).scalar_one_or_none()
        if existing:
            return existing.id

        stock = Stock(symbol=symbol, market=market, name=name or symbol)
        s.add(stock)
        s.flush()
        return stock.id


# ----------------------------------------------------------------------------
# fundamentals: source identification
# ----------------------------------------------------------------------------

def _identify_primary_source(market: str, data_source_field: str) -> str:
    """Map the existing fetcher's `data_source` string to a registered source code.

    The legacy fetcher merges multiple sources internally and reports composite labels
    like 'tencent+sina'. For DB writes we tag the row with the source that contributed
    the bulk of the *fundamental* ratios (the rest are price/PE/PB which we don't store
    in fundamentals).

    Future refactor: split the fetcher to return per-source data → write one row per source.
    """
    s = (data_source_field or "").lower()
    if "yfinance" in s:
        return "yfinance"
    if "sina" in s:
        return "sina"
    if "eastmoney" in s:
        return "eastmoney"
    if "tencent" in s and market == "a_share":
        return "sina"           # A-share fundamentals always go through sina
    if "tencent" in s:
        return "eastmoney"      # HK/US fundamentals come through eastmoney
    # Fallback: use the most-likely source per market
    return {"a_share": "sina", "hk": "eastmoney", "us": "yfinance"}.get(market, "tencent")


# ----------------------------------------------------------------------------
# fundamentals: read path
# ----------------------------------------------------------------------------

def _redis_key_fund(symbol: str, market: str) -> str:
    return f"fund:{market}:{symbol}"


def _read_redis_fundamentals(symbol: str, market: str) -> Optional[dict]:
    """Read from Redis with a single round-trip (no ping pre-check)."""
    try:
        raw = get_redis().get(_redis_key_fund(symbol, market))
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.debug("Redis read failed: %s", e)
    return None


def _write_redis_fundamentals(symbol: str, market: str, payload: dict) -> None:
    try:
        get_redis().setex(_redis_key_fund(symbol, market), REDIS_TTL_SECONDS,
                          json.dumps(payload, default=str))
    except Exception as e:
        logger.debug("Redis write failed: %s", e)


def _read_db_fundamentals(symbol: str, market: str, max_age_hours: int) -> Optional[dict]:
    """Read latest fundamentals from DB. Returns dict in the same format as the legacy fetcher,
    or None if no fresh data is available."""
    threshold = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    with session_scope() as s:
        stock = s.execute(
            select(Stock).where(
                Stock.symbol == symbol, Stock.market == market, Stock.is_active == True  # noqa: E712
            )
        ).scalar_one_or_none()
        if not stock:
            return None

        # Most recent raw_payload (we re-hydrate from raw to avoid lossy round-trips)
        latest_raw = s.execute(
            select(RawFundamentals)
            .where(RawFundamentals.stock_id == stock.id, RawFundamentals.fetched_at >= threshold)
            .order_by(RawFundamentals.fetched_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if latest_raw and isinstance(latest_raw.raw_payload, dict):
            payload = dict(latest_raw.raw_payload)
            payload["_db_cached"] = True
            payload["_db_fetched_at"] = latest_raw.fetched_at.isoformat()
            return payload

    return None


# ----------------------------------------------------------------------------
# fundamentals: write path
# ----------------------------------------------------------------------------

def _safe_decimal(value):
    """Convert any number-like value to Decimal-safe form, or None."""
    if value is None:
        return None
    try:
        f = float(value)
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _write_db_fundamentals(stock_id: int, market: str, payload: dict) -> None:
    """Persist a fetched payload to raw_fundamentals + fundamentals.

    Idempotent on (stock_id, period, period_type, source) via ON CONFLICT.
    """
    source = _identify_primary_source(market, payload.get("data_source", ""))
    period = date.today()
    period_type = "ttm"

    with session_scope() as s:
        # 1) immutable raw layer (always insert a new row)
        raw = RawFundamentals(
            stock_id=stock_id,
            source=source,
            period=period,
            period_type=period_type,
            raw_payload=payload,
        )
        s.add(raw)

        # 2) parsed/standardized layer (upsert on unique key)
        stmt = pg_insert(Fundamentals).values(
            stock_id=stock_id,
            period=period,
            period_type=period_type,
            source=source,
            roe=_safe_decimal(payload.get("roe")),
            net_margin=_safe_decimal(payload.get("profit_margin")),
            gross_margin=_safe_decimal(payload.get("gross_margin")),
            operating_margin=_safe_decimal(payload.get("operating_margin")),
            debt_to_equity=_safe_decimal(payload.get("debt_to_equity")),
            current_ratio=_safe_decimal(payload.get("current_ratio")),
            quick_ratio=_safe_decimal(payload.get("quick_ratio")),
            revenue_growth=_safe_decimal(payload.get("revenue_growth")),
            net_income_growth=_safe_decimal(payload.get("earnings_growth")),
            operating_cash_flow=_safe_decimal(payload.get("operating_cashflow")),
            free_cash_flow=_safe_decimal(payload.get("free_cashflow")),
            revenue=_safe_decimal(payload.get("total_revenue")),
            quality="single_source",
            confidence=70 if source != "merged" else 50,
            fetched_at=datetime.now(timezone.utc),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fund",
            set_={
                "roe": stmt.excluded.roe,
                "net_margin": stmt.excluded.net_margin,
                "gross_margin": stmt.excluded.gross_margin,
                "operating_margin": stmt.excluded.operating_margin,
                "debt_to_equity": stmt.excluded.debt_to_equity,
                "current_ratio": stmt.excluded.current_ratio,
                "quick_ratio": stmt.excluded.quick_ratio,
                "revenue_growth": stmt.excluded.revenue_growth,
                "net_income_growth": stmt.excluded.net_income_growth,
                "operating_cash_flow": stmt.excluded.operating_cash_flow,
                "free_cash_flow": stmt.excluded.free_cash_flow,
                "revenue": stmt.excluded.revenue,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        s.execute(stmt)


# ----------------------------------------------------------------------------
# Public DB-first wrapper
# ----------------------------------------------------------------------------

def get_or_fetch_fundamentals(symbol: str, market: str,
                              force_refresh: bool = False) -> dict:
    """DB-first version of fetch_fundamentals.

    Sequence: Redis → Postgres (≤ DB_FRESH_HOURS old) → original remote fetch.
    Falls back gracefully to the original fetcher if any layer is unavailable.
    """
    from src.data.financial import fetch_fundamentals as _remote_fetch

    if force_refresh:
        return _remote_fetch_and_persist(symbol, market, _remote_fetch)

    # Layer 1: Redis
    cached = _read_redis_fundamentals(symbol, market)
    if cached:
        return cached

    # Layer 2: Postgres (only if DB reachable)
    if db_available():
        db_data = _read_db_fundamentals(symbol, market, DB_FRESH_HOURS)
        if db_data:
            _write_redis_fundamentals(symbol, market, db_data)
            return db_data

    # Layer 3: remote fetch + persist
    return _remote_fetch_and_persist(symbol, market, _remote_fetch)


def _remote_fetch_and_persist(symbol: str, market: str, fetch_fn) -> dict:
    started = time.monotonic()
    payload = fetch_fn(symbol, market)
    duration_ms = int((time.monotonic() - started) * 1000)

    if not isinstance(payload, dict) or payload.get("data_source") == "error":
        return payload  # nothing to persist; fall through

    if not db_available():
        return payload

    try:
        stock_id = get_or_create_stock(symbol, market, name=payload.get("name"))
        _write_db_fundamentals(stock_id, market, payload)
        _write_redis_fundamentals(symbol, market, payload)
        logger.info("persisted fundamentals %s/%s in %dms", market, symbol, duration_ms)
    except Exception as e:
        logger.warning("DB persistence failed for %s/%s: %s", market, symbol, e)
        # Don't let DB errors break the user-facing flow

    return payload
