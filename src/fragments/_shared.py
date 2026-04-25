"""Helpers shared between fragment modules and the analysis page shell.

Moved out of `pages/2_analysis.py` so both the trimmed shell and the new
`src/fragments/*.py` can import from a stable location.
"""

from src.ui_theme import COLORS

# Plotly dark theme. Used by candlestick + ROE history + RSI charts.
PLOT_LAYOUT = dict(
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=COLORS["text_secondary"], size=11),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10, color=COLORS["text_muted"])),
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
    yaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
)


def fmt_pct(val):
    return "{:.1f}%".format(val) if val is not None else "--"


def trend_label(t):
    return {"bullish": "BULLISH", "bearish": "BEARISH", "neutral": "NEUTRAL"}.get(t, "--")


def momentum_label(m):
    return {"strong": "STRONG", "weak": "WEAK", "overbought": "OVERBOUGHT", "oversold": "OVERSOLD"}.get(m, "--")


def format_number(n):
    if n is None:
        return "--"
    a = abs(float(n))
    s = "-" if float(n) < 0 else ""
    if a >= 1e12:
        return "{}{}T".format(s, round(a / 1e12, 1))
    if a >= 1e9:
        return "{}{}B".format(s, round(a / 1e9, 1))
    if a >= 1e6:
        return "{}{}M".format(s, round(a / 1e6, 1))
    if a >= 1e3:
        return "{}{}K".format(s, round(a / 1e3, 1))
    return "{}{}".format(s, round(a))


def format_revenue(n):
    """Format revenue estimates (USD)."""
    if n is None:
        return "--"
    a = abs(float(n))
    if a >= 1e9:
        return "${:.1f}B".format(a / 1e9)
    if a >= 1e6:
        return "${:.0f}M".format(a / 1e6)
    return "${:.0f}".format(a)
