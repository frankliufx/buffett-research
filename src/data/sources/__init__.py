"""Multi-source data chain.

Architecture: stable-first / scrape-last. Fetchers in `src/data/price.py`
and `src/data/financial.py` consult this chain BEFORE falling back to
their existing yfinance/eastmoney/sina logic. Production gets richer,
more stable data; sandbox/CI hits the fixture short-circuit instead.

Each source implements a small Protocol so adding a new provider is a
10-line file. Failures are silent and chained (one source down → next).

Order priority is set per-fetcher, defaulting to:

    1. SEC EDGAR  — official US filings (no key, ⭐⭐⭐⭐⭐)
    2. Stooq      — global OHLCV (no key, ⭐⭐⭐⭐⭐)
    3. TuShare    — A-share comprehensive (token, ⭐⭐⭐⭐⭐)
    4. (existing yfinance / eastmoney / sina fallbacks)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


class QuoteSource(Protocol):
    name: str

    def supports(self, symbol: str, market: str) -> bool: ...
    def fetch_quote(self, symbol: str, market: str) -> Optional[dict]: ...


class HistorySource(Protocol):
    name: str

    def supports(self, symbol: str, market: str) -> bool: ...
    def fetch_history(self, symbol: str, market: str, days: int) -> Optional[Any]: ...


class FundamentalsSource(Protocol):
    name: str

    def supports(self, symbol: str, market: str) -> bool: ...
    def fetch_fundamentals(self, symbol: str, market: str) -> Optional[dict]: ...


def _try_chain(sources: list, fn_name: str, *args, **kwargs):
    """Walk sources in order; return the first non-empty result.

    A source's `supports(...)` must return True before we attempt its
    fetch. Any exception in a source is caught and logged; we move on.
    """
    for src in sources:
        try:
            if not src.supports(*args[:2]):  # (symbol, market)
                continue
            res = getattr(src, fn_name)(*args, **kwargs)
            if res:
                logger.debug("source hit: %s for %s", src.name, args)
                return res
        except Exception as e:
            logger.warning("source %s failed: %s", getattr(src, "name", "?"), e)
    return None


def _build_quote_sources() -> list[QuoteSource]:
    out: list[Any] = []
    try:
        from src.data.sources.stooq import StooqSource
        out.append(StooqSource())
    except Exception as e:
        logger.warning("stooq unavailable: %s", e)
    try:
        from src.data.sources.tushare import TushareSource
        ts = TushareSource()
        if ts.is_configured():
            out.append(ts)
    except Exception as e:
        logger.warning("tushare unavailable: %s", e)
    return out


def _build_fundamentals_sources() -> list[FundamentalsSource]:
    out: list[Any] = []
    try:
        from src.data.sources.sec_edgar import SecEdgarSource
        out.append(SecEdgarSource())
    except Exception as e:
        logger.warning("sec_edgar unavailable: %s", e)
    try:
        from src.data.sources.tushare import TushareSource
        ts = TushareSource()
        if ts.is_configured():
            out.append(ts)
    except Exception as e:
        logger.warning("tushare unavailable: %s", e)
    return out


def _build_history_sources() -> list[HistorySource]:
    out: list[Any] = []
    try:
        from src.data.sources.stooq import StooqSource
        out.append(StooqSource())
    except Exception as e:
        logger.warning("stooq unavailable: %s", e)
    try:
        from src.data.sources.tushare import TushareSource
        ts = TushareSource()
        if ts.is_configured():
            out.append(ts)
    except Exception as e:
        logger.warning("tushare unavailable: %s", e)
    return out


# Lazy build — sources are constructed on first call.
_quote_sources: Optional[list] = None
_fundamentals_sources: Optional[list] = None
_history_sources: Optional[list] = None


def chain_quote(symbol: str, market: str) -> Optional[dict]:
    global _quote_sources
    if _quote_sources is None:
        _quote_sources = _build_quote_sources()
    return _try_chain(_quote_sources, "fetch_quote", symbol, market)


def chain_fundamentals(symbol: str, market: str) -> Optional[dict]:
    global _fundamentals_sources
    if _fundamentals_sources is None:
        _fundamentals_sources = _build_fundamentals_sources()
    return _try_chain(_fundamentals_sources, "fetch_fundamentals", symbol, market)


def chain_history(symbol: str, market: str, days: int = 250):
    global _history_sources
    if _history_sources is None:
        _history_sources = _build_history_sources()
    return _try_chain(_history_sources, "fetch_history", symbol, market, days)
