"""Centralized cache TTLs for Streamlit `@st.cache_data`.

Buckets reflect how often the underlying data actually changes, so behavior
stays predictable across pages. Page code should never hardcode `ttl=…`; use
`CACHE_TTL["bucket"]` instead.
"""
from __future__ import annotations

from typing import Final

CACHE_TTL: Final[dict[str, int]] = {
    "quote":         1200,  # 20 min — intraday price (live during market hours)
    "history":       1800,  # 30 min — OHLCV bars
    "sentiment":      600,  # 10 min — market-wide sentiment / indicators
    "market_news":    900,  # 15 min — news feeds
    "fundamentals": 3600,   # 1 hour — slow-moving financials
    "calendar":     3600,   # 1 hour — earnings calendar
    "policy":      86400,   # 1 day  — A-share policy alignment docs
    "db_read":        60,   # 1 min  — Postgres lookups (decisions etc.)
    "static_html": 3600,    # 1 hour — brand intro / decorative HTML
}
