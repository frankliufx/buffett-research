"""资金面卡片 — 北向资金 / 龙虎榜 / 主力净流入。

A5.1 status: PLACEHOLDER. The real implementation (A5.2) will source from
akshare:
    - stock_hsgt_individual_em()        — per-stock 北向资金
    - stock_lhb_detail_em()              — 龙虎榜 detail
    - stock_individual_fund_flow()       — 主力净流入

For now we render a clearly-labeled "数据接入中" panel so the 4-card
layout is wired up and reviewable end-to-end.
"""

from __future__ import annotations

import streamlit as st


def render_capital_card(symbol: str) -> None:
    """Render the (placeholder) capital-flow card."""
    st.markdown(
        f"""
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 22px;height:100%;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
    <div style="font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;">
      💰 资金面
    </div>
    <div style="font-size:0.55rem;color:#7A7A8A;letter-spacing:1px;border:1px dashed #2A2A3A;padding:2px 6px;border-radius:2px;">
      A5.2
    </div>
  </div>
  <div style="font-size:0.78rem;color:#C8C8D8;line-height:1.65;">
    <b style="color:#E8E8F0;">即将接入：</b><br>
    · 北向资金近 5 / 20 日净流入<br>
    · 龙虎榜近 30 日上榜次数<br>
    · 主力资金近 5 日累计净流入<br>
    · 资金共识评分 (0-100)
  </div>
  <div style="font-size:0.6rem;color:#5A5A6A;margin-top:14px;border-top:1px solid #14141C;padding-top:8px;line-height:1.5;">
    <i>当前面板为 A5.1 占位结构；A5.2 将通过 akshare
    （<code style="color:#7A7A8A;">stock_hsgt_individual_em</code>、
    <code style="color:#7A7A8A;">stock_lhb_detail_em</code>）接入实时数据。</i>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
