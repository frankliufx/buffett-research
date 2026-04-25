"""估值 fragment — DCF verdict, price spectrum, AI insight cards, scenarios."""

import streamlit as st
import streamlit.components.v1 as components

from src.ai.summarizer import get_ai_insights
from src.analysis.valuation import calc_dcf
from src.ui_components import with_status
from src.ui_valuation import (
    render_valuation_verdict,
    render_price_spectrum,
    render_insight_cards,
    render_scenario_cards,
    render_assumptions_panel,
)


@st.fragment
def render_valuation_hero(symbol, name, market, price, fundamentals, normalized, quote,
                          tech_signal=None, provider=None):
    """Valuation decision hub — anchored just below the stock header.

    Render strategy: numeric panels paint immediately; the AI insight text
    streams in via `with_status` without blocking the rest of the page.
    """
    currency_map = {"us": "$", "hk": "HK$", "a_share": "¥"}
    currency = currency_map.get(market, "$")

    dcf = calc_dcf(price, fundamentals, normalized)

    # 1. Verdict banner — paint immediately
    verdict_html = render_valuation_verdict(dcf, symbol, name, currency)
    components.html(verdict_html, height=200, scrolling=False)

    # 2. Price spectrum — paint immediately
    spectrum_html = render_price_spectrum(dcf, quote, currency)
    if spectrum_html:
        components.html(spectrum_html, height=200, scrolling=False)

    # 3. Insight cards — quantitative parts first, AI text on demand
    insights_key = "ai_insights_{}".format(symbol)
    ai_insights = st.session_state.get(insights_key)

    if ai_insights is None and provider and provider.api_key:
        with with_status("AI 智能洞察生成中...", complete_label="AI 洞察已生成"):
            ai_insights = get_ai_insights(
                symbol, name, price, fundamentals, normalized,
                tech_signal or {}, dcf, provider)
            st.session_state[insights_key] = ai_insights

    insight_html = render_insight_cards(
        price, fundamentals, normalized, tech_signal or {}, dcf, quote,
        currency, ai_insights=ai_insights)
    components.html(insight_html, height=620, scrolling=False)

    # 4. Three-scenario + assumptions — collapse for detail
    if dcf and dcf.get("method") != "insufficient":
        with st.expander("Scenario Analysis & Assumptions", expanded=False):
            scenario_html = render_scenario_cards(dcf, currency)
            if scenario_html:
                components.html(scenario_html, height=260, scrolling=False)
            assumptions_html = render_assumptions_panel(dcf)
            if assumptions_html:
                components.html(assumptions_html, height=300, scrolling=False)
