"""Data provider router — selects between Financial Datasets AI and yfinance."""

from src.data.financial_datasets import (
    has_fd_key, fetch_fd_metrics, fetch_fd_line_items,
    fetch_fd_insider_trades, fetch_fd_news,
)


def get_enhanced_fundamentals(
    symbol: str, market: str, base_fundamentals: dict, fd_api_key: str = ""
) -> dict:
    """Merge yfinance fundamentals with FD data when available (US only)."""
    if market != "us" or not has_fd_key(fd_api_key):
        return base_fundamentals
    fd = fetch_fd_metrics(symbol, fd_api_key)
    if not fd:
        return base_fundamentals
    merged = {**base_fundamentals}
    for k, v in fd.items():
        if k != "_fd_raw" and v is not None:
            merged[k] = v
    merged["_fd_raw"] = fd.get("_fd_raw", {})
    merged["_data_source"] = "financial_datasets"
    return merged


def get_line_items(
    symbol: str, market: str, items: list[str], fd_api_key: str = ""
) -> dict:
    """Fetch line items from FD (US only). Returns {} if unavailable."""
    if market != "us" or not has_fd_key(fd_api_key):
        return {}
    return fetch_fd_line_items(symbol, items, fd_api_key)


def get_insider_trades(symbol: str, market: str, fd_api_key: str = "") -> list[dict]:
    """Fetch insider trades from FD (US only). Returns [] if unavailable."""
    if market != "us" or not has_fd_key(fd_api_key):
        return []
    return fetch_fd_insider_trades(symbol, fd_api_key)


def get_news_for_analysts(
    symbol: str, market: str, fd_api_key: str = "", limit: int = 10
) -> list[dict]:
    """Get news — FD for US with key, else existing news module."""
    if market == "us" and has_fd_key(fd_api_key):
        return fetch_fd_news(symbol, fd_api_key, limit)
    try:
        from src.data.news import fetch_stock_news
        return fetch_stock_news(symbol, market, limit)
    except Exception:
        return []


def data_source_label(market: str, fd_api_key: str = "") -> str:
    """Return human-readable data source label for UI."""
    if market == "us" and has_fd_key(fd_api_key):
        return "Financial Datasets AI"
    return "yfinance"
