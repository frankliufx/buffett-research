"""Page-level fragments extracted from `pages/2_analysis.py`.

Each module here owns one of the four analysis pillars:

    fundamental.py  — MOAT scorecard + Buffett/Duan checklist
    technical.py    — candlestick chart + trend analysis (with AI report)
    valuation.py    — DCF / verdict / insight cards (with AI insights)
    risk.py         — final AI verdict + local rule-based fallback

Shared helpers (formatters, plotly theme) live in `_shared.py`.

These were carved out of a 2045-line monolith to (a) keep each pillar
small enough to reason about in isolation and (b) let `@st.fragment`
re-runs scope to a single pillar instead of the whole page.
"""

from src.fragments.fundamental import render_moat_scorecard, render_valuation_reference
from src.fragments.technical import plot_candlestick, render_trend_analysis
from src.fragments.valuation import render_valuation_hero
from src.fragments.risk import render_ai_verdict

__all__ = [
    "render_moat_scorecard",
    "render_valuation_reference",
    "plot_candlestick",
    "render_trend_analysis",
    "render_valuation_hero",
    "render_ai_verdict",
]
