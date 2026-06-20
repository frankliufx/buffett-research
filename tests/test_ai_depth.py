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


from unittest.mock import patch, MagicMock
import json


def test_committee_master_prompts_contain_cot_steps():
    """每位大师的 prompt 必须包含四步推理结构"""
    from src.ai.committee import _masters
    for master in _masters:
        prompt = master["prompt"]
        assert "核心优势" in prompt or "核心论点" in prompt or "关键证据" in prompt, \
            f"{master['name']} prompt 缺少 CoT 结构"
        assert "key_evidence" in prompt, \
            f"{master['name']} prompt 缺少 key_evidence 字段"
        assert "main_concern" in prompt, \
            f"{master['name']} prompt 缺少 main_concern 字段"


def test_committee_data_context_includes_quality_warning():
    """当数据有 _warnings 时，_build_data_context 应在输出中包含质量提示"""
    from src.ai.committee import _build_data_context

    result_with_warnings = {
        "symbol": "AAPL",
        "name": "Apple",
        "price": 150.0,
        "change_pct": 1.5,
        "pe_trailing": 28.0,
        "pb": 42.0,
        "roe": 0.97,
        "profit_margin": 0.25,
        "gross_margin": 0.46,
        "operating_margin": 0.31,
        "revenue_growth": 0.04,
        "earnings_growth": 0.08,
        "debt_to_equity": 121.0,
        "current_ratio": 1.05,
        "free_cashflow": 110e9,
        "market_cap": 3200e9,
        "_warnings": ["roe: ⚠️ 数据源差异 15.3%（yfinance=0.97, sec_edgar=0.82）"],
        "_data_quality": {"roe": "uncertain"},
    }
    moat = {"total_score": 92, "grade": "A"}

    context = _build_data_context(result_with_warnings, moat)
    assert "⚠️" in context or "数据质量" in context or "uncertain" in context.lower(), \
        "数据质量警告未注入 data context"


def test_committee_json_parser_handles_new_fields():
    """committee 结果解析器应正确处理新增的 key_evidence / main_concern 字段"""
    from src.ai.committee import _parse_master_result

    raw_json = json.dumps({
        "signal": "bullish",
        "confidence": 85,
        "key_evidence": "ROE=28%，持续 10 年高于 20%",
        "main_concern": "估值偏高 PE=35x",
        "reasoning": "护城河坚实，现价有一定安全边际，但需警惕估值压缩",
    })
    result = _parse_master_result(raw_json)
    assert result["signal"] == "bullish"
    assert result["confidence"] == 85
    assert result["key_evidence"] == "ROE=28%，持续 10 年高于 20%"
    assert result["main_concern"] == "估值偏高 PE=35x"


def test_critic_refine_calls_llm_three_times():
    """Critic-Refine 流程应调用 LLM 3 次：初稿 + critic + refine"""
    from src.ai.summarizer import analyze_stock

    call_count = [0]
    call_args = []

    def mock_call_llm(provider, messages, max_tokens=2000, timeout=60.0):
        call_count[0] += 1
        call_args.append(messages)
        if call_count[0] == 1:
            return "# 初稿研报\n## 执行摘要\n看多，置信度高。"
        elif call_count[0] == 2:
            return "## 薄弱论点\n- 估值数据缺失\n\n## 遗漏风险\n利率风险\n\n## 做空论据\nPE 偏高"
        else:
            return "# 修订版研报\n## 执行摘要\n看多，但需注意估值风险。"

    mock_provider = MagicMock()
    mock_provider.provider = "anthropic"

    mock_result = {
        "symbol": "AAPL", "name": "Apple", "price": 150.0, "change_pct": 1.5,
        "pe_trailing": 28.0, "pb": 42.0, "roe": 0.97, "profit_margin": 0.25,
        "gross_margin": 0.46, "operating_margin": 0.31, "revenue_growth": 0.04,
        "earnings_growth": 0.08, "debt_to_equity": 121.0, "current_ratio": 1.05,
        "free_cashflow": 110e9, "market_cap": 3200e9,
    }
    mock_moat = {"total_score": 92, "grade": "A", "profitability_score": 28,
                  "profitability_max": 30, "moat_score": 22, "moat_max": 25,
                  "fortress_score": 18, "fortress_max": 20, "growth_score": 13,
                  "growth_max": 15, "opportunity_score": 8, "opportunity_max": 10}
    mock_valuation = {"intrinsic_value": 160.0, "safety_margin_pct": 6.7}

    with patch("src.ai.summarizer._call_llm", side_effect=mock_call_llm):
        report = analyze_stock(
            mock_result, mock_moat, mock_valuation,
            provider=mock_provider,
            use_critic=True,
        )

    assert call_count[0] == 3, f"期望 3 次 LLM 调用，实际 {call_count[0]} 次"
    assert "修订版研报" in report or "执行摘要" in report


def test_critic_refine_skipped_when_disabled():
    """use_critic=False 时只调用 LLM 1 次"""
    from src.ai.summarizer import analyze_stock

    call_count = [0]

    def mock_call_llm(provider, messages, max_tokens=2000, timeout=60.0):
        call_count[0] += 1
        return "# 研报内容"

    mock_provider = MagicMock()
    mock_result = {
        "symbol": "AAPL", "name": "Apple", "price": 150.0, "change_pct": 1.5,
        "pe_trailing": 28.0, "pb": None, "roe": 0.97, "profit_margin": 0.25,
        "gross_margin": 0.46, "operating_margin": None, "revenue_growth": None,
        "earnings_growth": None, "debt_to_equity": None, "current_ratio": None,
        "free_cashflow": None, "market_cap": None,
    }
    mock_moat = {"total_score": 70, "grade": "B", "profitability_score": 20,
                  "profitability_max": 30, "moat_score": 18, "moat_max": 25,
                  "fortress_score": 14, "fortress_max": 20, "growth_score": 10,
                  "growth_max": 15, "opportunity_score": 8, "opportunity_max": 10}

    with patch("src.ai.summarizer._call_llm", side_effect=mock_call_llm):
        report = analyze_stock(
            mock_result, mock_moat, {},
            provider=mock_provider,
            use_critic=False,
        )

    assert call_count[0] == 1, f"期望 1 次 LLM 调用，实际 {call_count[0]} 次"


def test_hedge_fund_analyst_prompts_contain_cot():
    """所有对冲基金分析师 prompt 必须包含 CoT 结构"""
    from src.ai.hedge_fund_agents import ANALYSTS
    for analyst in ANALYSTS:
        prompt = analyst["prompt"]
        assert "key_evidence" in prompt, \
            f"{analyst['name']} prompt 缺少 key_evidence 字段"
        assert "main_concern" in prompt, \
            f"{analyst['name']} prompt 缺少 main_concern 字段"
        assert "120字" in prompt or "150字" in prompt, \
            f"{analyst['name']} prompt 未指定 reasoning 长度限制"
