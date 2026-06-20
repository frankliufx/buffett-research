"""Stock universe: CSI300 (AKShare) + S&P500 top-100 (static list)."""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple

_logger = logging.getLogger(__name__)

StockEntry = Tuple[str, str]  # (ticker, name)

# Top-100 S&P 500 by market cap (static, updated 2026-06)
_SP500_TOP100: List[StockEntry] = [
    ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "NVIDIA"),
    ("GOOGL", "Alphabet"), ("AMZN", "Amazon"), ("META", "Meta Platforms"),
    ("TSLA", "Tesla"), ("BRK-B", "Berkshire Hathaway"), ("LLY", "Eli Lilly"),
    ("V", "Visa"), ("JPM", "JPMorgan Chase"), ("UNH", "UnitedHealth"),
    ("XOM", "Exxon Mobil"), ("MA", "Mastercard"), ("JNJ", "Johnson & Johnson"),
    ("PG", "Procter & Gamble"), ("HD", "Home Depot"), ("AVGO", "Broadcom"),
    ("CVX", "Chevron"), ("MRK", "Merck"), ("ABBV", "AbbVie"),
    ("PEP", "PepsiCo"), ("KO", "Coca-Cola"), ("COST", "Costco"),
    ("WMT", "Walmart"), ("BAC", "Bank of America"), ("MCD", "McDonald's"),
    ("CRM", "Salesforce"), ("ACN", "Accenture"), ("TMO", "Thermo Fisher"),
    ("ABT", "Abbott"), ("CSCO", "Cisco"), ("WFC", "Wells Fargo"),
    ("LIN", "Linde"), ("DHR", "Danaher"), ("TXN", "Texas Instruments"),
    ("NEE", "NextEra Energy"), ("PM", "Philip Morris"), ("RTX", "RTX Corp"),
    ("AMGN", "Amgen"), ("UPS", "UPS"), ("INTU", "Intuit"),
    ("HON", "Honeywell"), ("CAT", "Caterpillar"), ("IBM", "IBM"),
    ("SPGI", "S&P Global"), ("GS", "Goldman Sachs"), ("BKNG", "Booking"),
    ("MS", "Morgan Stanley"), ("LOW", "Lowe's"), ("DE", "Deere"),
    ("AXP", "American Express"), ("BLK", "BlackRock"), ("ELV", "Elevance"),
    ("MDLZ", "Mondelez"), ("ADI", "Analog Devices"), ("GILD", "Gilead"),
    ("PLD", "Prologis"), ("SYK", "Stryker"), ("ADP", "ADP"),
    ("REGN", "Regeneron"), ("VRTX", "Vertex Pharma"), ("PANW", "Palo Alto"),
    ("SBUX", "Starbucks"), ("LRCX", "Lam Research"), ("CI", "Cigna"),
    ("KLAC", "KLA Corp"), ("MU", "Micron"), ("SNPS", "Synopsys"),
    ("MCO", "Moody's"), ("SHW", "Sherwin-Williams"), ("CME", "CME Group"),
    ("SO", "Southern Co"), ("FI", "Fiserv"), ("APH", "Amphenol"),
    ("INTC", "Intel"), ("AON", "Aon"), ("ICE", "ICE"),
    ("GE", "GE Aerospace"), ("USB", "US Bancorp"), ("TJX", "TJX"),
    ("MMC", "Marsh & McLennan"), ("HCA", "HCA Healthcare"), ("PGR", "Progressive"),
    ("NOC", "Northrop Grumman"), ("ITW", "Illinois Tool Works"), ("ETN", "Eaton"),
    ("EMR", "Emerson Electric"), ("NSC", "Norfolk Southern"), ("FDX", "FedEx"),
    ("FCX", "Freeport-McMoRan"), ("PSA", "Public Storage"), ("NKE", "Nike"),
    ("ORCL", "Oracle"), ("AMAT", "Applied Materials"), ("NFLX", "Netflix"),
    ("QCOM", "Qualcomm"), ("TGT", "Target"), ("DUK", "Duke Energy"),
    ("ROP", "Roper Technologies"), ("AJG", "Arthur J. Gallagher"),
]


def get_csi300_tickers() -> List[StockEntry]:
    """Fetch CSI300 components via AKShare.

    Returns list of (ticker, name) where ticker uses sh/sz prefix.
    Falls back to empty list on error.
    """
    try:
        import akshare as ak
        df = ak.index_stock_cons_csindex(symbol="000300")
        result: List[StockEntry] = []
        for _, row in df.iterrows():
            code = str(row["成分券代码"]).zfill(6)
            name = str(row["成分券名称"])
            prefix = "sh" if code.startswith(("6", "9")) else "sz"
            result.append((f"{prefix}{code}", name))
        return result
    except Exception as exc:
        _logger.warning("Failed to fetch CSI300 from AKShare: %s", exc)
        return []


def get_sp500_tickers() -> List[StockEntry]:
    """Return S&P500 top-100 static list."""
    return list(_SP500_TOP100)


def get_full_universe() -> List[StockEntry]:
    """Combine CSI300 + S&P500 top-100."""
    return get_csi300_tickers() + get_sp500_tickers()


def fetch_basic_fundamentals(symbol: str) -> Dict[str, Any]:
    """Fetch key fundamentals for a single stock.

    For US stocks: yfinance Ticker.info
    For A-shares (sh/sz prefix): akshare stock_zh_a_spot_em (real-time quote)
    Returns empty dict on any error.
    """
    try:
        if symbol.startswith(("sh", "sz")):
            return _fetch_ashare_fundamentals(symbol)
        return _fetch_us_fundamentals(symbol)
    except Exception as exc:
        _logger.warning("Failed to fetch fundamentals for %s: %s", symbol, exc)
        return {}


def _fetch_us_fundamentals(symbol: str) -> Dict[str, Any]:
    """Fetch key fundamentals for a US stock via yfinance.

    Field mapping: returnOnEquity is a ratio (0.18 = 18%), NOT a percentage.
    grossMargins is also a ratio. revenueGrowth is a ratio.
    """
    import yfinance as yf
    info = yf.Ticker(symbol).info
    return {
        "pe": _safe_float(info.get("trailingPE")),
        "pb": _safe_float(info.get("priceToBook")),
        "roe": _safe_float(info.get("returnOnEquity")),
        "gross_margin": _safe_float(info.get("grossMargins")),
        "debt_to_equity": _safe_float(info.get("debtToEquity")),
        "revenue_growth": _safe_float(info.get("revenueGrowth")),
        "fcf": _safe_float(info.get("freeCashflow")),
        "market_cap": _safe_float(info.get("marketCap")),
    }


def _fetch_ashare_fundamentals(symbol: str) -> Dict[str, Any]:
    """Limited A-share data via AKShare real-time quote (PE/PB/market cap)."""
    import akshare as ak
    code = symbol[2:]  # strip sh/sz prefix
    df = ak.stock_zh_a_spot_em()
    row = df[df["代码"] == code]
    if row.empty:
        return {}
    r = row.iloc[0]
    return {
        "pe": _safe_float(r.get("市盈率-动态")),
        "pb": _safe_float(r.get("市净率")),
        "roe": None,
        "gross_margin": None,
        "debt_to_equity": None,
        "revenue_growth": None,
        "fcf": None,
        "market_cap": _safe_float(r.get("总市值")),
    }


def _safe_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
