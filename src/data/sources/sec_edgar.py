"""SEC EDGAR XBRL source — official US filings, no API key.

Endpoints used:
    https://www.sec.gov/files/company_tickers.json   — ticker → CIK map
    https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
        — every reported XBRL fact for the company

SEC requires a real User-Agent header with contact info — set via env
`SEC_USER_AGENT` (e.g. "Acme/1.0 ops@example.com"); falls back to a
neutral default. Output shape matches what `_normalize_fundamentals`
expects (decimals for ratios, yfinance-style x100 for D/E).
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_UA = os.getenv(
    "SEC_USER_AGENT",
    "BuffettResearch/1.0 contact@buffett-research.local",
)
_HEADERS = {"User-Agent": _UA, "Accept-Encoding": "gzip,deflate"}
_TIMEOUT = 8


@lru_cache(maxsize=1)
def _ticker_to_cik() -> dict[str, str]:
    """Download SEC's ticker→CIK index (small JSON, cached process-wide)."""
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=_HEADERS, timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json() or {}
        out: dict[str, str] = {}
        for row in data.values():
            t = str(row.get("ticker", "")).upper()
            cik = str(row.get("cik_str", "")).zfill(10)
            if t and cik:
                out[t] = cik
        return out
    except Exception as e:
        logger.warning("SEC ticker map fetch failed: %s", e)
        return {}


@lru_cache(maxsize=256)
def _company_facts(cik: str) -> dict:
    try:
        r = requests.get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
            headers=_HEADERS, timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json() or {}
    except Exception as e:
        logger.warning("SEC company facts fetch failed for CIK %s: %s", cik, e)
        return {}


def _latest_fact(facts: dict, *tags: str, unit: Optional[str] = None) -> Optional[float]:
    """Walk the XBRL `us-gaap` facts looking for any of `tags`; return the most recent value."""
    gaap = (facts.get("facts") or {}).get("us-gaap") or {}
    for tag in tags:
        node = gaap.get(tag)
        if not node:
            continue
        units = node.get("units") or {}
        for u_key, rows in units.items():
            if unit and u_key != unit:
                continue
            if not rows:
                continue
            try:
                latest = max(rows, key=lambda r: r.get("end", ""))
                return float(latest.get("val"))
            except Exception:
                continue
    return None


class SecEdgarSource:
    name = "sec_edgar"

    def supports(self, symbol: str, market: str) -> bool:
        return market.lower() == "us"

    def fetch_fundamentals(self, symbol: str, market: str) -> Optional[dict]:
        cik = _ticker_to_cik().get(symbol.upper())
        if not cik:
            return None
        facts = _company_facts(cik)
        if not facts:
            return None

        revenue = _latest_fact(facts, "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", unit="USD")
        net_income = _latest_fact(facts, "NetIncomeLoss", unit="USD")
        equity = _latest_fact(facts, "StockholdersEquity", unit="USD")
        liabilities = _latest_fact(facts, "Liabilities", unit="USD")
        assets = _latest_fact(facts, "Assets", unit="USD")
        cur_assets = _latest_fact(facts, "AssetsCurrent", unit="USD")
        cur_liab = _latest_fact(facts, "LiabilitiesCurrent", unit="USD")
        op_cf = _latest_fact(facts, "NetCashProvidedByUsedInOperatingActivities", unit="USD")
        capex = _latest_fact(facts, "PaymentsToAcquirePropertyPlantAndEquipment", unit="USD")
        gross_profit = _latest_fact(facts, "GrossProfit", unit="USD")

        out: dict = {}

        # Ratios — return as DECIMAL (0.15) to match the contract
        if net_income is not None and equity:
            out["roe"] = net_income / equity
        if net_income is not None and revenue:
            out["profit_margin"] = net_income / revenue
        if gross_profit is not None and revenue:
            out["gross_margin"] = gross_profit / revenue
        if liabilities is not None and equity:
            # yfinance-compatible "percentage * 100" form
            out["debt_to_equity"] = (liabilities / equity) * 100.0
        if cur_assets is not None and cur_liab:
            out["current_ratio"] = cur_assets / cur_liab

        if op_cf is not None and capex is not None:
            out["free_cashflow"] = op_cf - capex
        elif op_cf is not None:
            out["free_cashflow"] = op_cf
        if op_cf is not None:
            out["operating_cashflow"] = op_cf
        if revenue is not None:
            out["total_revenue"] = revenue

        return out or None
