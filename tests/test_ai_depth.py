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
