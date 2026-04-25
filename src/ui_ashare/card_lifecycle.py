"""政策周期卡片 — 信号灯 (●●○) + 文字标签 + 关键日期。"""

from __future__ import annotations

import html as _html

import streamlit as st

from schemas.policy import PolicyAlignment
from src.data.policy_lifecycle import lifecycle_signal
from src.data.policy_themes import find_theme

from src.ui_ashare._base import days_ago


def _light(level: int, color: str) -> str:
    """Render a 3-dot signal strip — `level` of 0/1/2 lights up that many."""
    dots = []
    for i in range(2):
        on = i < level
        c = color if on else "#262630"
        dots.append(f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{c};margin:0 2px;"></span>')
    return "".join(dots)


def render_lifecycle_card(alignment: PolicyAlignment) -> None:
    """Render the 'policy lifecycle' card with traffic-light strips."""
    if not alignment.matches:
        st.markdown(
            """
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 22px;height:100%;">
  <div style="font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-bottom:12px;">
    🌗 政策周期
  </div>
  <div style="font-size:0.8rem;color:#5A5A6A;font-style:italic;line-height:1.6;">
    无匹配主题，无周期信号可计算。
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    rows = ""
    for m in alignment.matches[:4]:
        theme = find_theme(m.theme_id)
        if theme is None:
            continue
        sig = lifecycle_signal(theme)

        past_strip = _light(sig.past, sig.color)
        curr_strip = _light(sig.current, sig.color)
        fut_strip = _light(sig.future, sig.color)

        last_label = (
            f"催化 {days_ago(theme.lifecycle.last_catalyst)}"
            if theme.lifecycle.last_catalyst else "催化 —"
        )
        next_label = (
            f"窗口 {days_ago(theme.lifecycle.next_window)}"
            if theme.lifecycle.next_window else "窗口 —"
        )

        rows += f"""
<div style="border-bottom:1px solid #14141C;padding:10px 0;">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:6px;">
    <div style="font-size:0.78rem;color:#E8E8F0;font-weight:500;">
      {_html.escape(theme.name)}
    </div>
    <span style="font-size:0.6rem;letter-spacing:1px;color:{sig.color};">{_html.escape(sig.label)}</span>
  </div>
  <div style="display:flex;align-items:center;gap:14px;font-size:0.55rem;color:#5A5A6A;letter-spacing:1px;text-transform:uppercase;">
    <span>近期 {past_strip}</span>
    <span>当下 {curr_strip}</span>
    <span>未来 {fut_strip}</span>
  </div>
  <div style="font-size:0.6rem;color:#7A7A8A;margin-top:4px;">
    {_html.escape(last_label)} · {_html.escape(next_label)}
  </div>
</div>
"""

    legend = (
        '<div style="display:flex;gap:14px;font-size:0.5rem;color:#5A5A6A;letter-spacing:1px;text-transform:uppercase;margin-top:10px;border-top:1px solid #14141C;padding-top:8px;">'
        '<span>● 强 ● 中 ○ 弱</span>'
        '<span style="color:#3ECF8E;">爆发期</span>'
        '<span style="color:#C9A962;">蓄势期</span>'
        '<span style="color:#EF4444;">退坡期</span>'
        '</div>'
    )

    st.markdown(
        f"""
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 22px;height:100%;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
    <div style="font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;">
      🌗 政策周期
    </div>
    <div style="font-size:0.6rem;color:#8A8A9A;">前 4 主题</div>
  </div>
  {rows}
  {legend}
</div>
""",
        unsafe_allow_html=True,
    )
