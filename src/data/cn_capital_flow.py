"""A股资金面数据 — 北向资金 / 主力净流入 / 龙虎榜。

Lazy-imports akshare inside each fetcher and catches every exception
type so a missing dep / network failure / API change can never crash
the policy panel. Each fetcher returns `None` on failure, the
aggregator collects fetch_errors[] and surfaces them in the UI.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from schemas.policy import CapitalFlow, CapitalFlowDay

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────


def _normalize_code(symbol: str) -> str:
    """Strip 'sh'/'sz' prefixes and any '.SS'/'.SZ' suffix → 6-digit code."""
    s = symbol.lower().replace("sh", "").replace("sz", "").split(".")[0].strip()
    return s.zfill(6)[-6:]


def _market_for(symbol: str) -> str:
    """akshare's stock_individual_fund_flow needs 'sh' / 'sz'."""
    s = symbol.lower()
    if s.startswith("sh") or _normalize_code(symbol).startswith(("60", "68", "9")):
        return "sh"
    return "sz"


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


# ── fetchers (each is single-source-of-failure isolated) ────────────────────


def _fetch_northbound(code: str) -> tuple[Optional[float], list[CapitalFlowDay], Optional[str]]:
    """Return (current_holding_pct, recent_history, error_label_or_None)."""
    try:
        import akshare as ak
        df = ak.stock_hsgt_individual_em(stock=code)
    except Exception as e:
        logger.warning("northbound fetch failed for %s: %s", code, e)
        return None, [], "北向"

    if df is None or df.empty:
        return None, [], None

    history: list[CapitalFlowDay] = []
    holding_pct: Optional[float] = None

    # akshare columns are CN strings; we tolerate variant names.
    cols = list(df.columns)
    date_col = next((c for c in cols if c in ("持股日期", "日期")), None)
    flow_col = next(
        (c for c in cols if c in ("当日成交净买额", "净买额", "净买入额-净买入额", "持股市值变化-1日")),
        None,
    )
    pct_col = next((c for c in cols if c in ("持股占流通股比", "占流通股比", "持股占A股百分比")), None)

    if pct_col and not df.empty:
        latest = df.iloc[-1]
        holding_pct = _safe_float(latest.get(pct_col))

    if date_col and flow_col:
        recent = df.tail(30)
        for _, row in recent.iterrows():
            try:
                d = row[date_col]
                if hasattr(d, "date"):
                    d = d.date()
                elif isinstance(d, str):
                    d = date.fromisoformat(d[:10])
                history.append(CapitalFlowDay(
                    date=d, net_inflow_yuan=_safe_float(row[flow_col]),
                ))
            except Exception:
                continue

    return holding_pct, history, None


def _fetch_main_flow(symbol: str) -> tuple[list[CapitalFlowDay], Optional[str]]:
    """Return (history, error_label_or_None). 主力净流入近 30 日。"""
    try:
        import akshare as ak
        code = _normalize_code(symbol)
        market = _market_for(symbol)
        df = ak.stock_individual_fund_flow(stock=code, market=market)
    except Exception as e:
        logger.warning("main flow fetch failed for %s: %s", symbol, e)
        return [], "主力"

    if df is None or df.empty:
        return [], None

    history: list[CapitalFlowDay] = []
    cols = list(df.columns)
    date_col = next((c for c in cols if c in ("日期",)), None)
    main_col = next((c for c in cols if c in ("主力净流入-净额", "主力净流入")), None)
    if not (date_col and main_col):
        return [], None

    recent = df.tail(30)
    for _, row in recent.iterrows():
        try:
            d = row[date_col]
            if hasattr(d, "date"):
                d = d.date()
            elif isinstance(d, str):
                d = date.fromisoformat(d[:10])
            history.append(CapitalFlowDay(
                date=d, net_inflow_yuan=_safe_float(row[main_col]),
            ))
        except Exception:
            continue
    return history, None


def _fetch_lhb_count(code: str, days: int = 30) -> tuple[Optional[int], Optional[str]]:
    """Count how many times the stock appeared on 龙虎榜 in last `days`."""
    try:
        import akshare as ak
        end = date.today()
        start = end - timedelta(days=days)
        df = ak.stock_lhb_detail_em(
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )
    except Exception as e:
        logger.warning("lhb fetch failed: %s", e)
        return None, "龙虎榜"

    if df is None or df.empty:
        return 0, None

    code_col = next((c for c in df.columns if c in ("代码", "股票代码")), None)
    if not code_col:
        return None, "龙虎榜"

    count = int((df[code_col].astype(str).str.zfill(6) == code).sum())
    return count, None


# ── aggregation + scoring ────────────────────────────────────────────────────


def _sum_window(history: list[CapitalFlowDay], days: int) -> Optional[float]:
    if not history:
        return None
    tail = history[-days:]
    vals = [d.net_inflow_yuan for d in tail if d.net_inflow_yuan is not None]
    return sum(vals) if vals else None


def _consensus_score(cf: CapitalFlow) -> tuple[Optional[float], Optional[str]]:
    """Aggregate the four sub-indicators into a 0-100 score.

    Heuristic (subject to revision once we have ground-truth):
      +25 if 北向 5d > 0    (+10 extra if also > 0 for 20d)
      +25 if 主力 5d > 0
      +20 if 北向持股占比 > 1%   (+10 extra if > 3%)
      +10 if 龙虎榜出现 ≥ 2 次内 (机构上榜更准但 detail 不查)
    Score < 35 → 弱共识 / 分歧；35-65 → 中性；>=65 → 强共识。
    """
    contributions = []

    if cf.northbound_5d_yuan is not None:
        if cf.northbound_5d_yuan > 0:
            contributions.append(25)
            if (cf.northbound_20d_yuan or 0) > 0:
                contributions.append(10)
        else:
            contributions.append(-15)

    if cf.main_5d_yuan is not None:
        if cf.main_5d_yuan > 0:
            contributions.append(25)
        else:
            contributions.append(-10)

    if cf.northbound_holding_pct is not None:
        if cf.northbound_holding_pct >= 3:
            contributions.append(30)
        elif cf.northbound_holding_pct >= 1:
            contributions.append(20)

    if cf.lhb_30d_count is not None and cf.lhb_30d_count >= 2:
        contributions.append(10)

    if not contributions:
        return None, None

    raw = sum(contributions)
    score = max(0.0, min(100.0, 50.0 + raw * 0.6))
    if score >= 65:
        label = "强共识"
    elif score >= 35:
        label = "中性"
    elif score >= 15:
        label = "弱共识"
    else:
        label = "分歧"
    return score, label


def get_capital_flow(symbol: str) -> CapitalFlow:
    """Aggregate northbound + main + LHB into a typed CapitalFlow."""
    code = _normalize_code(symbol)
    cf = CapitalFlow(symbol=symbol)
    errors: list[str] = []

    nb_pct, nb_hist, e1 = _fetch_northbound(code)
    if e1:
        errors.append(e1)
    cf.northbound_holding_pct = nb_pct
    cf.northbound_history = nb_hist
    cf.northbound_5d_yuan = _sum_window(nb_hist, 5)
    cf.northbound_20d_yuan = _sum_window(nb_hist, 20)

    main_hist, e2 = _fetch_main_flow(symbol)
    if e2:
        errors.append(e2)
    cf.main_history = main_hist
    cf.main_5d_yuan = _sum_window(main_hist, 5)

    lhb, e3 = _fetch_lhb_count(code)
    if e3:
        errors.append(e3)
    cf.lhb_30d_count = lhb

    cf.consensus_score, cf.consensus_label = _consensus_score(cf)
    cf.fetch_errors = errors
    return cf
