"""Stooq.com OHLCV source — global, free, no API key.

URL pattern: https://stooq.com/q/d/l/?s=<sym>&d1=YYYYMMDD&d2=YYYYMMDD&i=d
Returns plain CSV (Date,Open,High,Low,Close,Volume).

Symbol mapping:
    US      → "{ticker}.us"   (AAPL → aapl.us)
    HK      → "{4-digit}.hk"  (0700.HK → 0700.hk)
    A-share → not supported reliably (stooq's CN coverage is patchy);
              return False on supports() so we fall through to TuShare.
"""

from __future__ import annotations

import io
import logging
from datetime import date, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class StooqSource:
    name = "stooq"

    def supports(self, symbol: str, market: str) -> bool:
        m = market.lower()
        return m in ("us", "hk")

    def _stooq_symbol(self, symbol: str, market: str) -> str:
        s = symbol.lower().replace(".hk", "").replace(".ss", "").replace(".sz", "")
        if market.lower() == "us":
            return f"{s}.us"
        if market.lower() == "hk":
            # HK on stooq: zero-padded 4-digit
            return f"{s.zfill(4)}.hk"
        return s

    def _csv_url(self, sym: str, days: int) -> str:
        end = date.today()
        start = end - timedelta(days=int(days * 1.6))  # weekends/holidays buffer
        return (
            f"https://stooq.com/q/d/l/?s={sym}"
            f"&d1={start.strftime('%Y%m%d')}&d2={end.strftime('%Y%m%d')}&i=d"
        )

    def fetch_history(self, symbol: str, market: str, days: int = 250):
        try:
            import pandas as pd
        except ImportError:
            return None
        sym = self._stooq_symbol(symbol, market)
        try:
            r = requests.get(self._csv_url(sym, days), timeout=8,
                             headers={"User-Agent": "BuffettResearch/1.0"})
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
        except Exception as e:
            logger.debug("stooq fetch_history(%s): %s", sym, e)
            return None
        if df is None or df.empty:
            return None
        # Normalize columns
        df.columns = [c.strip().capitalize() for c in df.columns]
        if "Date" not in df.columns or "Close" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        return df[keep].tail(days)

    def fetch_quote(self, symbol: str, market: str) -> Optional[dict]:
        df = self.fetch_history(symbol, market, days=5)
        if df is None or df.empty:
            return None
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        last_close = float(last["Close"])
        prev_close = float(prev["Close"])
        change_pct = (last_close / prev_close - 1) * 100 if prev_close else 0.0
        return {
            "price": last_close,
            "regularMarketPrice": last_close,
            "regularMarketChangePercent": change_pct,
            "change_pct": change_pct,
            "open": float(last.get("Open", last_close)),
            "high": float(last.get("High", last_close)),
            "low": float(last.get("Low", last_close)),
            "volume": int(last.get("Volume", 0) or 0),
            "shortName": symbol,
        }
