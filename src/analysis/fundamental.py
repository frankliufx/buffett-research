"""基本面分析 — 巴菲特价值投资体系核心"""

import math
from src.config import BuffettStrategy


def _is_nan(val) -> bool:
    try:
        return math.isnan(float(val))
    except (TypeError, ValueError):
        return False


def _normalize_fundamentals(f: dict) -> dict:
    """
    标准化基本面数据格式。

    标准化后:
    - 百分比类指标: 数值形式 (15 表示 15%)
    - debt_to_equity: 比率形式 (1.0 表示 100%)
    - pe/pb 等: 原值不变
    """
    n = dict(f)

    # Data comes from Tencent/Sina APIs (unified data source)
    # 比率类数据是小数形式 (0.15 = 15%)
    for key in ("roe", "roa", "profit_margin", "operating_margin", "gross_margin",
                 "revenue_growth", "earnings_growth", "payout_ratio"):
        val = n.get(key)
        if val is not None and not _is_nan(val):
            n[key] = float(val) * 100
        else:
            n[key] = None

    # dividend_yield: trailingAnnualDividendYield 是小数
    dv = n.get("dividend_yield")
    if dv is not None and not _is_nan(dv):
        n["dividend_yield"] = float(dv) * 100
    else:
        n["dividend_yield"] = None

    # debt_to_equity: yfinance 返回 Debt/Equity * 100 (如 102.63)
    dte = n.get("debt_to_equity")
    if dte is not None and not _is_nan(dte):
        n["debt_to_equity"] = float(dte) / 100  # 转为比率
    else:
        n["debt_to_equity"] = None

    # 清理其他 NaN
    for key in ("pe_trailing", "pe_forward", "pb", "ps", "current_ratio",
                "quick_ratio", "free_cashflow", "operating_cashflow",
                "market_cap", "enterprise_value", "total_revenue"):
        val = n.get(key)
        if val is not None and _is_nan(val):
            n[key] = None

    # roe_history: 已经是百分比数值，清理 NaN
    roe_hist = n.get("roe_history", [])
    n["roe_history"] = [r for r in roe_hist if not _is_nan(r)]

    return n


def analyze_buffett(fundamentals: dict, strategy: BuffettStrategy) -> dict:
    """
    巴菲特价值投资评估体系 (满分100)

    维度:
    1. 护城河 (30分) — ROE 水平、一致性、利润率
    2. 财务健康 (20分) — 负债率、流动比率、自由现金流
    3. 成长性 (20分) — 营收增长、利润增长
    4. 估值安全边际 (25分) — PE、PB、股息率
    5. 管理层 (5分) — 分红率
    """
    f = _normalize_fundamentals(fundamentals)
    scores = {}
    details = []
    total_score = 0
    max_score = 0

    # ===== 1. 护城河评估 (30分) =====
    moat_score = 0
    moat_max = 30

    roe = f.get("roe")
    if roe is not None:
        if roe >= strategy.min_roe:
            moat_score += 10
            details.append(f"✓ ROE {roe:.1f}% >= {strategy.min_roe}%，盈利能力优秀")
        else:
            details.append(f"✗ ROE {roe:.1f}% < {strategy.min_roe}%，盈利能力不足")
    else:
        details.append("- ROE 数据不可用")

    roe_history = f.get("roe_history", [])
    if len(roe_history) >= 3:
        consistent = sum(1 for r in roe_history if r >= strategy.min_roe)
        if consistent >= len(roe_history):
            moat_score += 10
            details.append(f"✓ ROE 连续{len(roe_history)}年达标，护城河稳固")
        elif consistent >= len(roe_history) * 0.6:
            moat_score += 5
            details.append(f"△ ROE {consistent}/{len(roe_history)}年达标，护城河一般")
        else:
            details.append(f"✗ ROE 仅{consistent}/{len(roe_history)}年达标，护城河薄弱")

    pm = f.get("profit_margin")
    if pm is not None:
        if pm >= 20:
            moat_score += 10
            details.append(f"✓ 净利率 {pm:.1f}%，定价权强")
        elif pm >= 10:
            moat_score += 5
            details.append(f"△ 净利率 {pm:.1f}%，盈利尚可")
        else:
            details.append(f"✗ 净利率 {pm:.1f}%，缺乏定价权")

    scores["护城河"] = {"score": moat_score, "max": moat_max}
    total_score += moat_score
    max_score += moat_max

    # ===== 2. 财务健康 (20分) =====
    health_score = 0
    health_max = 20

    dte = f.get("debt_to_equity")
    if dte is not None:
        if dte <= strategy.max_debt_to_equity:
            health_score += 7
            details.append(f"✓ 负债权益比 {dte:.2f} <= {strategy.max_debt_to_equity}，财务稳健")
        else:
            details.append(f"✗ 负债权益比 {dte:.2f} > {strategy.max_debt_to_equity}，负债偏高")

    cr = f.get("current_ratio")
    if cr is not None:
        if cr >= strategy.min_current_ratio:
            health_score += 7
            details.append(f"✓ 流动比率 {cr:.2f}，短期偿债能力充足")
        else:
            details.append(f"✗ 流动比率 {cr:.2f}，短期偿债压力")

    fcf = f.get("free_cashflow")
    if fcf is not None and fcf > 0:
        health_score += 6
        details.append(f"✓ 自由现金流为正 ({_format_number(fcf)})，现金造血能力强")
    elif fcf is not None:
        details.append("✗ 自由现金流为负，需关注资金状况")

    scores["财务健康"] = {"score": health_score, "max": health_max}
    total_score += health_score
    max_score += health_max

    # ===== 3. 成长性 (20分) =====
    growth_score = 0
    growth_max = 20

    rg = f.get("revenue_growth")
    if rg is not None:
        if rg >= strategy.min_revenue_growth:
            growth_score += 10
            details.append(f"✓ 营收增长 {rg:.1f}%，成长性良好")
        else:
            details.append(f"✗ 营收增长 {rg:.1f}%，成长放缓")
    else:
        details.append("- 营收增长数据不可用")

    eg = f.get("earnings_growth")
    if eg is not None:
        if eg >= strategy.min_earnings_growth:
            growth_score += 10
            details.append(f"✓ 利润增长 {eg:.1f}%，盈利向上")
        else:
            details.append(f"✗ 利润增长 {eg:.1f}%，盈利承压")
    else:
        details.append("- 利润增长数据不可用")

    scores["成长性"] = {"score": growth_score, "max": growth_max}
    total_score += growth_score
    max_score += growth_max

    # ===== 4. 估值安全边际 (25分) =====
    value_score = 0
    value_max = 25

    pe = f.get("pe_trailing")
    if pe is not None and pe > 0:
        if pe <= strategy.max_pe * (1 - strategy.margin_of_safety):
            value_score += 10
            details.append(f"✓ PE {pe:.1f}，远低于上限{strategy.max_pe}，安全边际充足")
        elif pe <= strategy.max_pe:
            value_score += 5
            details.append(f"△ PE {pe:.1f}，处于合理范围")
        else:
            details.append(f"✗ PE {pe:.1f} > {strategy.max_pe}，估值偏高")
    else:
        details.append("- PE 数据不可用或为负（亏损）")

    pb = f.get("pb")
    if pb is not None and pb > 0:
        if pb <= strategy.max_pb * (1 - strategy.margin_of_safety):
            value_score += 8
            details.append(f"✓ PB {pb:.2f}，安全边际充足")
        elif pb <= strategy.max_pb:
            value_score += 4
            details.append(f"△ PB {pb:.2f}，估值合理")
        else:
            details.append(f"✗ PB {pb:.2f} > {strategy.max_pb}，估值偏高")

    div_pct = f.get("dividend_yield")
    if div_pct is not None and div_pct > 0:
        if div_pct >= 2:
            value_score += 7
            details.append(f"✓ 股息率 {div_pct:.2f}%，股东回报良好")
        else:
            value_score += 3
            details.append(f"△ 股息率 {div_pct:.2f}%，回报一般")

    scores["估值安全边际"] = {"score": value_score, "max": value_max}
    total_score += value_score
    max_score += value_max

    # ===== 5. 管理层与资本配置 (5分) =====
    mgmt_score = 0
    mgmt_max = 5

    payout = f.get("payout_ratio")  # 已标准化为百分比数值
    if payout is not None and 0 < payout < 100:
        min_payout_pct = strategy.min_payout_ratio * 100 if strategy.min_payout_ratio < 1 else strategy.min_payout_ratio
        if payout >= min_payout_pct:
            mgmt_score += 5
            details.append(f"✓ 分红率 {payout:.0f}%，管理层重视股东回报")

    scores["管理层"] = {"score": mgmt_score, "max": mgmt_max}
    total_score += mgmt_score
    max_score += mgmt_max

    # ===== 综合评级 =====
    pct = (total_score / max_score * 100) if max_score > 0 else 0

    if pct >= 80:
        grade = "A"
        recommendation = "强烈推荐"
        action = "巴菲特会买入 -- 优质企业+合理估值，建议重仓长期持有"
    elif pct >= 65:
        grade = "B"
        recommendation = "推荐关注"
        action = "好企业但需等更好价格，建议分批建仓或等待回调买入"
    elif pct >= 50:
        grade = "C"
        recommendation = "中性观望"
        action = "部分指标不达标，建议观望等待基本面改善"
    elif pct >= 35:
        grade = "D"
        recommendation = "不推荐"
        action = "不符合价值投资标准，建议回避"
    else:
        grade = "F"
        recommendation = "强烈回避"
        action = "多项指标严重不达标，远离"

    return {
        "total_score": total_score,
        "max_score": max_score,
        "percentage": round(pct, 1),
        "grade": grade,
        "recommendation": recommendation,
        "action": action,
        "scores": scores,
        "details": details,
    }


def _format_number(n) -> str:
    """格式化大数字"""
    if n is None:
        return "N/A"
    abs_n = abs(float(n))
    sign = "-" if float(n) < 0 else ""
    if abs_n >= 1e12:
        return f"{sign}{abs_n/1e12:.2f}万亿"
    elif abs_n >= 1e8:
        return f"{sign}{abs_n/1e8:.2f}亿"
    elif abs_n >= 1e4:
        return f"{sign}{abs_n/1e4:.2f}万"
    else:
        return f"{sign}{abs_n:.2f}"
