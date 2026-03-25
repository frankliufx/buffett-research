"""DCF 估值计算引擎 — 三情景内在价值 + 安全边际 + 决策输出

数据来源：yfinance (美股) / 东方财富 (港股) / 新浪 (A股) 的基本面字段
所有函数返回的 dict 可直接用于 UI 渲染
"""

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

# ── 默认假设 ─────────────────────────────────────────────────────────────────

_DEFAULT_DISCOUNT_RATE = 0.10      # 折现率（基准）
_DEFAULT_TERMINAL_GROWTH = 0.025   # 永续增长率
_PROJECTION_YEARS = 10             # 预测年数

# 三情景调整因子
_SCENARIOS = {
    "bear": {"growth_factor": 0.5,   "discount_adj": +0.02, "terminal_adj": -0.005},
    "base": {"growth_factor": 1.0,   "discount_adj": 0.0,   "terminal_adj": 0.0},
    "bull": {"growth_factor": 1.5,   "discount_adj": -0.01, "terminal_adj": +0.005},
}


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        result = float(val)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def calc_dcf(price: float, fundamentals: dict, normalized: dict) -> Optional[dict]:
    """核心 DCF 估值计算

    Args:
        price: 当前股价
        fundamentals: fetch_fundamentals() 的原始结果
        normalized: _normalize_fundamentals() 的结果

    Returns: dict with:
        - scenarios: {'bear': {...}, 'base': {...}, 'bull': {...}}
        - current_price, intrinsic_value (base), safety_margin_pct
        - verdict, confidence
        - assumptions: 核心假设参数
        - data_quality: 数据质量评估
    """
    if not price or price <= 0:
        return None

    # ── 提取关键输入 ─────────────────────────────────────────────────────
    fcf = _safe_float(fundamentals.get("free_cashflow"))
    ocf = _safe_float(fundamentals.get("operating_cashflow"))
    market_cap = _safe_float(fundamentals.get("market_cap"))
    earnings_growth = _safe_float(normalized.get("earnings_growth"))
    revenue_growth = _safe_float(normalized.get("revenue_growth"))
    pe = _safe_float(normalized.get("pe_trailing"))
    eps = None

    # 尝试估算 EPS（用于 PE 估值法兜底）
    if pe and pe > 0 and price > 0:
        eps = price / pe

    # 估算总股本
    shares_outstanding = None
    if market_cap and price > 0:
        shares_outstanding = market_cap / price

    # FCF per share（核心 DCF 输入）
    fcf_per_share = None
    if fcf and shares_outstanding and shares_outstanding > 0:
        fcf_per_share = fcf / shares_outstanding
    elif ocf and shares_outstanding and shares_outstanding > 0:
        fcf_per_share = ocf / shares_outstanding * 0.85  # OCF × 0.85 近似 FCF

    # 确定增长率（优先用 earnings_growth，回退 revenue_growth，再回退用 ROE 推导）
    roe = _safe_float(normalized.get("roe"))
    payout = _safe_float(fundamentals.get("payout_ratio"))

    base_growth = None
    growth_source = ""

    if earnings_growth is not None and -0.5 < earnings_growth < 1.0:
        base_growth = earnings_growth
        growth_source = "利润增速"
    elif revenue_growth is not None and -0.5 < revenue_growth < 1.0:
        base_growth = revenue_growth
        growth_source = "营收增速"
    elif roe is not None and roe > 0:
        retention = 1.0 - (payout if payout and 0 < payout < 1 else 0.3)
        base_growth = (roe / 100.0) * retention  # 可持续增长率 = ROE × 留存率
        growth_source = "ROE 推导"

    # ── 数据质量评估 ─────────────────────────────────────────────────────
    data_quality = "high"
    missing_fields = []
    if fcf_per_share is None and eps is None:
        missing_fields.append("FCF/EPS")
    if base_growth is None:
        missing_fields.append("增长率")
    if not market_cap:
        missing_fields.append("市值")

    if len(missing_fields) >= 2:
        data_quality = "low"
    elif missing_fields:
        data_quality = "medium"

    # ── 选择估值方法 ─────────────────────────────────────────────────────
    # 优先 FCF-DCF，其次 EPS-DCF，最后 PE Band
    method = "none"
    base_cf = None

    if fcf_per_share and fcf_per_share > 0 and base_growth is not None:
        base_cf = fcf_per_share
        method = "FCF-DCF"
    elif eps and eps > 0 and base_growth is not None:
        base_cf = eps
        method = "EPS-DCF"
    elif eps and eps > 0 and pe and pe > 0:
        method = "PE-Band"
    else:
        return _build_insufficient_result(price, missing_fields)

    # ── 三情景 DCF 计算 ──────────────────────────────────────────────────
    scenarios = {}

    if method in ("FCF-DCF", "EPS-DCF"):
        for scenario_name, adj in _SCENARIOS.items():
            g = base_growth * adj["growth_factor"]
            g = max(-0.10, min(g, 0.30))  # 限制增长率在 -10% ~ 30%

            r = _DEFAULT_DISCOUNT_RATE + adj["discount_adj"]
            tg = _DEFAULT_TERMINAL_GROWTH + adj["terminal_adj"]
            tg = min(tg, r - 0.01)  # 永续增长率必须 < 折现率

            # 逐年折现
            pv_total = 0.0
            projected_cf = base_cf
            for year in range(1, _PROJECTION_YEARS + 1):
                projected_cf *= (1 + g)
                pv_total += projected_cf / ((1 + r) ** year)

            # 终值
            terminal_cf = projected_cf * (1 + tg)
            terminal_value = terminal_cf / (r - tg)
            pv_terminal = terminal_value / ((1 + r) ** _PROJECTION_YEARS)

            intrinsic = pv_total + pv_terminal
            intrinsic = max(intrinsic, 0)

            scenarios[scenario_name] = {
                "intrinsic_value": round(intrinsic, 2),
                "growth_rate": round(g * 100, 1),
                "discount_rate": round(r * 100, 1),
                "terminal_growth": round(tg * 100, 1),
                "safety_margin_pct": round((intrinsic - price) / intrinsic * 100, 1) if intrinsic > 0 else 0,
            }

    elif method == "PE-Band":
        # PE 分位数估值法
        for scenario_name, adj in _SCENARIOS.items():
            if scenario_name == "bear":
                target_pe = pe * 0.7
            elif scenario_name == "bull":
                target_pe = pe * 1.3
            else:
                # 使用历史平均 PE 或当前 PE
                target_pe = pe

            fair_pe = min(target_pe, 25) if scenario_name == "bear" else target_pe
            intrinsic = eps * fair_pe
            intrinsic = max(intrinsic, 0)

            scenarios[scenario_name] = {
                "intrinsic_value": round(intrinsic, 2),
                "growth_rate": None,
                "discount_rate": None,
                "terminal_growth": None,
                "target_pe": round(fair_pe, 1),
                "safety_margin_pct": round((intrinsic - price) / intrinsic * 100, 1) if intrinsic > 0 else 0,
            }

    # ── 核心输出 ─────────────────────────────────────────────────────────
    base_iv = scenarios["base"]["intrinsic_value"]
    bear_iv = scenarios["bear"]["intrinsic_value"]
    bull_iv = scenarios["bull"]["intrinsic_value"]
    safety_margin = scenarios["base"]["safety_margin_pct"]

    # 止损位 = 悲观估值 × 0.9（再留 10% 缓冲）
    stop_loss = round(bear_iv * 0.9, 2) if bear_iv > 0 else round(price * 0.85, 2)

    # 决策判定
    verdict, confidence = _determine_verdict(price, bear_iv, base_iv, bull_iv,
                                              safety_margin, data_quality)

    return {
        "method": method,
        "current_price": price,
        "intrinsic_value": base_iv,
        "safety_margin_pct": safety_margin,
        "stop_loss": stop_loss,
        "scenarios": scenarios,
        "verdict": verdict,
        "confidence": confidence,
        "data_quality": data_quality,
        "assumptions": {
            "base_cashflow": round(base_cf, 2) if base_cf else None,
            "base_growth": round(base_growth * 100, 1) if base_growth is not None else None,
            "growth_source": growth_source,
            "discount_rate": _DEFAULT_DISCOUNT_RATE * 100,
            "terminal_growth": _DEFAULT_TERMINAL_GROWTH * 100,
            "projection_years": _PROJECTION_YEARS,
            "method": method,
            "eps": round(eps, 2) if eps else None,
            "fcf_per_share": round(fcf_per_share, 2) if fcf_per_share else None,
        },
    }


def _determine_verdict(price, bear_iv, base_iv, bull_iv, safety_margin, data_quality):
    """根据安全边际和数据质量判定投资结论"""
    if data_quality == "low":
        confidence = "低"
    elif data_quality == "medium":
        confidence = "中"
    else:
        confidence = "高"

    if safety_margin >= 30:
        verdict = "强烈买入"
        if confidence == "中":
            confidence = "中"
    elif safety_margin >= 15:
        verdict = "买入"
    elif safety_margin >= 0:
        verdict = "持有观望"
    elif safety_margin >= -15:
        verdict = "谨慎持有"
    elif safety_margin >= -30:
        verdict = "考虑减持"
    else:
        verdict = "回避"

    # 如果当前价低于悲观估值，信号更强
    if price <= bear_iv and safety_margin >= 15:
        verdict = "强烈买入"

    # 如果当前价高于乐观估值，信号明确
    if price >= bull_iv and bull_iv > 0:
        verdict = "回避"

    return verdict, confidence


def _build_insufficient_result(price, missing_fields):
    """数据不足时返回提示结果"""
    return {
        "method": "insufficient",
        "current_price": price,
        "intrinsic_value": None,
        "safety_margin_pct": None,
        "stop_loss": None,
        "scenarios": {},
        "verdict": "数据不足",
        "confidence": "低",
        "data_quality": "insufficient",
        "missing_fields": missing_fields,
        "assumptions": {},
    }
