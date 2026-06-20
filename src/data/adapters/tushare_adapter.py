"""Tushare Pro 数据源适配器 — A 股基本面 + K 线历史"""
from __future__ import annotations
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from .base import BaseAdapter

logger = logging.getLogger(__name__)


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        s = str(val).strip()
        if s in ("", "-", "--", "N/A", "nan"):
            return default
        f = float(s)
        return None if f != f else f
    except (TypeError, ValueError):
        return default


class TushareAdapter(BaseAdapter):
    """Tushare Pro 适配器，仅支持 A 股。

    Token 优先从构造参数读取，其次读 TUSHARE_TOKEN 环境变量。
    """

    def __init__(self, token: str | None = None):
        self._token = token or os.getenv("TUSHARE_TOKEN", "")
        self._pro = None

    def _get_pro(self):
        if self._pro is None and self._token:
            import tushare as ts
            ts.set_token(self._token)
            self._pro = ts.pro_api()
        return self._pro

    def is_available(self) -> bool:
        if not self._token:
            return False
        try:
            pro = self._get_pro()
            result = pro.trade_cal(exchange="SSE", start_date="20260101", end_date="20260102")
            return result is not None and not result.empty
        except Exception as e:
            logger.debug("Tushare availability check failed: %s", e)
            return False

    def _to_ts_code(self, symbol: str) -> str:
        """'600519' → '600519.SH', '000001' → '000001.SZ'"""
        symbol = symbol.upper().strip()
        if symbol.endswith(".SH") or symbol.endswith(".SZ"):
            return symbol
        if symbol.startswith("6") or symbol.startswith("9"):
            return f"{symbol}.SH"
        return f"{symbol}.SZ"

    def get_a_share_financials(self, symbol: str) -> Optional[dict]:
        pro = self._get_pro()
        if pro is None:
            return None

        ts_code = self._to_ts_code(symbol)
        today = datetime.now().strftime("%Y%m%d")

        try:
            daily_basic = pro.daily_basic(
                ts_code=ts_code, trade_date=today,
                fields="ts_code,trade_date,pe,pb,total_mv,dv_ratio"
            )
            if daily_basic is None or daily_basic.empty:
                start = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
                daily_basic = pro.daily_basic(
                    ts_code=ts_code, start_date=start, end_date=today,
                    fields="ts_code,trade_date,pe,pb,total_mv,dv_ratio"
                )
                if daily_basic is not None and not daily_basic.empty:
                    daily_basic = daily_basic.iloc[0:1]

            now = datetime.now()
            q_ends = []
            for y in [now.year, now.year - 1]:
                for m in ["1231", "0930", "0630", "0331"]:
                    q_ends.append(f"{y}{m}")

            fina = None
            for period in q_ends[:4]:
                try:
                    df = pro.fina_indicator(
                        ts_code=ts_code, period=period,
                        fields="ts_code,end_date,roe,grossprofit_margin,netprofit_margin,"
                               "debt_to_assets,current_ratio,quick_ratio,fcff,n_cashflow_act,operate_income"
                    )
                    if df is not None and not df.empty:
                        fina = df.iloc[0]
                        break
                except Exception:
                    continue

            result: dict = {
                "_source": "tushare",
                "symbol": symbol,
            }

            if daily_basic is not None and not daily_basic.empty:
                row = daily_basic.iloc[0]
                result["pe_trailing"] = _safe_float(row.get("pe"))
                result["pb"] = _safe_float(row.get("pb"))
                mv = _safe_float(row.get("total_mv"))
                result["market_cap"] = mv * 10000 if mv else None
                result["dividend_yield"] = _safe_float(row.get("dv_ratio"))

            if fina is not None:
                roe = _safe_float(fina.get("roe"))
                result["roe"] = roe / 100.0 if roe is not None else None

                gm = _safe_float(fina.get("grossprofit_margin"))
                result["gross_margin"] = gm / 100.0 if gm is not None else None

                nm = _safe_float(fina.get("netprofit_margin"))
                result["profit_margin"] = nm / 100.0 if nm is not None else None

                da = _safe_float(fina.get("debt_to_assets"))
                if da is not None and 0 < da < 100:
                    debt_ratio = da / 100.0
                    if debt_ratio < 1.0:
                        result["debt_to_equity"] = (debt_ratio / (1 - debt_ratio)) * 100

                result["current_ratio"] = _safe_float(fina.get("current_ratio"))
                result["quick_ratio"] = _safe_float(fina.get("quick_ratio"))
                result["free_cashflow"] = _safe_float(fina.get("fcff"))
                result["operating_cashflow"] = _safe_float(fina.get("n_cashflow_act"))
                result["total_revenue"] = _safe_float(fina.get("operate_income"))

            return result if len(result) > 2 else None

        except Exception as e:
            logger.warning("TushareAdapter.get_a_share_financials(%s) failed: %s", symbol, e)
            return None

    def get_us_financials(self, symbol: str) -> Optional[dict]:
        return None

    def get_a_share_history(self, symbol: str, days: int = 250) -> Optional[pd.DataFrame]:
        pro = self._get_pro()
        if pro is None:
            return None

        ts_code = self._to_ts_code(symbol)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days + 30)).strftime("%Y%m%d")

        try:
            df = pro.daily(
                ts_code=ts_code, start_date=start_date, end_date=end_date,
                fields="trade_date,open,high,low,close,vol"
            )
            if df is None or df.empty:
                return None

            df = df.rename(columns={"trade_date": "date", "vol": "volume"})
            df = df.sort_values("date").reset_index(drop=True)
            return df.tail(days)

        except Exception as e:
            logger.warning("TushareAdapter.get_a_share_history(%s) failed: %s", symbol, e)
            return None
