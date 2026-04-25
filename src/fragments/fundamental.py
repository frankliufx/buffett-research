"""基本面 fragment — MOAT scorecard + Buffett/Duan valuation checklist."""

import streamlit as st

from src.ui_theme import COLORS, render_grade_badge, render_detail_item
from src.ui_components import render_quote
from src.fragments._shared import fmt_pct, format_number


_VERDICT_CSS = {
    "买入": "verdict-buy",
    "增持": "verdict-accumulate",
    "持有": "verdict-hold",
    "减持": "verdict-reduce",
    "回避": "verdict-avoid",
}
_CONFIDENCE_LABEL = {"高": "HIGH", "中": "MED", "低": "LOW"}


@st.fragment
def render_moat_scorecard(moat, brief=None, normalized=None):
    """Redesigned moat scorecard — with optional AI brief overlay."""
    grade = moat["grade"]
    pct = moat["percentage"]
    label = moat["label"]
    color = moat["color"]

    # ── 1. AI verdict banner ─────────────────────────────────────────────
    if brief:
        verdict = brief.get("verdict", "持有")
        confidence = brief.get("confidence", "中")
        reason = brief.get("reason", "")
        css_cls = _VERDICT_CSS.get(verdict, "verdict-hold")
        conf_label = _CONFIDENCE_LABEL.get(confidence, confidence)
        st.markdown("""
        <div class="verdict-banner {css}">
            <div class="verdict-action">{verdict}</div>
            <div class="verdict-confidence">置信度 · {conf}</div>
            <div class="verdict-reason">{reason}</div>
        </div>
        """.format(css=css_cls, verdict=verdict, conf=conf_label, reason=reason),
        unsafe_allow_html=True)
    else:
        local_action = moat.get("verdict", "")
        st.markdown("""
        <div style="background:#141419; border:1px solid #2A2A33; padding:12px 18px; margin-bottom:16px;
                    display:flex; align-items:center; gap:12px;">
            <span style="color:{color}; font-size:0.9rem; font-weight:600; letter-spacing:1px;">{label}</span>
            <span style="color:#5A5A68; font-size:0.82rem;">{verdict}</span>
        </div>
        """.format(color=color, label=label, verdict=local_action), unsafe_allow_html=True)

    # ── 2. Two-column layout: left = grade panel, right = dimension cards ─
    col_left, col_right = st.columns([1, 2])

    with col_left:
        pe_v = "{:.1f}".format(normalized["pe_trailing"]) if normalized and normalized.get("pe_trailing") else "--"
        pb_v = "{:.2f}".format(normalized["pb"]) if normalized and normalized.get("pb") else "--"
        roe_v = fmt_pct(normalized.get("roe")) if normalized else "--"
        mcap = normalized.get("market_cap") if normalized else None

        st.markdown("""
        <div class="grade-panel">
            {badge}
            <div class="score-big">{pct:.0f}</div>
            <div class="score-label">/ 100 · 综合评分</div>
            <div style="margin:14px 0 8px;">
                <span class="moat-label" style="background:{color}18; color:{color}; font-size:0.72rem;">
                    {label}
                </span>
            </div>
            <div style="height:1px; background:#1E1E26; margin:12px 0;"></div>
            <div class="grade-stat-row"><span class="stat-k">PE</span><span class="stat-v">{pe}</span></div>
            <div class="grade-stat-row"><span class="stat-k">PB</span><span class="stat-v">{pb}</span></div>
            <div class="grade-stat-row"><span class="stat-k">ROE</span><span class="stat-v">{roe}</span></div>
            <div class="grade-stat-row"><span class="stat-k">市值</span><span class="stat-v">{mcap}</span></div>
        </div>
        """.format(
            badge=render_grade_badge(grade),
            pct=pct, color=color, label=label,
            pe=pe_v, pb=pb_v, roe=roe_v,
            mcap=format_number(mcap) if mcap else "--",
        ), unsafe_allow_html=True)

    with col_right:
        dim_insights = brief.get("dimensions", {}) if brief else {}
        for cat_name, info in moat["scores"].items():
            icon = info.get("icon", "")
            score = info["score"]
            max_s = info["max"]
            pct_s = score / max_s * 100 if max_s > 0 else 0
            if pct_s >= 65:
                bar_color = COLORS["success"]
            elif pct_s >= 40:
                bar_color = COLORS["warning"]
            else:
                bar_color = COLORS["danger"]
            ai_text = dim_insights.get(cat_name, "")
            has_cls = "has-insight" if ai_text else ""
            display_text = ai_text if ai_text else moat.get("verdict", "")[:30] if cat_name == list(moat["scores"].keys())[0] else ""

            st.markdown("""
            <div class="dim-card-v2">
                <div class="dim-header-v2">
                    <span class="dim-icon-v2">{icon}</span>
                    <span class="dim-name-v2">{name}</span>
                    <span class="dim-score-v2">{score}/{max}</span>
                </div>
                <div class="dim-bar-bg-v2">
                    <div class="dim-bar-fill-v2" style="width:{pct:.0f}%; background:{color};"></div>
                </div>
                {insight_html}
            </div>
            """.format(
                icon=icon, name=cat_name, score=score, max=max_s, pct=pct_s, color=bar_color,
                insight_html='<div class="dim-ai-v2 {}">{}</div>'.format(has_cls, display_text) if display_text else "",
            ), unsafe_allow_html=True)

    # ── 3. Bull / bear breakdown ─────────────────────────────────────────
    if brief:
        bull = brief.get("bull_points", [])
        bear = brief.get("bear_points", [])
        if bull or bear:
            bull_items = "".join('<div class="bb-item">· {}</div>'.format(b) for b in bull)
            bear_items = "".join('<div class="bb-item">· {}</div>'.format(b) for b in bear)
            st.markdown("""
            <div class="bb-grid">
                <div class="bb-col bb-bull">
                    <div class="bb-title">✓ 核心优势</div>
                    {bull}
                </div>
                <div class="bb-col bb-bear">
                    <div class="bb-title">✗ 主要风险</div>
                    {bear}
                </div>
            </div>
            """.format(bull=bull_items, bear=bear_items), unsafe_allow_html=True)

    # ── 4. Detail expander ────────────────────────────────────────────────
    st.write("")
    with st.expander("查看详细维度分析"):
        for icon, text, level in moat["details"]:
            st.markdown(render_detail_item(icon, text, level), unsafe_allow_html=True)


def render_valuation_reference(symbol, normalized, moat):
    """Buffett + Duan checklist — replaces a useless refresh button."""
    pe = normalized.get("pe_trailing")
    pb = normalized.get("pb")
    roe = normalized.get("roe")
    gm = normalized.get("gross_margin")
    pm = normalized.get("profit_margin")
    dte = normalized.get("debt_to_equity")
    cr = normalized.get("current_ratio")
    score = moat["percentage"]

    st.markdown("")

    checks = []

    if roe is not None:
        if roe >= 20:
            checks.append(("pass", "ROE {:.1f}% — 远超巴菲特 15% 门槛，盈利能力卓越".format(roe)))
        elif roe >= 15:
            checks.append(("pass", "ROE {:.1f}% — 达到巴菲特 15% 门槛".format(roe)))
        elif roe >= 10:
            checks.append(("warn", "ROE {:.1f}% — 接近但未达巴菲特 15% 标准".format(roe)))
        else:
            checks.append(("fail", "ROE {:.1f}% — 低于巴菲特 15% 底线".format(roe)))
    else:
        checks.append(("na", "ROE 数据缺失"))

    if pe is not None and pe > 0:
        if pe <= 15:
            checks.append(("pass", "PE {:.1f} — 市场先生在恐慌抛售，格雷厄姆会点头".format(pe)))
        elif pe <= 25:
            checks.append(("pass", "PE {:.1f} — 估值合理，好公司值得这个价".format(pe)))
        elif pe <= 35:
            checks.append(("warn", "PE {:.1f} — 偏贵，需要确认成长性能否支撑".format(pe)))
        else:
            checks.append(("fail", "PE {:.1f} — 巴菲特不会在这个价位买入".format(pe)))
    else:
        checks.append(("na", "PE 数据缺失或为负（亏损）"))

    if gm is not None:
        if gm >= 40:
            checks.append(("pass", "毛利率 {:.1f}% — 拥有定价权，护城河有鳄鱼".format(gm)))
        elif gm >= 25:
            checks.append(("warn", "毛利率 {:.1f}% — 定价权一般".format(gm)))
        else:
            checks.append(("fail", "毛利率 {:.1f}% — 缺乏定价权，生意模式不够好".format(gm)))

    if dte is not None:
        if dte <= 0.5:
            checks.append(("pass", "负债权益比 {:.2f} — 段永平：不用杠杆是本分".format(dte)))
        elif dte <= 1.0:
            checks.append(("warn", "负债权益比 {:.2f} — 负债可控但需关注".format(dte)))
        else:
            checks.append(("fail", "负债权益比 {:.2f} — 杠杆偏高，段永平会 pass".format(dte)))

    if score >= 65:
        checks.append(("pass", "护城河 {:.0f} 分 — 十年后大概率还在，值得长期持有".format(score)))
    elif score >= 50:
        checks.append(("warn", "护城河 {:.0f} 分 — 竞争优势一般，需持续跟踪".format(score)))
    else:
        checks.append(("fail", "护城河 {:.0f} 分 — 巴菲特会等待更好的标的".format(score)))

    icon_map = {"pass": ":green[PASS]", "fail": ":red[FAIL]", "warn": ":orange[WARN]", "na": "N/A"}

    with st.expander("巴菲特 + 段永平估值检查表", expanded=False):
        st.caption("用大师的标准逐项审视这家公司")

        for status, text in checks:
            st.markdown(icon_map[status] + " &nbsp; " + text)

        st.markdown("---")

        pass_count = sum(1 for s, _ in checks if s == "pass")
        fail_count = sum(1 for s, _ in checks if s == "fail")

        if fail_count == 0 and pass_count >= 3:
            quote_text = "以合理的价格买入优秀的企业，远胜于以便宜的价格买入平庸的企业。"
            quote_author = "buffett"
        elif fail_count >= 2:
            quote_text = "Stop Doing List 比 To Do List 更重要。不懂不做，这四个字价值万亿。"
            quote_author = "duan"
        elif pe and pe > 30:
            quote_text = "价格是你付出的，价值是你得到的。市场短期是投票机，长期是称重机。"
            quote_author = "buffett"
        else:
            quote_text = "投资最重要的是不要亏大钱。好公司遇到暂时困难时，往往是最好的买入机会。"
            quote_author = "duan"

        render_quote(quote_text, author=quote_author)
