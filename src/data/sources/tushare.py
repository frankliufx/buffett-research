"""TuShare Pro source — A股一体化数据，token-based.

Token comes from one of (in order):
    1. env  TUSHARE_TOKEN
    2. ~/.streamlit/secrets.toml  → tushare_token
    3. config.yaml                → tushare.token

If no token is configured, `is_configured()` returns False and the
source is excluded from the chain — production deployments add the
token via env or secrets.toml.

Endpoints used (read via the tushare python sdk, lazy-imported):
    pro.daily(...)        — 日线 OHLCV
    pro.fina_indicator()  — 财务指标 (ROE / 毛利率 / 净利率 / 资产负债率 ...)
    pro.daily_basic()     — 估值快照 (PE / PB / 市值 / 换手率)
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


def _resolve_token() -> Optional[str]:
    if t := os.getenv("TUSHARE_TOKEN"):
        return t.strip()
    # streamlit secrets
    try:
        import streamlit as st  # type: ignore
        if hasattr(st, "secrets") and "tushare_token" in st.secrets:
            return str(st.secrets["tushare_token"]).strip()
    except Exception:
        pass
    # config.yaml fallback
    try:
        from src.config import load_config
        cfg = load_config()
        tok = getattr(getattr(cfg, "tushare", object()), "token", None)
        if tok:
            return str(tok).strip()
    except Exception:
        pass
    return None


@lru_cache(maxsize=1)
def _pro():
    token = _resolve_token()
    if not token:
        return None
    try:
        import tushare as ts  # type: ignore
        ts.set_token(token)
        return ts.pro_api()
    except Exception as e:
        logger.warning("tushare init failed: %s", e)
        return None


def _ts_code(symbol: str) -> Optional[str]:
    """sh600519 → 600519.SH; sz000858 → 000858.SZ"""
    s = symbol.lower()
    if s.startswith("sh"):
        return s[2:].upper() + ".SH"
    if s.startswith("sz"):
        return s[2:].upper() + ".SZ"
    return None


class TushareSource:
    name = "tushare"

    def __init__(self):
        self._token = _resolve_token()

    def is_configured(self) -> bool:
        return bool(self._token)

    def supports(self, symbol: str, market: str) -> bool:
        return market.lower() == "a_share" and self.is_configured()

    def fetch_history(self, symbol: str, market: str, days: int = 250):
        try:
            import pandas as pd
        except ImportError:
            return None
        pro = _pro()
        ts_code = _ts_code(symbol)
        if pro is None or not ts_code:
            return None
        try:
            from datetime import date, timedelta
            end = date.today()
            start = end - timedelta(days=int(days * 1.6))
            df = pro.daily(ts_code=ts_code,
                           start_date=start.strftime("%Y%m%d"),
                           end_date=end.strftime("%Y%m%d"))
        except Exception as e:
            logger.warning("tushare daily failed for %s: %s", ts_code, e)
            return None
        if df is None or df.empty:
            return None
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                                  "close": "Close", "vol": "Volume",
                                  "trade_date": "Date"})
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        return df[["Open", "High", "Low", "Close", "Volume"]].tail(days)

    def fetch_quote(self, symbol: str, market: str) -> Optional[dict]:
        df = self.fetch_history(symbol, market, days=5)
        if df is None or df.empty:
            return None
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        last_close = float(last["Close"])
        prev_close = float(prev["Close"])
        chg = (last_close / prev_close - 1) * 100 if prev_close else 0.0
        return {
            "price": last_close,
            "regularMarketPrice": last_close,
            "regularMarketChangePercent": chg,
            "change_pct": chg,
            "open": float(last.get("Open", last_close)),
            "high": float(last.get("High", last_close)),
            "low": float(last.get("Low", last_close)),
            "volume": int(last.get("Volume", 0) or 0),
            "shortName": symbol,
        }

    def fetch_fundamentals(self, symbol: str, market: str) -> Optional[dict]:
        pro = _pro()
        ts_code = _ts_code(symbol)
        if pro is None or not ts_code:
            return None
        out: dict = {}
        try:
            ind = pro.fina_indicator(ts_code=ts_code)
            if ind is not None and not ind.empty:
                row = ind.iloc[0]
                # tushare returns ROE/毛利率/净利率 already as % (e.g. 25.4)
                # — convert to decimal to match _normalize_fundamentals contract
                if "roe" in row and row["roe"] is not None:
                    out["roe"] = float(row["roe"]) / 100
                if "grossprofit_margin" in row and row["grossprofit_margin"] is not None:
                    out["gross_margin"] = float(row["grossprofit_margin"]) / 100
                if "netprofit_margin" in row and row["netprofit_margin"] is not None:
                    out["profit_margin"] = float(row["netprofit_margin"]) / 100
                if "debt_to_assets" in row and row["debt_to_assets"] is not None:
                    # crude proxy: debt/assets * 100 → not perfect but close
                    out["debt_to_equity"] = float(row["debt_to_assets"])
                if "current_ratio" in row and row["current_ratio"] is not None:
                    out["current_ratio"] = float(row["current_ratio"])
                if "or_yoy" in row and row["or_yoy"] is not None:
                    out["revenue_growth"] = float(row["or_yoy"]) / 100
                if "netprofit_yoy" in row and row["netprofit_yoy"] is not None:
                    out["earnings_growth"] = float(row["netprofit_yoy"]) / 100
        except Exception as e:
            logger.warning("tushare fina_indicator failed for %s: %s", ts_code, e)

        try:
            db = pro.daily_basic(ts_code=ts_code, fields="pe,pb,total_mv,dv_ratio")
            if db is not None and not db.empty:
                row = db.iloc[0]
                if "pe" in row and row["pe"] is not None:
                    out["pe_trailing"] = float(row["pe"])
                if "pb" in row and row["pb"] is not None:
                    out["pb"] = float(row["pb"])
                if "total_mv" in row and row["total_mv"] is not None:
                    out["market_cap"] = float(row["total_mv"]) * 10_000  # 万元 → 元
                if "dv_ratio" in row and row["dv_ratio"] is not None:
                    out["dividend_yield"] = float(row["dv_ratio"]) / 100
        except Exception as e:
            logger.warning("tushare daily_basic failed for %s: %s", ts_code, e)

        return out or None
