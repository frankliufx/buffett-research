"""Stock chip — the 36px row used in watchlists, search results, portfolio.

Layout: [ticker | name | price | Δ% | grade pill | optional sparkline]

This is the foundational unit for Phase 4 flywheel surfacing — anywhere
we need to show a list of stocks with at-a-glance state, this is the
component.
"""

from __future__ import annotations

import html as _html
from typing import Optional

import streamlit as st


def _delta_color(pct: Optional[float]) -> str:
    if pct is None:
        return "var(--ink-muted)"
    return "var(--bull)" if pct >= 0 else "var(--bear)"


def _grade_color(grade: Optional[str]) -> str:
    return {
        "S": "#C9A962",
        "A": "#3ECF8E",
        "B": "#5BA4CF",
        "C": "#F5A623",
        "D": "#EF4444",
    }.get((grade or "").upper(), "var(--ink-muted)")


def render_stock_chip(
    ticker: str,
    name: str = "",
    price: Optional[float] = None,
    change_pct: Optional[float] = None,
    grade: Optional[str] = None,
    *,
    currency: str = "$",
    on_click_key: Optional[str] = None,
) -> None:
    """Single 36px stock-row chip.

    Use inside a column / list. For a row of N chips, wrap in
    `st.columns(N)` and call once per column.
    """
    delta_color = _delta_color(change_pct)
    grade_color = _grade_color(grade)

    if change_pct is None:
        delta_str = "—"
    else:
        delta_str = ("+" if change_pct >= 0 else "") + f"{change_pct:.2f}%"

    price_str = f"{currency}{price:,.2f}" if price is not None else "—"

    grade_html = ""
    if grade:
        grade_html = (
            f'<span style="font-family:var(--font-sans);font-size:0.65rem;font-weight:700;'
            f'color:{grade_color};border:1px solid {grade_color}66;background:{grade_color}10;'
            f'padding:1px 7px;border-radius:3px;letter-spacing:0.5px;">{_html.escape(grade.upper())}</span>'
        )

    st.markdown(
        f"""
<div style="
  display:flex;align-items:center;justify-content:space-between;gap:12px;
  height:36px;padding:0 12px;
  background:var(--surface-raised);
  border:1px solid var(--ink-disabled);
  border-radius:var(--r-sm);
  transition:background 120ms;
" onmouseover="this.style.background='var(--surface-hover)'"
   onmouseout="this.style.background='var(--surface-raised)'">
  <div style="display:flex;align-items:baseline;gap:10px;min-width:0;flex:1;">
    <span class="num" style="font-size:0.82rem;font-weight:600;color:var(--ink-primary);">
      {_html.escape(ticker)}
    </span>
    <span style="font-size:0.75rem;color:var(--ink-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
      {_html.escape(name)}
    </span>
  </div>
  <div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">
    <span class="num" style="font-size:0.78rem;color:var(--ink-primary);">{price_str}</span>
    <span class="num" style="font-size:0.72rem;font-weight:500;color:{delta_color};min-width:54px;text-align:right;">{delta_str}</span>
    {grade_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
