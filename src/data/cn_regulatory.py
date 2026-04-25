"""A股监管风险数据 — ST 状态 / 实控人性质 / 业绩预警 / CSRC 处罚。

Same defensive-import pattern as cn_capital_flow.py — every fetcher is
isolated by try/except so partial data degradation doesn't break the
panel. The aggregator computes a `RiskLevel` and explanatory reasons
that the UI displays as colored badges + a textual reason list.
"""

from __future__ import annotations

import logging
from typing import Optional

from schemas.policy import ControllerType, RegulatoryStatus, RiskLevel

logger = logging.getLogger(__name__)


_RISK_COLOR = {
    "低":   "#3ECF8E",
    "中":   "#C9A962",
    "高":   "#F5A623",
    "极高": "#EF4444",
}


def _normalize_code(symbol: str) -> str:
    s = symbol.lower().replace("sh", "").replace("sz", "").split(".")[0].strip()
    return s.zfill(6)[-6:]


# ── fetchers ─────────────────────────────────────────────────────────────────


def _fetch_st_status(code: str) -> tuple[Optional[bool], Optional[str], Optional[str]]:
    """Return (is_st, st_label, error_label)."""
    try:
        import akshare as ak
        df = ak.stock_zh_a_st_em()
    except Exception as e:
        logger.warning("ST list fetch failed: %s", e)
        return None, None, "ST"

    if df is None or df.empty:
        return False, None, None

    code_col = next((c for c in df.columns if c in ("代码", "股票代码")), None)
    name_col = next((c for c in df.columns if c in ("名称", "股票简称")), None)
    if not code_col:
        return None, None, "ST"

    matched = df[df[code_col].astype(str).str.zfill(6) == code]
    if matched.empty:
        return False, None, None

    label = "ST"
    if name_col:
        name = str(matched.iloc[0][name_col])
        if "*ST" in name or "*st" in name.lower():
            label = "*ST"
        elif "暂停" in name:
            label = "暂停上市"
    return True, label, None


def _classify_controller(raw: str) -> ControllerType:
    """Heuristic mapping from 实控人/控股股东 description text → enum.

    Order matters: local-government markers must be checked before the
    generic '国资委' keyword (which is ambiguous between central and
    local — e.g. '北京市国资委' must classify as 地方国企, not 央企).
    """
    if not raw:
        return "未知"
    s = raw.strip()
    # No-实控人 first — "公众" can collide with 央企 prose otherwise.
    if "无实际控制人" in s or "无实控人" in s or s == "公众企业":
        return "无实控人"
    # Local-government markers (specific) before generic '国资委'
    if any(k in s for k in (
        "地方国资", "地方政府", "省国资", "市国资", "县国资", "区国资",
        "省人民政府", "市人民政府", "财政局", "财政厅",
    )):
        return "地方国企"
    if any(k in s for k in ("国务院", "中央汇金", "中央", "央企")):
        return "央企"
    # Generic 国资委 — if not caught above, it's a 省/市 国资委 by elimination
    if "国资委" in s:
        return "地方国企"
    if any(k in s for k in ("外资", "境外", "外商")):
        return "外资企业"
    if any(k in s for k in ("自然人", "先生", "女士")) or len(s) <= 4:
        return "民营企业"
    return "民营企业"


def _fetch_controller(code: str) -> tuple[ControllerType, Optional[str], Optional[str]]:
    """Return (controller_type, controller_name, error_label)."""
    try:
        import akshare as ak
        df = ak.stock_individual_info_em(symbol=code)
    except Exception as e:
        logger.warning("controller info fetch failed for %s: %s", code, e)
        return "未知", None, "实控人"

    if df is None or df.empty:
        return "未知", None, None

    # The returned shape is: rows of {item, value} (key/value pairs).
    item_col = next((c for c in df.columns if c in ("item", "项目")), df.columns[0])
    val_col = next((c for c in df.columns if c in ("value", "值")), df.columns[1] if len(df.columns) > 1 else None)
    if not val_col:
        return "未知", None, "实控人"

    row_lookup = {str(r[item_col]).strip(): str(r[val_col]).strip() for _, r in df.iterrows()}
    raw = (
        row_lookup.get("实际控制人")
        or row_lookup.get("控股股东")
        or row_lookup.get("最终控股")
        or ""
    )
    return _classify_controller(raw), raw or None, None


def _fetch_perf_warning(code: str) -> tuple[Optional[str], Optional[str]]:
    """业绩预告 (akshare stock_yjbb_em or similar). Best-effort only."""
    try:
        import akshare as ak
        # stock_yjyc_em returns 预告 for the most recent quarter
        if hasattr(ak, "stock_yjyc_em"):
            from datetime import date as _date
            yr = _date.today().year
            for q in ("1231", "0930", "0630", "0331"):
                try:
                    df = ak.stock_yjyc_em(date=f"{yr}{q}")
                    if df is None or df.empty:
                        continue
                    code_col = next((c for c in df.columns if c in ("股票代码", "代码")), None)
                    type_col = next((c for c in df.columns if c in ("预测类型", "业绩变动", "预告类型")), None)
                    if not code_col or not type_col:
                        continue
                    matched = df[df[code_col].astype(str).str.zfill(6) == code]
                    if matched.empty:
                        continue
                    label = str(matched.iloc[0][type_col])
                    if any(k in label for k in ("预亏", "预减", "首亏", "续亏")):
                        return label, None
                    return None, None
                except Exception:
                    continue
        return None, None
    except Exception as e:
        logger.warning("perf warning fetch failed: %s", e)
        return None, "业绩预告"


# ── aggregation ──────────────────────────────────────────────────────────────


def _level_from(rs: RegulatoryStatus) -> tuple[RiskLevel, list[str]]:
    """Compute (RiskLevel, reasons[]) from accumulated fields."""
    reasons: list[str] = []
    score = 0  # the higher, the riskier

    if rs.is_st:
        score += 60 if (rs.st_label or "").startswith("*") else 30
        reasons.append(f"{rs.st_label or 'ST'} — 监管特别处理")
    if rs.controller_type == "无实控人":
        score += 10
        reasons.append("无实控人 — 治理稳定性弱")
    if rs.perf_warning:
        score += 25
        reasons.append(f"业绩预警: {rs.perf_warning}")
    if (rs.csrc_penalty_count_3y or 0) > 0:
        score += 15 * min(rs.csrc_penalty_count_3y, 3)
        reasons.append(f"近 3 年 {rs.csrc_penalty_count_3y} 次 CSRC 处罚")

    if score >= 60:
        return "极高", reasons
    if score >= 30:
        return "高", reasons
    if score >= 10:
        return "中", reasons or ["数据综合无显著风险"]
    return "低", reasons or ["未发现监管风险信号"]


def get_regulatory_status(symbol: str) -> RegulatoryStatus:
    code = _normalize_code(symbol)

    # Fixture short-circuit
    from src.data.fixtures import is_fixture_mode, get_a_share_stock
    if is_fixture_mode():
        fx = get_a_share_stock(code)
        if fx:
            reg = fx.get("regulatory", {}) or {}
            rs = RegulatoryStatus(
                symbol=symbol,
                is_st=reg.get("is_st"),
                st_label=reg.get("st_label"),
                controller_type=reg.get("controller_type", "未知"),
                controller_name=reg.get("controller_name"),
                perf_warning=reg.get("perf_warning"),
                csrc_penalty_count_3y=reg.get("csrc_penalty_count_3y"),
            )
            rs.risk_level, rs.risk_reasons = _level_from(rs)
            rs.risk_color = _RISK_COLOR[rs.risk_level]
            return rs

    rs = RegulatoryStatus(symbol=symbol)
    errors: list[str] = []

    is_st, st_label, e1 = _fetch_st_status(code)
    if e1:
        errors.append(e1)
    rs.is_st = is_st
    rs.st_label = st_label

    ctype, cname, e2 = _fetch_controller(code)
    if e2:
        errors.append(e2)
    rs.controller_type = ctype
    rs.controller_name = cname

    pw, e3 = _fetch_perf_warning(code)
    if e3:
        errors.append(e3)
    rs.perf_warning = pw

    # CSRC penalty fetcher is left out of v1 (akshare endpoint is unstable);
    # the field stays None so the UI shows "暂未接入".
    rs.csrc_penalty_count_3y = None
    rs.csrc_penalty_recent = None

    rs.risk_level, rs.risk_reasons = _level_from(rs)
    rs.risk_color = _RISK_COLOR[rs.risk_level]
    rs.fetch_errors = errors
    return rs
