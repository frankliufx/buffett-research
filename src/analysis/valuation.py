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


# ══════════════════════════════════════════════════════════════════════════════
# 多模型估值引擎 — 借鉴 ai-hedge-fund 的四模型加权体系
# ══════════════════════════════════════════════════════════════════════════════

def calc_owner_earnings(price: float, fundamentals: dict, normalized: dict) -> Optional[dict]:
    """巴菲特 Owner Earnings 估值法

    Owner Earnings = 净利润 + 折旧摊销 - 维护性资本开支 - 营运资本变化
    维护性资本开支 ≈ 总资本开支 × 85%（保守估计）
    """
    net_income = _safe_float(fundamentals.get("net_income"))
    depreciation = _safe_float(fundamentals.get("depreciation"))
    capex = _safe_float(fundamentals.get("capital_expenditure"))
    market_cap = _safe_float(fundamentals.get("market_cap"))

    # 尝试从其他字段推导
    if net_income is None:
        # 用 EPS × 总股本推导
        eps = None
        pe = _safe_float(normalized.get("pe_trailing"))
        if pe and pe > 0 and price > 0:
            eps = price / pe
        if eps and market_cap and price > 0:
            shares = market_cap / price
            net_income = eps * shares

    if net_income is None or market_cap is None or market_cap <= 0:
        return None

    shares = market_cap / price if price > 0 else None
    if not shares:
        return None

    # Owner Earnings 计算
    dep = depreciation if depreciation else 0
    maintenance_capex = abs(capex) * 0.85 if capex else dep  # 若无资本开支，用折旧近似
    owner_earnings = net_income + dep - maintenance_capex

    if owner_earnings <= 0:
        return None

    oe_per_share = owner_earnings / shares

    # 增长率
    eg = _safe_float(normalized.get("earnings_growth"))
    rg = _safe_float(normalized.get("revenue_growth"))
    growth = None
    if eg is not None and -0.3 < eg < 0.5:
        growth = eg
    elif rg is not None and -0.3 < rg < 0.5:
        growth = rg

    if growth is None:
        growth = 0.05  # 保守假设 5%

    # DCF (15% 要求回报率, 25% 安全边际)
    required_return = 0.15
    terminal_growth = min(0.03, growth * 0.5)
    if required_return <= terminal_growth:
        terminal_growth = required_return - 0.02

    pv_total = 0.0
    cf = oe_per_share
    for yr in range(1, 11):
        cf *= (1 + growth)
        pv_total += cf / ((1 + required_return) ** yr)

    terminal_cf = cf * (1 + terminal_growth)
    terminal_val = terminal_cf / (required_return - terminal_growth)
    pv_terminal = terminal_val / ((1 + required_return) ** 10)

    intrinsic = (pv_total + pv_terminal) * 0.75  # 25% 安全边际已扣除
    intrinsic = max(intrinsic, 0)

    safety_margin = round((intrinsic - price) / intrinsic * 100, 1) if intrinsic > 0 else 0

    return {
        "method": "Owner Earnings",
        "intrinsic_value": round(intrinsic, 2),
        "safety_margin_pct": safety_margin,
        "owner_earnings_per_share": round(oe_per_share, 2),
        "growth_rate": round(growth * 100, 1),
    }


def calc_ev_ebitda(price: float, fundamentals: dict, normalized: dict) -> Optional[dict]:
    """EV/EBITDA 倍数估值法

    用行业中位数或历史均值 × 当前 EBITDA 推算公允价值
    """
    ebitda = _safe_float(fundamentals.get("ebitda"))
    ev = _safe_float(fundamentals.get("enterprise_value"))
    market_cap = _safe_float(fundamentals.get("market_cap"))
    total_debt = _safe_float(fundamentals.get("total_debt"))
    cash = _safe_float(fundamentals.get("cash"))

    if not ebitda or ebitda <= 0:
        return None

    if not market_cap or market_cap <= 0:
        return None

    shares = market_cap / price if price > 0 else None
    if not shares:
        return None

    # 当前 EV/EBITDA
    if ev and ev > 0:
        current_multiple = ev / ebitda
    elif market_cap:
        debt = total_debt if total_debt else 0
        cash_val = cash if cash else 0
        ev = market_cap + debt - cash_val
        current_multiple = ev / ebitda if ev > 0 else None
    else:
        return None

    if not current_multiple or current_multiple <= 0:
        return None

    # 公允倍数（行业通用基准）
    # 低倍数 (<8): 可能被低估
    # 中倍数 (8-15): 合理
    # 高倍数 (>15): 可能高估，需要高增长支撑
    fair_multiple = min(current_multiple, 12.0)  # 保守取 min(当前, 12)
    fair_ev = ebitda * fair_multiple
    debt = total_debt if total_debt else 0
    cash_val = cash if cash else 0
    fair_equity = fair_ev - debt + cash_val
    fair_price = fair_equity / shares if shares > 0 else 0
    fair_price = max(fair_price, 0)

    safety_margin = round((fair_price - price) / fair_price * 100, 1) if fair_price > 0 else 0

    return {
        "method": "EV/EBITDA",
        "intrinsic_value": round(fair_price, 2),
        "safety_margin_pct": safety_margin,
        "current_multiple": round(current_multiple, 1),
        "fair_multiple": round(fair_multiple, 1),
        "ebitda": round(ebitda, 0),
    }


def calc_residual_income(price: float, fundamentals: dict, normalized: dict) -> Optional[dict]:
    """残余收益估值法

    Intrinsic Value = Book Value + PV(Residual Income)
    RI = Net Income - Cost_of_Equity × Book Value
    """
    book_value = _safe_float(fundamentals.get("book_value"))
    market_cap = _safe_float(fundamentals.get("market_cap"))
    roe = _safe_float(normalized.get("roe"))  # 已经是百分比形式
    pb = _safe_float(normalized.get("pb"))

    # 从 PB 推导每股账面价值
    if pb and pb > 0 and price > 0:
        bvps = price / pb
    elif book_value and market_cap and market_cap > 0 and price > 0:
        shares = market_cap / price
        bvps = book_value / shares if shares > 0 else None
    else:
        bvps = None

    if not bvps or bvps <= 0 or roe is None:
        return None

    roe_decimal = roe / 100.0
    cost_of_equity = 0.10  # 10% 权益成本

    # 残余收益
    ri = bvps * (roe_decimal - cost_of_equity)

    # 假设 RI 以一定速率衰减（竞争侵蚀超额收益）
    fade_rate = 0.05  # 每年衰减 5%
    pv_ri = 0.0
    current_ri = ri
    for yr in range(1, 11):
        current_ri *= (1 - fade_rate)
        pv_ri += current_ri / ((1 + cost_of_equity) ** yr)

    intrinsic = bvps + pv_ri
    intrinsic = max(intrinsic, 0)

    safety_margin = round((intrinsic - price) / intrinsic * 100, 1) if intrinsic > 0 else 0

    return {
        "method": "残余收益",
        "intrinsic_value": round(intrinsic, 2),
        "safety_margin_pct": safety_margin,
        "book_value_per_share": round(bvps, 2),
        "residual_income_per_share": round(ri, 2),
        "roe": round(roe, 1),
    }


def calc_multi_model_valuation(price: float, fundamentals: dict, normalized: dict) -> Optional[dict]:
    """多模型加权估值 — 四模型综合

    权重分配（借鉴 ai-hedge-fund）：
    - DCF (原有): 35%
    - Owner Earnings: 30%
    - EV/EBITDA: 20%
    - 残余收益: 15%

    只对成功计算的模型做加权平均。
    """
    results = {}
    weights = {}

    # 1. 原有 DCF
    dcf = calc_dcf(price, fundamentals, normalized)
    if dcf and dcf.get("method") != "insufficient" and dcf.get("intrinsic_value"):
        results["DCF"] = dcf
        weights["DCF"] = 0.35

    # 2. Owner Earnings
    oe = calc_owner_earnings(price, fundamentals, normalized)
    if oe:
        results["Owner Earnings"] = oe
        weights["Owner Earnings"] = 0.30

    # 3. EV/EBITDA
    ev = calc_ev_ebitda(price, fundamentals, normalized)
    if ev:
        results["EV/EBITDA"] = ev
        weights["EV/EBITDA"] = 0.20

    # 4. 残余收益
    ri = calc_residual_income(price, fundamentals, normalized)
    if ri:
        results["残余收益"] = ri
        weights["残余收益"] = 0.15

    if not results:
        return None

    # 归一化权重
    total_weight = sum(weights.values())
    norm_weights = {k: v / total_weight for k, v in weights.items()}

    # 加权平均内在价值
    weighted_iv = sum(
        results[k]["intrinsic_value"] * norm_weights[k]
        for k in results
    )

    # 加权安全边际
    weighted_sm = round((weighted_iv - price) / weighted_iv * 100, 1) if weighted_iv > 0 else 0

    # 一致性分析：所有模型是否方向一致
    directions = []
    for r in results.values():
        sm = r.get("safety_margin_pct", 0)
        if sm > 10:
            directions.append("undervalued")
        elif sm < -10:
            directions.append("overvalued")
        else:
            directions.append("fair")

    unique_dirs = set(directions)
    if len(unique_dirs) == 1:
        consistency = "高"
    elif len(unique_dirs) == 2:
        consistency = "中"
    else:
        consistency = "低"

    # 判定
    if weighted_sm >= 25:
        verdict = "多模型共识低估"
    elif weighted_sm >= 10:
        verdict = "轻度低估"
    elif weighted_sm >= -10:
        verdict = "估值合理"
    elif weighted_sm >= -25:
        verdict = "轻度高估"
    else:
        verdict = "多模型共识高估"

    return {
        "weighted_intrinsic_value": round(weighted_iv, 2),
        "weighted_safety_margin_pct": weighted_sm,
        "model_count": len(results),
        "models": results,
        "weights_used": {k: round(v * 100, 1) for k, v in norm_weights.items()},
        "consistency": consistency,
        "verdict": verdict,
    }
