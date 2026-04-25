"""主题对齐卡片 — 显示股票命中的政策主题、tier、概念证据。"""

from __future__ import annotations

import html as _html

import streamlit as st

from schemas.policy import PolicyAlignment

from src.ui_ashare._base import GOLD


def _tier_meta(tier: int) -> tuple[str, str]:
    """Return (label, color) for a tier."""
    return {
        1: ("一级 · 核心主线", GOLD),
        2: ("二级 · 受益方向", "#5B8DB8"),
        3: ("三级 · 政策外延", "#7C7C8E"),
    }.get(tier, ("未分级", "#5A5A6A"))


def render_alignment_card(alignment: PolicyAlignment) -> None:
    """Render the 'theme alignment' card."""
    if not alignment.matches:
        st.markdown(
            """
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 22px;height:100%;">
  <div style="font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-bottom:12px;">
    📜 主题对齐
  </div>
  <div style="font-size:0.8rem;color:#5A5A6A;font-style:italic;line-height:1.6;">
    暂无匹配的政策主题。该股票当前未命中
    <code>data/cn_policy_themes.yaml</code> 中的任一关键词。
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    rows = ""
    for m in alignment.matches[:5]:
        label, color = _tier_meta(m.tier)
        concepts = " · ".join(_html.escape(c) for c in m.matched_concepts[:3])
        if len(m.matched_concepts) > 3:
            concepts += f' · <span style="color:#5A5A6A;">+{len(m.matched_concepts)-3}</span>'
        rows += f"""
<div style="border-bottom:1px solid #14141C;padding:10px 0;">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px;">
    <div style="font-size:0.85rem;color:#E8E8F0;font-weight:600;">{_html.escape(m.theme_name)}</div>
    <span style="font-size:0.55rem;letter-spacing:1px;color:{color};border:1px solid {color}55;padding:2px 8px;border-radius:2px;">{label}</span>
  </div>
  <div style="font-size:0.68rem;color:#8A8A9A;line-height:1.5;">
    {concepts}
  </div>
</div>
"""

    extra_count = max(0, len(alignment.matches) - 5)
    extra_html = (
        f'<div style="font-size:0.65rem;color:#5A5A6A;margin-top:8px;">'
        f'+{extra_count} 个其他主题</div>'
        if extra_count else ""
    )

    st.markdown(
        f"""
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 22px;height:100%;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
    <div style="font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;">
      📜 主题对齐
    </div>
    <div style="font-size:0.6rem;color:#8A8A9A;">命中 {len(alignment.matches)} 个主题</div>
  </div>
  {rows}
  {extra_html}
</div>
""",
        unsafe_allow_html=True,
    )
