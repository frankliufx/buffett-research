"""测试 AI 分析深度升级：prompt 结构 + Critic-Refine 机制"""
from __future__ import annotations
import pytest
from src.ai.prompts import CRITIC_PROMPT, BUFFETT_ANALYSIS_PROMPT


def test_critic_prompt_exists():
    assert CRITIC_PROMPT is not None
    assert len(CRITIC_PROMPT) > 100


def test_critic_prompt_has_required_placeholders():
    """CRITIC_PROMPT 必须包含 {report} 和 {data} 占位符"""
    assert "{report}" in CRITIC_PROMPT
    assert "{data}" in CRITIC_PROMPT


def test_critic_prompt_renders_without_error():
    rendered = CRITIC_PROMPT.format(
        report="这是一份测试研报内容",
        data="ROE: 25%, PE: 20, 净利润增长: 15%",
    )
    assert "测试研报内容" in rendered
    assert "ROE: 25%" in rendered


def test_buffett_prompt_has_executive_summary_section():
    assert "执行摘要" in BUFFETT_ANALYSIS_PROMPT


def test_buffett_prompt_has_core_arguments_section():
    assert "核心论点" in BUFFETT_ANALYSIS_PROMPT


def test_buffett_prompt_has_risk_section():
    assert "主要风险" in BUFFETT_ANALYSIS_PROMPT


def test_buffett_prompt_has_valuation_section():
    assert "估值区间" in BUFFETT_ANALYSIS_PROMPT


def test_buffett_prompt_renders_without_error():
    """BUFFETT_ANALYSIS_PROMPT 可以用所有必须占位符正常渲染，不抛出 KeyError"""
    rendered = BUFFETT_ANALYSIS_PROMPT.format(
        symbol="TEST",
        name="TEST",
        price="TEST",
        change_pct="TEST",
        market_label="TEST",
        moat_total="TEST",
        moat_grade="TEST",
        profitability_score="TEST",
        profitability_max="TEST",
        moat_depth_score="TEST",
        moat_depth_max="TEST",
        fortress_score="TEST",
        fortress_max="TEST",
        growth_score="TEST",
        growth_max="TEST",
        opportunity_score="TEST",
        opportunity_max="TEST",
        buffett_grade="TEST",
        buffett_score="TEST",
        buffett_max="TEST",
        buffett_pct="TEST",
        buffett_details="TEST",
        trend="TEST",
        momentum="TEST",
        rsi="TEST",
        tech_signals="TEST",
        pe="TEST",
        pb="TEST",
        roe="TEST",
        profit_margin="TEST",
        gross_margin="TEST",
        debt_to_equity="TEST",
        current_ratio="TEST",
        revenue_growth="TEST",
        earnings_growth="TEST",
        dividend_yield="TEST",
        free_cashflow="TEST",
        data_quality_warning_section="TEST",
        data_completeness="TEST",
    )
    assert len(rendered) > 100
