"""护城河评分系统 — 基于巴菲特五大原则

五大原则：
1. 好公司+低价 = 千载难逢（不是低价就好，是好公司的低价）
2. 无视市场先生的日常疯狂
3. 关注生意本身：ROE、确定性、长期可持有
4. ROE 15%+ 长期稳定 = 护城河的量化证据
5. 一句话说清业务 + 十年后还在 = 真正的护城河
"""

import math
from typing import Dict, List, Optional


def score_moat(fundamentals: dict, normalized: dict, tech_signal: dict) -> dict:
    """
    护城河综合评分 (满分 100)

    五大维度：
    1. 盈利质量 (30分) — ROE 的高度和稳定性
    2. 护城河深度 (25分) — 利润率、定价权
    3. 财务堡垒 (20分) — 低负债、高现金流
    4. 成长确定性 (15分) — 可预测的成长
    5. 市场先生机会 (10分) — 估值是否处于恐慌区域
    """
    scores = {}
    details = []
    total = 0
    max_total = 0

    # ===== 1. 盈利质量 (30分) =====
    # "ROE 15%+ 长期稳定 = 确定性&可预测性"
    eq_score = 0
    eq_max = 30

    roe = normalized.get("roe")
    roe_history = normalized.get("roe_history", [])

    if roe is not None:
        if roe >= 20:
            eq_score += 12
            details.append(("✓", "ROE {:.1f}%，远超15%门槛，盈利能力卓越".format(roe), "high"))
        elif roe >= 15:
            eq_score += 8
            details.append(("✓", "ROE {:.1f}%，达到巴菲特15%门槛".format(roe), "medium"))
        elif roe >= 10:
            eq_score += 4
            details.append(("△", "ROE {:.1f}%，接近但未达15%门槛".format(roe), "low"))
        else:
            details.append(("✗", "ROE {:.1f}%，远低于15%门槛".format(roe), "negative"))

    # ROE 稳定性（标准差越小越稳定）
    if len(roe_history) >= 3:
        above_15 = sum(1 for r in roe_history if r >= 15)
        ratio = above_15 / len(roe_history)
        if ratio >= 1.0:
            eq_score += 12
            details.append(("✓", "ROE 连续{}年超15%，确定性极高".format(len(roe_history)), "high"))
        elif ratio >= 0.8:
            eq_score += 8
            details.append(("✓", "ROE {}年中{}年超15%，稳定性良好".format(len(roe_history), above_15), "medium"))
        elif ratio >= 0.5:
            eq_score += 4
            details.append(("△", "ROE 稳定性一般，波动较大", "low"))
        else:
            details.append(("✗", "ROE 多年未达标，缺乏确定性", "negative"))

        # 趋势：ROE 是否在改善
        if len(roe_history) >= 2:
            recent = sum(roe_history[:2]) / 2  # 最近2年
            older = sum(roe_history[-2:]) / 2   # 较早2年
            if recent > older * 1.1:
                eq_score += 6
                details.append(("✓", "ROE 呈上升趋势，护城河在加深", "high"))
            elif recent > older * 0.9:
                eq_score += 3
                details.append(("△", "ROE 保持平稳", "medium"))
            else:
                details.append(("✗", "ROE 呈下降趋势，护城河可能在弱化", "negative"))

    scores["盈利质量"] = {"score": eq_score, "max": eq_max, "icon": "📊"}
    total += eq_score
    max_total += eq_max

    # ===== 2. 护城河深度 (25分) =====
    # "有鳄鱼的护城河：定价权 + 利润率"
    moat_score = 0
    moat_max = 25

    # 毛利率 — 定价权的直接体现
    gm = normalized.get("gross_margin")
    if gm is not None:
        if gm >= 60:
            moat_score += 10
            details.append(("✓", "毛利率 {:.1f}%，极强定价权（鳄鱼级护城河）".format(gm), "high"))
        elif gm >= 40:
            moat_score += 7
            details.append(("✓", "毛利率 {:.1f}%，较强定价权".format(gm), "medium"))
        elif gm >= 25:
            moat_score += 4
            details.append(("△", "毛利率 {:.1f}%，定价权一般".format(gm), "low"))
        else:
            details.append(("✗", "毛利率 {:.1f}%，缺乏定价权".format(gm), "negative"))

    # 净利率 — 护城河的最终体现
    pm = normalized.get("profit_margin")
    if pm is not None:
        if pm >= 25:
            moat_score += 10
            details.append(("✓", "净利率 {:.1f}%，护城河又深又宽".format(pm), "high"))
        elif pm >= 15:
            moat_score += 7
            details.append(("✓", "净利率 {:.1f}%，护城河较深".format(pm), "medium"))
        elif pm >= 8:
            moat_score += 3
            details.append(("△", "净利率 {:.1f}%，护城河较浅".format(pm), "low"))
        else:
            details.append(("✗", "净利率 {:.1f}%，几乎没有护城河".format(pm), "negative"))

    # 运营利润率稳定性
    om = normalized.get("operating_margin")
    if om is not None and om > 15:
        moat_score += 5
        details.append(("✓", "经营利润率 {:.1f}%，运营效率高".format(om), "medium"))

    scores["护城河深度"] = {"score": moat_score, "max": moat_max, "icon": "🏰"}
    total += moat_score
    max_total += moat_max

    # ===== 3. 财务堡垒 (20分) =====
    # "即使股市关门5年仍然可以投"
    fort_score = 0
    fort_max = 20

    # 负债率
    dte = normalized.get("debt_to_equity")
    if dte is not None:
        if dte <= 0.3:
            fort_score += 7
            details.append(("✓", "负债权益比 {:.2f}，财务堡垒坚固".format(dte), "high"))
        elif dte <= 0.6:
            fort_score += 4
            details.append(("△", "负债权益比 {:.2f}，负债可控".format(dte), "medium"))
        else:
            details.append(("✗", "负债权益比 {:.2f}，财务压力较大".format(dte), "negative"))

    # 流动比率
    cr = normalized.get("current_ratio")
    if cr is not None:
        if cr >= 2.0:
            fort_score += 5
            details.append(("✓", "流动比率 {:.2f}，短期无忧".format(cr), "high"))
        elif cr >= 1.5:
            fort_score += 3
            details.append(("△", "流动比率 {:.2f}，尚可".format(cr), "medium"))
        elif cr > 0:
            details.append(("✗", "流动比率 {:.2f}，偏紧".format(cr), "negative"))

    # 自由现金流
    fcf = normalized.get("free_cashflow")
    if fcf is not None:
        if fcf > 0:
            fort_score += 8
            details.append(("✓", "自由现金流为正，公司能自己造血", "high"))
        else:
            details.append(("✗", "自由现金流为负，需持续融资", "negative"))

    scores["财务堡垒"] = {"score": fort_score, "max": fort_max, "icon": "🛡️"}
    total += fort_score
    max_total += fort_max

    # ===== 4. 成长确定性 (15分) =====
    # "确定性&可预测性"
    grow_score = 0
    grow_max = 15

    rg = normalized.get("revenue_growth")
    eg = normalized.get("earnings_growth")

    if rg is not None:
        if rg >= 15:
            grow_score += 5
            details.append(("✓", "营收增长 {:.1f}%，成长动力强劲".format(rg), "high"))
        elif rg >= 5:
            grow_score += 3
            details.append(("✓", "营收增长 {:.1f}%，稳健成长".format(rg), "medium"))
        elif rg >= 0:
            grow_score += 1
            details.append(("△", "营收增长 {:.1f}%，增长放缓".format(rg), "low"))
        else:
            details.append(("✗", "营收下滑 {:.1f}%".format(rg), "negative"))

    if eg is not None:
        if eg >= 15:
            grow_score += 5
            details.append(("✓", "利润增长 {:.1f}%，盈利向好".format(eg), "high"))
        elif eg >= 5:
            grow_score += 3
            details.append(("✓", "利润增长 {:.1f}%，利润稳健".format(eg), "medium"))
        elif eg >= 0:
            grow_score += 1
        else:
            details.append(("✗", "利润下滑 {:.1f}%".format(eg), "negative"))

    # 营收和利润是否同步增长（质量）
    if rg is not None and eg is not None and rg > 0 and eg > 0:
        if eg >= rg:
            grow_score += 5
            details.append(("✓", "利润增速超营收，盈利质量在提升", "high"))
        else:
            grow_score += 2
            details.append(("△", "利润增速低于营收，关注成本控制", "low"))

    scores["成长确定性"] = {"score": grow_score, "max": grow_max, "icon": "📈"}
    total += grow_score
    max_total += grow_max

    # ===== 5. 市场先生机会 (10分) =====
    # "等市场先生发疯时买入"
    mr_score = 0
    mr_max = 10

    pe = normalized.get("pe_trailing")
    pb = normalized.get("pb")

    # PE 估值
    if pe is not None and pe > 0:
        if pe <= 15:
            mr_score += 4
            details.append(("✓", "PE {:.1f}，市场先生可能在恐慌抛售".format(pe), "high"))
        elif pe <= 25:
            mr_score += 2
            details.append(("△", "PE {:.1f}，估值合理".format(pe), "medium"))
        else:
            details.append(("✗", "PE {:.1f}，市场先生可能过于乐观".format(pe), "negative"))

    # PB 估值
    if pb is not None and pb > 0:
        if pb <= 2:
            mr_score += 3
            details.append(("✓", "PB {:.2f}，价格接近账面价值".format(pb), "high"))
        elif pb <= 4:
            mr_score += 1
            details.append(("△", "PB {:.2f}".format(pb), "medium"))
        else:
            details.append(("✗", "PB {:.2f}，溢价较高".format(pb), "negative"))

    # RSI 超卖 = 市场先生恐慌
    rsi = tech_signal.get("rsi")
    if rsi is not None:
        if rsi < 30:
            mr_score += 3
            details.append(("✓", "RSI {:.0f}，市场先生极度恐慌，可能是机会！".format(rsi), "high"))
        elif rsi > 70:
            details.append(("✗", "RSI {:.0f}，市场先生过度兴奋，注意风险".format(rsi), "negative"))

    scores["市场先生机会"] = {"score": mr_score, "max": mr_max, "icon": "🎯"}
    total += mr_score
    max_total += mr_max

    # ===== 综合评级 =====
    pct = (total / max_total * 100) if max_total > 0 else 0

    if pct >= 80:
        grade = "S"
        label = "金牌护城河"
        color = "#D4AF37"
        verdict = "巴菲特级别的投资标的！护城河极深，鳄鱼环伺，长期持有的好公司。"
    elif pct >= 65:
        grade = "A"
        label = "强护城河"
        color = "#00c853"
        verdict = "优质企业，护城河宽且深。等待合理价格后值得重仓。"
    elif pct >= 50:
        grade = "B"
        label = "中等护城河"
        color = "#2196f3"
        verdict = "不错的公司，但护城河可能不够深。适合适量配置，持续观察。"
    elif pct >= 35:
        grade = "C"
        label = "弱护城河"
        color = "#ff9800"
        verdict = "护城河较浅，竞争优势不明显。巴菲特可能会选择等待更好的机会。"
    else:
        grade = "D"
        label = "无护城河"
        color = "#f44336"
        verdict = "缺乏持久竞争优势，不符合价值投资标准。远离。"

    return {
        "total_score": total,
        "max_score": max_total,
        "percentage": round(pct, 1),
        "grade": grade,
        "label": label,
        "color": color,
        "verdict": verdict,
        "scores": scores,
        "details": details,
    }
