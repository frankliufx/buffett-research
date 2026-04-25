"""风险 fragment — final AI investment verdict + rule-based fallback."""

import json
import logging
import re

import streamlit as st

from src.ai.summarizer import _call_llm
from src.ui_components import with_status

logger = logging.getLogger(__name__)


_ACTION_COLORS = {
    "强烈买入": ("#3ECF8E", "rgba(62,207,142,0.08)"),
    "买入":     ("#3ECF8E", "rgba(62,207,142,0.06)"),
    "增持":     ("#3ECF8E", "rgba(62,207,142,0.04)"),
    "持有":     ("#60A5FA", "rgba(96,165,250,0.06)"),
    "减持":     ("#F5A623", "rgba(245,166,35,0.06)"),
    "卖出":     ("#EF4444", "rgba(239,68,68,0.06)"),
    "强烈卖出": ("#EF4444", "rgba(239,68,68,0.08)"),
    "观望":     ("#C9A962", "rgba(201,169,98,0.06)"),
}


@st.fragment
def render_ai_verdict(symbol, name, market, price, change, moat, normalized, result, provider):
    """Render the final AI investment recommendation card for a stock."""
    verdict_key = "ai_verdict_{}".format(symbol)

    if verdict_key not in st.session_state:
        if provider:
            with with_status("AI 综合投资建议生成中...", complete_label="投资建议已就绪"):
                st.session_state[verdict_key] = _generate_verdict(
                    symbol, name, market, price, change, moat, normalized, result, provider
                )
        else:
            st.session_state[verdict_key] = _local_verdict(
                symbol, name, price, change, moat, normalized, result
            )

    verdict_data = st.session_state.get(verdict_key, {})
    if not verdict_data:
        return

    action = verdict_data.get("action", "观望")
    confidence = verdict_data.get("confidence", "中")
    reason = verdict_data.get("reason", "")
    details = verdict_data.get("details", "")

    text_color, bg_color = _ACTION_COLORS.get(action, ("#C9A962", "rgba(201,169,98,0.06)"))

    st.markdown("---")

    st.markdown(
        '<div style="background:' + bg_color + ';border:1px solid ' + text_color + '44;'
        'border-radius:8px;padding:20px 24px;margin:8px 0;">'
        '<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">'
        '<div style="font-size:1.3rem;font-weight:700;color:' + text_color + ';letter-spacing:2px;'
        'padding:6px 18px;background:' + text_color + '18;border-radius:4px;">' + action + '</div>'
        '<div style="font-size:0.72rem;color:#8A8A96;letter-spacing:1px;">置信度: ' + confidence + '</div>'
        '<div style="flex:1;min-width:200px;font-size:0.92rem;color:#BDBDBD;line-height:1.6;">' + reason + '</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    if details:
        with st.expander("查看 AI 详细分析依据", expanded=True):
            st.markdown(details)

    if st.button("刷新 AI 建议", key="refresh_verdict_{}".format(symbol)):
        del st.session_state[verdict_key]
        st.rerun()


def _generate_verdict(symbol, name, market, price, change, moat, normalized, result, provider):
    """Call the LLM for a structured verdict; falls back to local rules on failure."""
    tech = result.tech_signal

    pe = normalized.get("pe_trailing")
    pb = normalized.get("pb")
    roe = normalized.get("roe")
    pm = normalized.get("profit_margin")
    gm = normalized.get("gross_margin")
    dte = normalized.get("debt_to_equity")
    cr = normalized.get("current_ratio")
    rg = normalized.get("revenue_growth")
    eg = normalized.get("earnings_growth")
    rsi = tech.get("rsi")
    trend = tech.get("trend", "unknown")
    roe_hist = normalized.get("roe_history", [])

    def _v(val, suffix=""):
        if val is None:
            return "N/A"
        return str(round(val, 2)) + suffix

    prompt = (
        "你是一位拥有30年经验的巴菲特风格首席投资顾问。"
        "你必须给出**明确、直接、有说服力**的投资建议，不能模棱两可。\n\n"
        "## 股票信息\n"
        "股票: " + symbol + " (" + name + ")\n"
        "当前股价: " + str(price) + " (今日" + ("+" if change >= 0 else "") + str(round(change, 2)) + "%)\n"
        "市场: " + {"us": "美股", "hk": "港股", "a_share": "A股"}.get(market, market) + "\n\n"
        "## 护城河评分\n"
        "总分: " + str(moat["percentage"]) + "/100 (" + moat["grade"] + "级 · " + moat["label"] + ")\n"
    )

    for dim_name, info in moat.get("scores", {}).items():
        prompt += "- " + dim_name + ": " + str(info["score"]) + "/" + str(info["max"]) + "\n"

    prompt += (
        "\n## 关键财务指标\n"
        "PE: " + _v(pe) + " | PB: " + _v(pb) + " | ROE: " + _v(roe, "%") + "\n"
        "净利率: " + _v(pm, "%") + " | 毛利率: " + _v(gm, "%") + "\n"
        "负债权益比: " + _v(dte) + " | 流动比率: " + _v(cr) + "\n"
        "营收增长: " + _v(rg, "%") + " | 利润增长: " + _v(eg, "%") + "\n"
        "ROE历史: " + str(roe_hist) + "\n\n"
        "## 技术面\n"
        "趋势: " + trend + " | RSI: " + _v(rsi) + "\n"
        "技术信号: " + "; ".join(tech.get("signals", [])) + "\n\n"
        "---\n"
        "请严格按以下JSON格式输出，不输出其他内容：\n"
        '{\n'
        '  "action": "强烈买入/买入/增持/持有/减持/卖出/强烈卖出/观望",\n'
        '  "confidence": "高/中/低",\n'
        '  "reason": "一句话核心理由，不超过40字，必须引用具体数据（如PE、ROE等）",\n'
        '  "details": "详细分析，用markdown格式，包含以下内容：\\n'
        '## 核心逻辑\\n[为什么给出这个建议，结合护城河评分和当前股价]\\n\\n'
        '## 基本面判断\\n[ROE/利润率/成长性的具体解读]\\n\\n'
        '## 估值判断\\n[当前PE/PB是贵了还是便宜了，对比历史和行业]\\n\\n'
        '## 技术面配合\\n[趋势和RSI是否支持当前建议]\\n\\n'
        '## 风险提示\\n[最需要警惕的1-2个风险]\\n\\n'
        '## 操作方案\\n[具体建议：建仓/加仓/减仓/清仓，建议仓位比例]"\n'
        '}\n\n'
        "核心要求：\n"
        "1. 建议必须明确，不能说\"可以考虑\"\"建议观察\"这种废话\n"
        "2. reason必须引用至少2个具体数据\n"
        "3. 如果基本面好但估值贵，说\"持有但不追高\"；如果基本面好且估值低，果断说\"买入\"\n"
        "4. 如果基本面差，不管技术面如何，都不建议买入"
    )

    try:
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=1200)
        text = text.strip()
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text).strip()
        return json.loads(text)
    except Exception as e:
        logger.warning("AI verdict failed for %s: %s", symbol, e)
        return _local_verdict(symbol, name, price, change, moat, normalized, result)


def _local_verdict(symbol, name, price, change, moat, normalized, result):
    """Rule-based verdict for when no AI provider is configured."""
    score = moat["percentage"]
    grade = moat["grade"]
    pe = normalized.get("pe_trailing")
    roe = normalized.get("roe")
    trend = result.tech_signal.get("trend", "unknown")
    rsi = result.tech_signal.get("rsi")

    if score >= 75 and pe and pe < 20 and trend in ("bullish", "neutral"):
        action, confidence = "买入", "高"
        reason = "护城河评分{:.0f}分({}级)，PE仅{:.1f}倍，基本面优秀且估值合理".format(score, grade, pe)
    elif score >= 65 and pe and pe < 25:
        action, confidence = "增持", "中"
        reason = "护城河{:.0f}分，PE {:.1f}倍处于合理区间，值得逐步建仓".format(score, pe)
    elif score >= 65 and pe and pe >= 25:
        action, confidence = "持有", "中"
        reason = "护城河{:.0f}分({})，但PE {:.1f}偏高，持有不追高".format(score, grade, pe)
    elif score >= 50:
        action, confidence = "观望", "中"
        reason = "护城河{:.0f}分，品质尚可但不够突出，等待更好价格".format(score)
    elif score >= 35:
        action, confidence = "减持", "中"
        reason = "护城河仅{:.0f}分({}级)，竞争优势不明显".format(score, grade)
    else:
        action, confidence = "卖出", "高"
        reason = "护城河{:.0f}分({}级)，不符合价值投资标准".format(score, grade)

    if rsi and rsi < 30 and action in ("买入", "增持"):
        reason += "，且RSI={:.0f}超卖，短期反弹概率大".format(rsi)
        confidence = "高"
    elif rsi and rsi > 70 and action in ("买入", "增持"):
        action = "持有"
        reason += "，但RSI={:.0f}超买，建议等回调再加仓".format(rsi)

    details = (
        "## 核心逻辑\n"
        "护城河综合评分 **{:.0f}/100** ({}级 · {})".format(score, grade, moat["label"])
        + ("，当前PE **{:.1f}**".format(pe) if pe else "")
        + ("，ROE **{:.1f}%**".format(roe) if roe else "")
        + "\n\n*（此为本地规则引擎生成，配置 API Key 后可获得 AI 深度分析）*"
    )

    return {"action": action, "confidence": confidence, "reason": reason, "details": details}
