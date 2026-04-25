"""Build structured A股 context blocks for LLM prompts.

A5.3: turns the typed objects from A5.1/A5.2 (PolicyAlignment, CapitalFlow,
RegulatoryStatus) into a single context string the prompt can inject.
The goal is to remove every "请你判断政策周期" type instruction from the
prompt — those phrases were how we asked the LLM to invent data we didn't
have. Now data layer gives ground truth, prompt asks LLM to interpret it.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from schemas.policy import (
    CapitalFlow,
    PolicyAlignment,
    PolicyTheme,
    RegulatoryStatus,
)
from src.data.policy_lifecycle import aggregate_phase, lifecycle_signal
from src.data.policy_themes import find_theme


def _fmt_yuan(v: Optional[float]) -> str:
    if v is None:
        return "数据未取到"
    sign = "" if v >= 0 else "-"
    a = abs(v)
    if a >= 1e8:
        return f"{sign}{a/1e8:.2f}亿元"
    if a >= 1e4:
        return f"{sign}{a/1e4:.0f}万元"
    return f"{sign}{a:.0f}元"


def _alignment_block(alignment: Optional[PolicyAlignment]) -> str:
    if alignment is None or not alignment.matches:
        return (
            "【政策主题对齐】\n"
            "- 该股票当前未命中任一已编档的十四五/十五五政策主题。\n"
            "- 政策得分: 0/100；操作判断不应依赖政策溢价。\n"
        )

    matched_themes: list[PolicyTheme] = []
    for m in alignment.matches:
        t = find_theme(m.theme_id)
        if t:
            matched_themes.append(t)
    phase, _ = aggregate_phase(matched_themes)

    lines = [
        "【政策主题对齐】",
        f"- 综合对齐分: {alignment.score:.0f}/100  (level={alignment.level})",
        f"- 主导周期阶段: {phase}  ← 由 data 层 aggregate_phase 计算，不要再自行判断",
        "- 命中主题（按 tier 排序）:",
    ]
    for m in alignment.matches[:5]:
        theme = find_theme(m.theme_id)
        if theme is None:
            continue
        sig = lifecycle_signal(theme)
        last = theme.lifecycle.last_catalyst.isoformat() if theme.lifecycle.last_catalyst else "未标注"
        nxt = theme.lifecycle.next_window.isoformat() if theme.lifecycle.next_window else "未标注"
        decay = theme.lifecycle.decay_after.isoformat() if theme.lifecycle.decay_after else "未标注"
        evidence = "、".join(m.matched_concepts[:3]) or "（无具体概念证据）"
        lines.append(
            f"  · [tier {theme.tier}] {theme.name} ({theme.plan} · {theme.pillar}) "
            f"— 当前阶段: {sig.label}; 最近催化: {last}; 下一窗口: {nxt}; "
            f"预期退坡: {decay}; 命中证据: {evidence}"
        )
    return "\n".join(lines) + "\n"


def _capital_block(cf: Optional[CapitalFlow]) -> str:
    if cf is None:
        return "【资金面】数据未加载（A5.2 接口未连通）。\n"
    if cf.consensus_score is None and cf.fetch_errors:
        return (
            "【资金面】数据不可用（fetch_errors: "
            + ", ".join(cf.fetch_errors)
            + "）。\n"
        )

    lines = ["【资金面】"]
    if cf.consensus_score is not None:
        lines.append(
            f"- 共识评分: {cf.consensus_score:.0f}/100 ({cf.consensus_label}) "
            f"← 由 4 个子指标聚合，不要再自行评分"
        )
    if cf.northbound_holding_pct is not None:
        lines.append(f"- 北向持股占流通股: {cf.northbound_holding_pct:.2f}%")
    if cf.northbound_5d_yuan is not None:
        lines.append(f"- 北向 5 日净流入: {_fmt_yuan(cf.northbound_5d_yuan)}")
    if cf.northbound_20d_yuan is not None:
        lines.append(f"- 北向 20 日净流入: {_fmt_yuan(cf.northbound_20d_yuan)}")
    if cf.main_5d_yuan is not None:
        lines.append(f"- 主力 5 日净流入: {_fmt_yuan(cf.main_5d_yuan)}")
    if cf.lhb_30d_count is not None:
        lines.append(f"- 龙虎榜 30 日次数: {cf.lhb_30d_count}")
    if cf.fetch_errors:
        lines.append(f"- 部分数据缺失: {', '.join(cf.fetch_errors)} (评分已自动降权)")
    return "\n".join(lines) + "\n"


def _regulatory_block(rs: Optional[RegulatoryStatus]) -> str:
    if rs is None:
        return "【监管风险】数据未加载（A5.2 接口未连通）。\n"

    lines = ["【监管风险】"]
    lines.append(
        f"- 综合风险等级: {rs.risk_level}  ← 由 data 层 _level_from() 评定，不要再自行判定"
    )
    if rs.is_st is True:
        lines.append(f"- ST 状态: {rs.st_label or 'ST'}（监管特别处理）")
    elif rs.is_st is False:
        lines.append("- ST 状态: 正常")
    lines.append(f"- 实控人性质: {rs.controller_type}" + (f"（{rs.controller_name[:30]}）" if rs.controller_name else ""))
    if rs.perf_warning:
        lines.append(f"- 业绩预警: {rs.perf_warning}")
    if rs.csrc_penalty_count_3y is not None and rs.csrc_penalty_count_3y > 0:
        lines.append(f"- 近 3 年 CSRC 处罚: {rs.csrc_penalty_count_3y} 次")
    if rs.risk_reasons:
        lines.append("- 判定依据:")
        for r in rs.risk_reasons[:4]:
            lines.append(f"  · {r}")
    if rs.fetch_errors:
        lines.append(f"- 部分数据缺失: {', '.join(rs.fetch_errors)}")
    return "\n".join(lines) + "\n"


def build_ashare_context(
    alignment: Optional[PolicyAlignment] = None,
    capital_flow: Optional[CapitalFlow] = None,
    regulatory: Optional[RegulatoryStatus] = None,
) -> str:
    """Assemble the prompt-ready context block.

    Returns a multi-line string with three labeled sections. Empty data
    is replaced with explicit "数据未加载" lines so the LLM cannot pretend
    to know what we didn't tell it.
    """
    return (
        _alignment_block(alignment)
        + "\n"
        + _capital_block(capital_flow)
        + "\n"
        + _regulatory_block(regulatory)
    )


def build_short_summary(
    alignment: Optional[PolicyAlignment] = None,
    capital_flow: Optional[CapitalFlow] = None,
    regulatory: Optional[RegulatoryStatus] = None,
) -> str:
    """Compact one-line summary for the brief prompt's policy_picture slot."""
    parts: list[str] = []
    if alignment and alignment.matches:
        themes = [find_theme(m.theme_id) for m in alignment.matches[:2]]
        themes = [t for t in themes if t is not None]
        phase, _ = aggregate_phase(themes)
        names = "/".join(t.name for t in themes)
        parts.append(f"主线 {alignment.score:.0f}分 · {phase} · {names}")
    elif alignment:
        parts.append(f"主线对齐 0 分（无政策主题）")
    if capital_flow and capital_flow.consensus_label:
        parts.append(f"资金 {capital_flow.consensus_label}")
    if regulatory:
        parts.append(f"风险 {regulatory.risk_level}")
    return " | ".join(parts) if parts else "数据未就绪"
