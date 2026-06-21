"""Financial Datasets AI client — US stocks only, requires API key."""

import os
import httpx
from typing import Optional

BASE_URL = "https://api.financialdatasets.ai"
_CACHE: dict = {}


def _get_key(api_key: str = "") -> str:
    return api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY", "")


def has_fd_key(api_key: str = "") -> bool:
    return bool(_get_key(api_key))


def _get(path: str, params: dict, api_key: str) -> dict:
    cache_key = (path, str(sorted(params.items())))
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    headers = {"X-API-KEY": api_key}
    try:
        r = httpx.get(f"{BASE_URL}{path}", params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        _CACHE[cache_key] = data
        return data
    except Exception:
        return {}


def fetch_fd_metrics(symbol: str, api_key: str) -> dict:
    """Fetch financial metrics. Returns dict with same keys as fetch_fundamentals() where possible."""
    data = _get("/financial-metrics/", {"ticker": symbol, "period": "ttm", "limit": 1}, api_key)
    items = data.get("financial_metrics") or []
    if not items:
        return {}
    m = items[0]
    return {
        "pe_ratio": m.get("price_to_earnings_ratio"),
        "pb_ratio": m.get("price_to_book_ratio"),
        "roe": m.get("return_on_equity"),
        "roa": m.get("return_on_assets"),
        "profit_margin": m.get("net_margin"),
        "gross_margin": m.get("gross_margin"),
        "operating_margin": m.get("operating_margin"),
        "debt_to_equity": m.get("debt_to_equity"),
        "current_ratio": m.get("current_ratio"),
        "revenue_growth": m.get("revenue_growth"),
        "earnings_growth": m.get("earnings_per_share_growth"),
        "free_cashflow_yield": m.get("free_cash_flow_yield"),
        "price_to_fcf": m.get("price_to_free_cash_flow_ratio"),
        "peg_ratio": m.get("price_earnings_to_growth_ratio"),
        "roic": m.get("return_on_invested_capital"),
        "dividend_yield": m.get("dividend_yield"),
        "market_cap": m.get("market_cap"),
        "_fd_raw": m,
    }


def fetch_fd_line_items(symbol: str, items: list[str], api_key: str) -> dict:
    """Fetch specific financial statement line items. Returns most recent values keyed by item name."""
    data = _get(
        "/financials/search/line-items/",
        {"ticker": symbol, "line_items": ",".join(items), "period": "annual", "limit": 4},
        api_key,
    )
    results = data.get("search_results") or []
    out: dict = {}
    for r in results:
        name = r.get("line_item")
        value = r.get("value")
        if name and name not in out:
            out[name] = value
    return out


def fetch_fd_insider_trades(symbol: str, api_key: str) -> list[dict]:
    """Fetch recent insider trades."""
    data = _get("/insider-trades/", {"ticker": symbol, "limit": 20}, api_key)
    return data.get("insider_trades") or []


def fetch_fd_news(symbol: str, api_key: str, limit: int = 10) -> list[dict]:
    """Fetch company news articles."""
    data = _get("/news/", {"ticker": symbol, "limit": limit}, api_key)
    articles = data.get("news") or []
    return [
        {
            "title": a.get("title", ""),
            "source": a.get("source", ""),
            "time": a.get("published_at", ""),
            "summary": a.get("summary", ""),
            "sentiment": a.get("sentiment", ""),
        }
        for a in articles
    ]
