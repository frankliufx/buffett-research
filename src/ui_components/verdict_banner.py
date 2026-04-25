"""Verdict banner — the canonical "what should I do?" surface.

Generalized from `src/ui_ashare/decision_banner.py`. Used at the top of
any analysis surface to answer the user's #1 question — Buy / Hold /
Avoid — before they have to read anything else.

Decision-first principle (north star #1): the verdict banner is the
*only* element guaranteed at every viewport top. Everything else is
supporting material.
"""

from __future__ import annotations

import html as _html
from typing import Literal, Optional

import streamlit as st


_ACTION_TONE = {
    # action → (accent_color, soft_bg)
    "强烈买入": ("#3ECF8E", "rgba(62,207,142,0.10)"),
    "买入":     ("#3ECF8E", "rgba(62,207,142,0.08)"),
    "增持":     ("#3ECF8E", "rgba(62,207,142,0.06)"),
    "ACCUMULATE": ("#3ECF8E", "rgba(62,207,142,0.06)"),
    "BUY":      ("#3ECF8E", "rgba(62,207,142,0.08)"),
    "持有":     ("#5BA4CF", "rgba(91,164,207,0.06)"),
    "HOLD":     ("#5BA4CF", "rgba(91,164,207,0.06)"),
    "观望":     ("#C9A962", "rgba(201,169,98,0.06)"),
    "WATCH":    ("#C9A962", "rgba(201,169,98,0.06)"),
    "减持":     ("#F5A623", "rgba(245,166,35,0.06)"),
    "REDUCE":   ("#F5A623", "rgba(245,166,35,0.06)"),
    "卖出":     ("#EF4444", "rgba(239,68,68,0.06)"),
    "回避":     ("#EF4444", "rgba(239,68,68,0.06)"),
    "AVOID":    ("#EF4444", "rgba(239,68,68,0.06)"),
}


def _tone(action: str) -> tuple[str, str]:
    return _ACTION_TONE.get(action, ("#C9A962", "rgba(201,169,98,0.06)"))


def render_verdict_banner(
    action: str,
    *,
    confidence: Optional[str] = None,
    rationale: Optional[str] = None,
    score: Optional[float] = None,
    score_label: str = "score",
    sticky: bool = False,
    extra_chips: Optional[list[str]] = None,
) -> None:
    """Render the canonical verdict banner.

    Args:
        action:      Verdict label, e.g. "BUY" / "买入" / "HOLD" / "AVOID".
                     Color is matched from a known set; unknown actions get gold.
        confidence:  Optional confidence indicator ("HIGH" / "高" / "85%").
        rationale:   One-sentence reason; ≤ 80 chars displays inline,
                     longer text wraps.
        score:       Optional 0-100 score rendered on the right side.
        score_label: Label for the score (default "score"; can be e.g. "MOAT").
        sticky:      If True, banner sticks to the top of the viewport on scroll.
        extra_chips: Optional list of small chip labels appended below the rationale
                     (e.g. theme tags or signal markers).
    """
    accent, bg = _tone(action)
    sticky_cls = "sticky-top" if sticky else ""

    confidence_html = ""
    if confidence:
        confidence_html = (
            f'<span style="font-size:0.65rem;letter-spacing:1px;color:{accent};'
            f'border:1px solid {accent}55;background:{accent}12;padding:2px 8px;'
            f'border-radius:3px;text-transform:uppercase;">{_html.escape(confidence)}</span>'
        )

    rationale_html = ""
    if rationale:
        rationale_html = (
            f'<div style="font-size:0.88rem;color:var(--ink-primary);'
            f'line-height:1.55;margin-top:6px;">{_html.escape(rationale)}</div>'
        )

    chips_html = ""
    if extra_chips:
        chip_items = "".join(
            f'<span style="display:inline-block;font-size:0.6rem;letter-spacing:0.5px;'
            f'color:var(--ink-secondary);border:1px solid var(--ink-disabled);'
            f'padding:2px 8px;border-radius:3px;margin-right:6px;margin-top:6px;">'
            f'{_html.escape(c)}</span>'
            for c in extra_chips
        )
        chips_html = f'<div style="margin-top:8px;">{chip_items}</div>'

    score_block = ""
    if score is not None:
        score_block = f"""
        <div style="text-align:right;flex-shrink:0;padding-left:16px;">
          <div class="eyebrow" style="margin-bottom:2px;">{_html.escape(score_label)}</div>
          <div class="display-serif num" style="font-size:2rem;color:{accent};">
            {score:.0f}<span style="font-size:0.85rem;color:var(--ink-muted);font-weight:300;"> /100</span>
          </div>
        </div>
        """

    st.markdown(
        f"""
<div class="{sticky_cls}" style="
  background:linear-gradient(135deg, var(--surface-raised) 0%, var(--surface-canvas) 100%);
  border:1px solid var(--ink-disabled);
  border-left:3px solid {accent};
  border-radius:var(--r-md);
  padding:14px 18px;
  margin-bottom:18px;
">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:14px;">
    <div style="flex:1;min-width:0;">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        <span class="display-serif" style="font-size:1.5rem;color:{accent};line-height:1;letter-spacing:0.04em;">
          {_html.escape(action)}
        </span>
        {confidence_html}
      </div>
      {rationale_html}
      {chips_html}
    </div>
    {score_block}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
