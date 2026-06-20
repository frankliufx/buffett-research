"""Stock universe: CSI300 (AKShare) + S&P500 top-100 (static list)."""

from __future__ import annotations
from typing import List, Tuple

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
            result.append(("{prefix}{code}".format(prefix=prefix, code=code), name))
        return result
    except Exception:
        return []


def get_sp500_tickers() -> List[StockEntry]:
    """Return S&P500 top-100 static list."""
    return list(_SP500_TOP100)


def get_full_universe() -> List[StockEntry]:
    """Combine CSI300 + S&P500 top-100."""
    return get_csi300_tickers() + get_sp500_tickers()
