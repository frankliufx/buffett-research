"""综合判断横幅 — A股 4-card 面板的入口决策框。

Combines:
    - 主线对齐 level (核心主线 / 受益方向 / 暂无)
    - 主导政策周期 phase (爆发期 / 蓄势期 / 退坡期)
    - 一句话操作定调 (基于 phase × tier 的简单规则)

Renders directly into Streamlit context — caller does not need to wrap
in components.html.
"""

from __future__ import annotations

import html as _html

import streamlit as st

from schemas.policy import PolicyAlignment
from src.data.policy_lifecycle import aggregate_phase
from src.data.policy_themes import find_theme

from src.ui_ashare._base import GOLD, PHASE_COLOR


# Action heuristic — keyed on (level, phase). The text is intentionally
# directive ("...建议X") not advisory ("...可以考虑X"). Reviewed by user.
_ACTION = {
    ("核心主线", "爆发期"): "卡位主线 · 趋势内持有，关注下一催化窗口",
    ("核心主线", "蓄势期"): "提前布局 · 蓄势期估值低，等待爆发期兑现",
    ("核心主线", "退坡期"): "兑现收益 · 政策红利末段，警惕情绪溢价回吐",
    ("受益方向", "爆发期"): "顺势参与 · 仓位适度，避免错把题材当主线",
    ("受益方向", "蓄势期"): "跟踪等待 · 主线确认后再加仓",
    ("受益方向", "退坡期"): "减仓离场 · 政策驱动减弱，回归基本面定价",
    ("暂无明显政策主题", "未知"): "纯基本面驱动 · 政策面无显著加成或拖累",
}


def _action_text(level: str, phase: str) -> str:
    return _ACTION.get((level, phase), "无明显政策定调，按基本面/估值原则操作")


def render_decision_banner(alignment: PolicyAlignment) -> None:
    """Render the top-of-panel decision banner.

    Args:
        alignment: Typed `PolicyAlignment` from `get_policy_alignment(symbol)`.
    """
    matched_themes = [find_theme(m.theme_id) for m in alignment.matches]
    matched_themes = [t for t in matched_themes if t is not None]
    phase, phase_color = aggregate_phase(matched_themes)
    level = alignment.level
    score = alignment.score

    action = _action_text(level, phase)

    # Top-3 themes (by tier then concept hits)
    top_themes = alignment.matches[:3]
    chip_html = ""
    for m in top_themes:
        tier_color = {1: GOLD, 2: "#5B8DB8", 3: "#7C7C8E"}.get(m.tier, "#5A5A6A")
        chip_html += (
            f'<span style="display:inline-block;border:1px solid {tier_color}55;'
            f'background:{tier_color}10;color:{tier_color};font-size:0.65rem;'
            f'letter-spacing:1px;padding:3px 10px;border-radius:2px;margin-right:6px;">'
            f'{_html.escape(m.theme_name)} · {m.phase}</span>'
        )
    if not chip_html:
        chip_html = (
            '<span style="font-size:0.7rem;color:#5A5A6A;font-style:italic;">'
            '暂无匹配主题</span>'
        )

    st.markdown(
        f"""
<div style="
  background:linear-gradient(135deg,#0D0D14 0%,#12121C 100%);
  border:1px solid #1E1E2A;border-left:3px solid {phase_color};
  border-radius:4px;padding:18px 22px;margin-bottom:18px;
">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:18px;flex-wrap:wrap;">
    <div style="flex:1;min-width:240px;">
      <div style="font-size:0.5rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:4px;">
        政策综合判断
      </div>
      <div style="font-family:'Cormorant Garamond',Georgia,serif;font-size:1.5rem;font-weight:700;color:{phase_color};line-height:1.15;">
        {level} · {phase}
      </div>
      <div style="font-size:0.78rem;color:#C8C8D8;margin-top:8px;line-height:1.55;">
        {_html.escape(action)}
      </div>
      <div style="margin-top:10px;">{chip_html}</div>
    </div>
    <div style="text-align:right;flex-shrink:0;">
      <div style="font-size:0.5rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:2px;">
        对齐分
      </div>
      <div style="font-family:'Cormorant Garamond',Georgia,serif;font-size:2.4rem;font-weight:700;color:{phase_color};line-height:1;">
        {score:.0f}<span style="font-size:0.85rem;font-weight:300;color:#5A5A6A;">/100</span>
      </div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
