"""SEC EDGAR 数据源适配器 — 美股官方财务数据（免费，无需 API Key）

数据来源：data.sec.gov XBRL API
覆盖：10-K / 10-Q 年报季报中的标准 US-GAAP 指标
"""
from __future__ import annotations
import logging
import time
from functools import lru_cache
from typing import Optional

import pandas as pd
import requests

from .base import BaseAdapter

logger = logging.getLogger(__name__)

_EDGAR_BASE = "https://data.sec.gov"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_HEADERS = {
    "User-Agent": "StockAnalyst research@example.com",
    "Accept-Encoding": "gzip, deflate",
}
_TIMEOUT = 15
_REQUEST_DELAY = 0.15


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return None if f != f else f
    except (TypeError, ValueError):
        return default


def _get_latest_annual_value(units_list: list) -> Optional[float]:
    """从 XBRL units 列表中取最新 10-K 年报值"""
    annual = [u for u in units_list if u.get("form") in ("10-K", "10-K/A")]
    if not annual:
        return None
    latest = max(annual, key=lambda u: u.get("filed", ""))
    return _safe_float(latest.get("val"))


class SecEdgarAdapter(BaseAdapter):
    """SEC EDGAR XBRL 适配器，仅支持美股。无需 API Key，免费使用。"""

    def is_available(self) -> bool:
        try:
            r = requests.get(_TICKERS_URL, headers=_HEADERS, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    @lru_cache(maxsize=1024)
    def _get_cik(self, ticker: str) -> Optional[str]:
        """ticker → CIK（补零到10位）"""
        try:
            r = requests.get(_TICKERS_URL, headers=_HEADERS, timeout=_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            ticker_upper = ticker.upper()
            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker_upper:
                    cik = str(entry["cik_str"]).zfill(10)
                    return cik
        except Exception as e:
            logger.debug("SEC EDGAR CIK lookup failed for %s: %s", ticker, e)
        return None

    def _get_company_facts(self, ticker: str) -> Optional[dict]:
        cik = self._get_cik(ticker)
        if not cik:
            return None
        time.sleep(_REQUEST_DELAY)
        try:
            url = f"{_EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
            r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.debug("SEC EDGAR company facts failed for %s: %s", ticker, e)
            return None

    def get_us_financials(self, ticker: str) -> Optional[dict]:
        facts = self._get_company_facts(ticker)
        if not facts:
            return None

        gaap = facts.get("facts", {}).get("us-gaap", {})

        def _get(concept: str) -> Optional[float]:
            data = gaap.get(concept, {})
            usd = data.get("units", {}).get("USD", [])
            return _get_latest_annual_value(usd)

        net_income = _get("NetIncomeLoss")
        equity = _get("StockholdersEquity")
        revenues = _get("Revenues") or _get("RevenueFromContractWithCustomerExcludingAssessedTax")
        gross_profit = _get("GrossProfit")
        operating_income = _get("OperatingIncomeLoss")
        total_assets = _get("Assets")
        total_liabilities = _get("Liabilities")
        current_assets = _get("AssetsCurrent")
        current_liabilities = _get("LiabilitiesCurrent")
        operating_cf = _get("NetCashProvidedByUsedInOperatingActivities")
        capex_raw = _get("PaymentsToAcquirePropertyPlantAndEquipment")
        capex = -abs(capex_raw) if capex_raw is not None else None

        roe = (net_income / equity) if (net_income and equity and equity != 0) else None
        roa = (net_income / total_assets) if (net_income and total_assets and total_assets != 0) else None
        profit_margin = (net_income / revenues) if (net_income and revenues and revenues != 0) else None
        gross_margin = (gross_profit / revenues) if (gross_profit and revenues and revenues != 0) else None
        operating_margin = (operating_income / revenues) if (operating_income and revenues and revenues != 0) else None
        current_ratio = (current_assets / current_liabilities) if (current_assets and current_liabilities and current_liabilities != 0) else None
        debt_to_equity = None
        if total_liabilities and equity and equity != 0:
            debt_to_equity = (total_liabilities / equity) * 100
        fcf = (operating_cf + capex) if (operating_cf and capex) else operating_cf

        return {
            "_source": "sec_edgar",
            "symbol": ticker,
            "roe": roe,
            "roa": roa,
            "profit_margin": profit_margin,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "total_revenue": revenues,
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "free_cashflow": fcf,
            "operating_cashflow": operating_cf,
        }

    def get_a_share_financials(self, symbol: str) -> Optional[dict]:
        return None

    def get_a_share_history(self, symbol: str, days: int = 250) -> Optional[pd.DataFrame]:
        return None
