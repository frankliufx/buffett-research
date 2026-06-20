"""Tests for AI-powered stock screener."""

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


def test_batch_evaluate_sorted_by_score():
    from src.screener.ai_screener import batch_evaluate
    from src.config import ApiProvider

    provider = ApiProvider(
        name="Test", provider="openai_compatible",
        api_key="key", base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-chat-v3-0324", is_active=True,
    )

    responses = {
        "AAPL": '{"score": 90, "category": "强烈关注", "rationale": "强"}',
        "MSFT": '{"score": 60, "category": "持续观察", "rationale": "中"}',
        "BAD":  '{"score": 20, "category": "回避", "rationale": "差"}',
    }

    def fake_create(model, messages, **kwargs):
        content = messages[1]["content"]
        for sym, resp in responses.items():
            if sym in content:
                m = MagicMock()
                m.choices = [MagicMock()]
                m.choices[0].message.content = resp
                return m
        m = MagicMock()
        m.choices = [MagicMock()]
        m.choices[0].message.content = '{"score": 50, "category": "持续观察", "rationale": "default"}'
        return m

    with patch("openai.OpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create.side_effect = fake_create
        stocks = [("AAPL", "Apple"), ("MSFT", "Microsoft"), ("BAD", "Bad Stock")]
        results = batch_evaluate(stocks, {}, provider, max_workers=1)

    assert results[0]["score"] >= results[1]["score"] >= results[2]["score"]
    assert results[0]["symbol"] == "AAPL"


def test_batch_evaluate_progress_callback():
    from src.screener.ai_screener import batch_evaluate
    from src.config import ApiProvider

    provider = ApiProvider(
        name="Test", provider="openai_compatible",
        api_key="key", base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-chat-v3-0324", is_active=True,
    )
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = '{"score": 70, "category": "持续观察", "rationale": "ok"}'

    calls = []

    def on_progress(done, total):
        calls.append((done, total))

    with patch("openai.OpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create.return_value = mock_resp
        stocks = [("AAPL", "Apple"), ("MSFT", "Microsoft")]
        batch_evaluate(stocks, {}, provider, max_workers=1, progress_callback=on_progress)

    assert len(calls) == 2
    assert all(total == 2 for _, total in calls)
    dones = sorted(d for d, _ in calls)
    assert dones == [1, 2]


def test_batch_evaluate_api_exception_does_not_abort_batch():
    """When one stock's API call fails, the rest should still complete."""
    from src.screener.ai_screener import batch_evaluate
    from src.config import ApiProvider

    provider = ApiProvider(
        name="Test", provider="openai_compatible",
        api_key="key", base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-chat-v3-0324", is_active=True,
    )

    call_count = [0]

    def fake_create(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("network error")
        m = MagicMock()
        m.choices = [MagicMock()]
        m.choices[0].message.content = '{"score": 70, "category": "持续观察", "rationale": "ok"}'
        return m

    with patch("openai.OpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create.side_effect = fake_create
        stocks = [("FAIL", "Failing Stock"), ("PASS", "Passing Stock")]
        results = batch_evaluate(stocks, {}, provider, max_workers=1)

    assert len(results) == 2
    fail_result = next(r for r in results if r["symbol"] == "FAIL")
    pass_result = next(r for r in results if r["symbol"] == "PASS")
    assert fail_result["category"] == "回避"
    assert fail_result["score"] == 0
    assert pass_result["score"] == 70
