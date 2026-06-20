"""Tests for AI-powered stock screener."""

import pytest
from unittest.mock import patch, MagicMock


def test_investment_principles_count():
    from src.screener.ai_screener import INVESTMENT_PRINCIPLES
    assert len(INVESTMENT_PRINCIPLES) == 10


def test_parse_ai_response_valid():
    from src.screener.ai_screener import _parse_response
    raw = '{"score": 82, "category": "强烈关注", "rationale": "强护城河，ROE连续高于15%"}'
    result = _parse_response(raw)
    assert result["score"] == 82
    assert result["category"] == "强烈关注"
    assert "rationale" in result


def test_parse_ai_response_with_markdown_fence():
    from src.screener.ai_screener import _parse_response
    raw = '```json\n{"score": 45, "category": "回避", "rationale": "高债务"}\n```'
    result = _parse_response(raw)
    assert result["score"] == 45
    assert result["category"] == "回避"


def test_parse_ai_response_fallback():
    from src.screener.ai_screener import _parse_response
    result = _parse_response("invalid json content")
    assert result["score"] == 50
    assert result["category"] == "持续观察"
    assert "rationale" in result


def test_evaluate_stock_calls_provider():
    from src.screener.ai_screener import evaluate_stock
    from src.config import ApiProvider

    mock_provider = ApiProvider(
        name="Test",
        provider="openai_compatible",
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-chat-v3-0324",
        is_active=True,
    )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"score": 75, "category": "持续观察", "rationale": "合理估值"}'

    with patch("openai.OpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create.return_value = mock_response
        result = evaluate_stock("AAPL", "Apple", {"pe": 28, "roe": 0.18}, mock_provider)

    assert result["symbol"] == "AAPL"
    assert result["score"] == 75
    assert result["category"] == "持续观察"
