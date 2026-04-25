"""风险面卡片 — ST / 实控人 / 业绩预警 / CSRC 处罚 + 综合风险等级。

UX rules:
- Top-right: a "风险等级" badge (低/中/高/极高) with phase-style color
- Each risk dimension shows status as a small chip + supporting text
- Reasons list is rendered as bullet points so the user sees WHY the
  level is what it is
- Per-source fetch failures show inline at the bottom
"""

from __future__ import annotations

import html as _html
from typing import Optional

import streamlit as st

from schemas.policy import RegulatoryStatus


_LOW = "#3ECF8E"
_GRAY = "#5A5A6A"


_CONTROLLER_COLOR = {
    "央企":      "#C9A962",
    "地方国企":  "#5B8DB8",
    "民营企业":  "#E8E8F0",
    "外资企业":  "#A78BFA",
    "公众企业":  "#7C7C8E",
    "无实控人":  "#EF4444",
    "未知":      "#5A5A6A",
}


def _level_pill(level: str, color: str) -> str:
    return (
        f'<span style="font-size:0.65rem;color:{color};letter-spacing:1.5px;'
        f'border:1px solid {color}66;background:{color}12;padding:3px 12px;'
        f'border-radius:2px;font-weight:600;">{_html.escape(level)} 风险</span>'
    )


def _status_chip(text: str, color: str, *, dashed: bool = False) -> str:
    border = "dashed" if dashed else "solid"
    return (
        f'<span style="display:inline-block;font-size:0.6rem;color:{color};'
        f'letter-spacing:1px;border:1px {border} {color}55;background:{color}10;'
        f'padding:2px 8px;border-radius:2px;">{_html.escape(text)}</span>'
    )


def _row(label: str, chip_html: str, sub: str = "") -> str:
    sub_html = (
        f'<div style="font-size:0.6rem;color:#7A7A8A;line-height:1.45;margin-top:3px;">{_html.escape(sub)}</div>'
        if sub else ""
    )
    return f"""
<div style="padding:10px 0;border-bottom:1px solid #14141C;">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
    <div style="font-size:0.6rem;color:#8A8A9A;letter-spacing:1.5px;text-transform:uppercase;">{_html.escape(label)}</div>
    <div>{chip_html}</div>
  </div>
  {sub_html}
</div>
"""


def render_risk_card(symbol: str, status: Optional[RegulatoryStatus] = None) -> None:
    """Render the regulatory-risk card."""
    if status is None:
        st.markdown(
            f"""
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 22px;height:100%;">
  <div style="font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-bottom:10px;">⚠️ 风险面</div>
  <div style="font-size:0.78rem;color:#5A5A6A;font-style:italic;">风险数据未加载（{_html.escape(symbol)}）。</div>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    # ── ST status row ─────────────────────────────────────────────────────
    if status.is_st is None:
        st_chip = _status_chip("数据缺失", _GRAY, dashed=True)
        st_sub = ""
    elif status.is_st:
        st_chip = _status_chip(status.st_label or "ST", "#EF4444")
        st_sub = "监管特别处理 — 退市风险加大"
    else:
        st_chip = _status_chip("正常", _LOW)
        st_sub = ""

    # ── Controller row ────────────────────────────────────────────────────
    ctype = status.controller_type
    ctype_color = _CONTROLLER_COLOR.get(ctype, _GRAY)
    ctype_chip = _status_chip(ctype, ctype_color, dashed=(ctype == "未知"))
    cname_sub = (status.controller_name or "")[:60]

    # ── Performance warning row ───────────────────────────────────────────
    if status.perf_warning:
        pw_chip = _status_chip(status.perf_warning, "#F5A623")
        pw_sub = "最近一期业绩预告异常"
    else:
        pw_chip = _status_chip("无预警", _LOW)
        pw_sub = ""

    # ── CSRC penalty row ──────────────────────────────────────────────────
    if status.csrc_penalty_count_3y is None:
        penalty_chip = _status_chip("A5.2 续接", _GRAY, dashed=True)
        penalty_sub = "数据源接入待续期 (CSRC API 不稳定)"
    elif status.csrc_penalty_count_3y == 0:
        penalty_chip = _status_chip("无记录", _LOW)
        penalty_sub = "近 3 年无 CSRC 处罚"
    else:
        penalty_chip = _status_chip(f"{status.csrc_penalty_count_3y} 次", "#F5A623")
        penalty_sub = (status.csrc_penalty_recent or "")[:60]

    # ── Reasons block (always visible, drives the level above) ────────────
    reasons_items = "".join(
        f'<li style="margin-bottom:3px;">{_html.escape(r)}</li>'
        for r in status.risk_reasons
    )
    reasons_html = (
        f'<div style="font-size:0.65rem;color:#8A8A9A;line-height:1.6;'
        f'margin-top:10px;border-top:1px solid #14141C;padding-top:8px;">'
        f'<div style="font-size:0.55rem;letter-spacing:1.5px;color:#5A5A6A;'
        f'text-transform:uppercase;margin-bottom:4px;">综合判定依据</div>'
        f'<ul style="margin:0;padding-left:14px;">{reasons_items}</ul></div>'
    )

    # ── Fetch error banner ────────────────────────────────────────────────
    err_html = ""
    if status.fetch_errors:
        err_html = (
            f'<div style="font-size:0.55rem;color:#EF4444;letter-spacing:1px;margin-top:8px;'
            f'border-top:1px solid #14141C;padding-top:6px;">'
            f'⚠ 部分数据加载失败: {", ".join(_html.escape(e) for e in status.fetch_errors)}</div>'
        )

    st.markdown(
        f"""
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 22px;height:100%;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
    <div style="font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;">⚠️ 风险面</div>
    <div>{_level_pill(status.risk_level, status.risk_color)}</div>
  </div>
  {_row("ST / 退市状态", st_chip, st_sub)}
  {_row("实控人性质", ctype_chip, cname_sub)}
  {_row("业绩预警", pw_chip, pw_sub)}
  {_row("CSRC 处罚（3年）", penalty_chip, penalty_sub)}
  {reasons_html}
  {err_html}
</div>
""",
        unsafe_allow_html=True,
    )
