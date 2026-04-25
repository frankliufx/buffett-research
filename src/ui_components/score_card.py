"""Score card — number + label + 20-day delta sparkline.

Replaces the ~5 different KPI styles currently in use across pages.
Use in a 3- or 4-column grid for at-a-glance dashboards.

Visual contract:
    ┌─────────────────────────┐
    │ EYEBROW LABEL           │
    │  84  /100               │  ← display-serif if accent_serif=True
    │ ▂▃▄▅▆▇█▇▅▃▂▁▂▃▄▅▆▇█▇▆▅ │  ← optional 20-day delta sparkline
    └─────────────────────────┘
"""

from __future__ import annotations

import html as _html
from typing import Iterable, Optional

import streamlit as st


def _spark_svg(values: list[float], width: int = 140, height: int = 28,
                color_pos: str = "#3ECF8E", color_neg: str = "#EF4444") -> str:
    """Tiny inline SVG sparkline. Sign-colored bars; works with any value range."""
    if not values:
        return f'<svg width="{width}" height="{height}"></svg>'
    n = len(values)
    bar_w = max(1, (width - (n - 1)) / n)
    peak = max(abs(min(values)), abs(max(values)), 1)
    mid = height / 2
    bars = []
    for i, v in enumerate(values):
        c = color_pos if v >= 0 else color_neg
        scaled = abs(v) / peak * (mid - 1)
        x = i * (bar_w + 1)
        if v >= 0:
            y = mid - scaled
            h = scaled
        else:
            y = mid
            h = scaled
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{max(h,0.5):.1f}" fill="{c}"/>'
        )
    bars.append(f'<line x1="0" y1="{mid}" x2="{width}" y2="{mid}" stroke="#1E1E2A" stroke-width="0.5"/>')
    return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">{"".join(bars)}</svg>'


def render_score_card(
    label: str,
    value: float,
    *,
    max_value: Optional[float] = 100,
    accent: str = "#C9A962",
    delta_history: Optional[Iterable[float]] = None,
    sub: Optional[str] = None,
    serif: bool = True,
) -> None:
    """A single score card (use in a column).

    Args:
        label:         Eyebrow label above the number ("MOAT", "POLICY", ...)
        value:         The headline number.
        max_value:     If given, displayed as "value/max" (e.g. "84/100").
        accent:        Color of the headline number.
        delta_history: Optional list of recent values; rendered as a sparkline.
        sub:           Optional sub-text below the number.
        serif:         Use Cormorant Garamond for the headline number (default True).
    """
    num_class = "display-serif num" if serif else "num"
    max_str = ""
    if max_value is not None:
        max_str = (
            f'<span style="font-size:0.7rem;color:var(--ink-muted);font-weight:300;"> /{int(max_value)}</span>'
        )
    sub_html = (
        f'<div class="caption" style="margin-top:2px;">{_html.escape(sub)}</div>'
        if sub else ""
    )
    spark_html = ""
    if delta_history is not None:
        spark_html = (
            f'<div style="margin-top:8px;line-height:0;">{_spark_svg(list(delta_history))}</div>'
        )

    # Display the headline number — integer-look if it's a clean integer, else 2dp.
    value_str = f"{value:.0f}" if float(value) == int(value) else f"{value:.2f}"

    st.markdown(
        f"""
<div style="
  background:var(--surface-raised);
  border:1px solid var(--ink-disabled);
  border-radius:var(--r-md);
  padding:14px 16px;
  height:100%;
">
  <div class="eyebrow" style="margin-bottom:6px;">{_html.escape(label)}</div>
  <div class="{num_class}" style="font-size:1.75rem;color:{accent};line-height:1;">
    {value_str}{max_str}
  </div>
  {sub_html}
  {spark_html}
</div>
""",
        unsafe_allow_html=True,
    )
