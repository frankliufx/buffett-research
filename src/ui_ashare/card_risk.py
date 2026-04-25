"""风险面卡片 — ST/退市预警 + 实控人性质 + 监管处罚记录。

A5.1 status: PLACEHOLDER. Real implementation (A5.2) sources:
    - stock_zh_a_st_em()              — ST / *ST list
    - stock_pre_warning_em()          — 业绩预亏 / 退市预警
    - stock_individual_info_em()      — 实控人 / 控股股东类型
    - stock_csrc_punish_em()          — CSRC 处罚记录

For now: rendered as a structured "to-be-wired" placeholder.
"""

from __future__ import annotations

import streamlit as st


def render_risk_card(symbol: str) -> None:
    """Render the (placeholder) regulatory-risk card."""
    st.markdown(
        f"""
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 22px;height:100%;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
    <div style="font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;">
      ⚠️ 风险面
    </div>
    <div style="font-size:0.55rem;color:#7A7A8A;letter-spacing:1px;border:1px dashed #2A2A3A;padding:2px 6px;border-radius:2px;">
      A5.2
    </div>
  </div>
  <div style="font-size:0.78rem;color:#C8C8D8;line-height:1.65;">
    <b style="color:#E8E8F0;">即将接入：</b><br>
    · ST / *ST / 退市预警状态<br>
    · 实控人性质（央企 / 地方国企 / 民企 / 外资）<br>
    · 近 3 年 CSRC 处罚 / 警示函记录<br>
    · 持续督导期状态
  </div>
  <div style="font-size:0.6rem;color:#5A5A6A;margin-top:14px;border-top:1px solid #14141C;padding-top:8px;line-height:1.5;">
    <i>当前面板为 A5.1 占位结构；A5.2 将接入 akshare 监管数据，并在风险等级提升时
    （ST / 受罚 / 民企遭遇行业整顿）以红框警示。</i>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
