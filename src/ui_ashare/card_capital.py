"""资金面卡片 — 北向 / 主力 / 龙虎榜 + inline SVG sparklines。

We use inline SVG (not Plotly) for the sparklines so the entire card
renders as one continuous st.markdown block — no fragmented borders
or layout gaps. Each sparkline is ~20 days, ~120px wide, color-coded
by sign (green up / red down).

UX rules:
- Numbers colored by sign of the value
- Each net-flow row pairs a number with a sparkline of the trend
- Consensus score is rendered as a colored pill in the top-right
- Per-source fetch failures show "⚠ 数据加载失败" inline
"""

from __future__ import annotations

import html as _html
from typing import Optional

import streamlit as st

from schemas.policy import CapitalFlow, CapitalFlowDay


_GREEN = "#3ECF8E"
_RED = "#EF4444"
_GRAY = "#5A5A6A"


def _fmt_yuan(v: Optional[float]) -> str:
    if v is None:
        return "—"
    sign = "" if v >= 0 else "-"
    a = abs(v)
    if a >= 1e8:
        return f"{sign}{a/1e8:.2f}亿"
    if a >= 1e4:
        return f"{sign}{a/1e4:.0f}万"
    return f"{sign}{a:.0f}"


def _sign_color(v: Optional[float]) -> str:
    if v is None:
        return _GRAY
    return _GREEN if v >= 0 else _RED


def _svg_sparkline(history: list[CapitalFlowDay], days: int = 20,
                    width: int = 120, height: int = 28) -> str:
    """Render a sign-colored bar sparkline as inline SVG.

    Empty / no-data → returns a small placeholder dashes line so the
    layout doesn't shift.
    """
    if not history:
        return (
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<line x1="0" y1="{height/2}" x2="{width}" y2="{height/2}" '
            f'stroke="#262630" stroke-width="1" stroke-dasharray="2 3"/></svg>'
        )

    tail = history[-days:]
    vals = [d.net_inflow_yuan or 0 for d in tail]
    if not vals or all(v == 0 for v in vals):
        return (
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<line x1="0" y1="{height/2}" x2="{width}" y2="{height/2}" '
            f'stroke="#262630" stroke-width="1"/></svg>'
        )

    n = len(vals)
    bar_w = max(1, (width - (n - 1) * 1) / n)
    peak = max(abs(min(vals)), abs(max(vals)), 1)
    mid = height / 2

    bars = []
    for i, v in enumerate(vals):
        color = _GREEN if v >= 0 else _RED
        scaled = abs(v) / peak * (mid - 1)
        x = i * (bar_w + 1)
        if v >= 0:
            y = mid - scaled
            h = scaled
        else:
            y = mid
            h = scaled
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{max(h,0.5):.1f}" fill="{color}"/>'
        )
    bars.append(f'<line x1="0" y1="{mid}" x2="{width}" y2="{mid}" stroke="#1E1E2A" stroke-width="0.5"/>')
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        + "".join(bars) + "</svg>"
    )


def _row_with_spark(label: str, value_text: str, value_color: str,
                    sub: str, sparkline_svg: str) -> str:
    sub_html = (
        f'<div style="font-size:0.55rem;color:#5A5A6A;letter-spacing:1px;margin-top:1px;">{_html.escape(sub)}</div>'
        if sub else ""
    )
    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid #14141C;">
  <div style="min-width:0;">
    <div style="font-size:0.6rem;color:#8A8A9A;letter-spacing:1.5px;text-transform:uppercase;">{_html.escape(label)}</div>
    {sub_html}
  </div>
  <div style="display:flex;align-items:center;gap:10px;">
    <div style="line-height:0;">{sparkline_svg}</div>
    <div style="font-size:0.95rem;font-weight:600;color:{value_color};text-align:right;min-width:64px;">{value_text}</div>
  </div>
</div>
"""


def _row_simple(label: str, value_text: str, value_color: str, sub: str = "") -> str:
    sub_html = (
        f'<div style="font-size:0.55rem;color:#5A5A6A;letter-spacing:1px;margin-top:1px;">{_html.escape(sub)}</div>'
        if sub else ""
    )
    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 0;border-bottom:1px solid #14141C;">
  <div>
    <div style="font-size:0.6rem;color:#8A8A9A;letter-spacing:1.5px;text-transform:uppercase;">{_html.escape(label)}</div>
    {sub_html}
  </div>
  <div style="font-size:0.95rem;font-weight:600;color:{value_color};text-align:right;">{value_text}</div>
</div>
"""


def _consensus_pill(score: Optional[float], label: Optional[str]) -> str:
    if score is None:
        return (
            '<span style="font-size:0.55rem;color:#5A5A6A;letter-spacing:1.5px;'
            'border:1px dashed #2A2A3A;padding:3px 8px;border-radius:2px;">数据不足</span>'
        )
    if score >= 65:
        color = _GREEN
    elif score >= 35:
        color = "#C9A962"
    else:
        color = _RED
    return (
        f'<span style="font-size:0.65rem;color:{color};letter-spacing:1.5px;'
        f'border:1px solid {color}55;background:{color}10;padding:3px 10px;border-radius:2px;">'
        f'{score:.0f} · {_html.escape(label or "")}</span>'
    )


def render_capital_card(symbol: str, flow: Optional[CapitalFlow] = None) -> None:
    """Render the capital-flow card."""
    if flow is None:
        st.markdown(
            f"""
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 22px;height:100%;">
  <div style="font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-bottom:10px;">💰 资金面</div>
  <div style="font-size:0.78rem;color:#5A5A6A;font-style:italic;">资金数据未加载（{_html.escape(symbol)}）。</div>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    nb_5d_color = _sign_color(flow.northbound_5d_yuan)
    nb_20d_color = _sign_color(flow.northbound_20d_yuan)
    main_5d_color = _sign_color(flow.main_5d_yuan)

    pct_text = "—" if flow.northbound_holding_pct is None else f"{flow.northbound_holding_pct:.2f}%"
    pct_sub = ""
    if flow.northbound_holding_pct is not None:
        if flow.northbound_holding_pct >= 3:
            pct_sub = "重仓"
        elif flow.northbound_holding_pct >= 1:
            pct_sub = "标配"
        else:
            pct_sub = "轻仓"

    lhb_text = "—" if flow.lhb_30d_count is None else f"{flow.lhb_30d_count} 次"
    lhb_color = _GREEN if (flow.lhb_30d_count or 0) >= 2 else _GRAY

    err_html = ""
    if flow.fetch_errors:
        err_html = (
            f'<div style="font-size:0.55rem;color:#EF4444;letter-spacing:1px;margin-top:10px;border-top:1px solid #14141C;padding-top:8px;">'
            f'⚠ 部分数据加载失败: {", ".join(_html.escape(e) for e in flow.fetch_errors)}</div>'
        )

    nb_spark = _svg_sparkline(flow.northbound_history)
    main_spark = _svg_sparkline(flow.main_history)

    st.markdown(
        f"""
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 22px;height:100%;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
    <div style="font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;">💰 资金面</div>
    <div>{_consensus_pill(flow.consensus_score, flow.consensus_label)}</div>
  </div>
  {_row_simple("北向持股占比", pct_text, _GRAY if flow.northbound_holding_pct is None else "#E8E8F0", pct_sub)}
  {_row_with_spark("北向 5 日净流入", _fmt_yuan(flow.northbound_5d_yuan), nb_5d_color, "近 20 日趋势", nb_spark)}
  {_row_simple("北向 20 日净流入", _fmt_yuan(flow.northbound_20d_yuan), nb_20d_color)}
  {_row_with_spark("主力 5 日净流入", _fmt_yuan(flow.main_5d_yuan), main_5d_color, "近 20 日趋势", main_spark)}
  {_row_simple("龙虎榜 30 日次数", lhb_text, lhb_color)}
  {err_html}
</div>
""",
        unsafe_allow_html=True,
    )
