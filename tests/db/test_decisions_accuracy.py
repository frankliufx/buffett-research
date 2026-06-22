import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal


def test_get_decisions_for_accuracy_returns_empty_when_db_unavailable():
    with patch("src.db.decisions.db_available", return_value=False):
        from src.db.decisions import get_decisions_for_accuracy
        result = get_decisions_for_accuracy(min_age_days=30, limit=200)
    assert result == []


def test_get_decisions_for_accuracy_returns_empty_on_exception():
    """Returns [] and does not raise when session_scope raises an exception."""
    with patch("src.db.decisions.db_available", return_value=True), \
         patch("src.db.decisions.session_scope", side_effect=RuntimeError("db gone")):
        from src.db.decisions import get_decisions_for_accuracy
        result = get_decisions_for_accuracy(min_age_days=30, limit=200)
    assert result == []


def test_get_decisions_for_accuracy_structure():
    """Verify the returned dict shape when DB returns a row."""
    mock_row = MagicMock()
    mock_row.id = 42
    mock_row.decided_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    mock_row.price = Decimal("150.00")
    mock_row.consensus_signal = "bullish"
    mock_row.votes_payload = [
        {"id": "buffett", "name": "Warren Buffett", "signal": "bullish", "confidence": 80}
    ]
    mock_stock = MagicMock()
    mock_stock.symbol = "AAPL"
    mock_stock.market = "us"

    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_ctx.execute.return_value.all.return_value = [(mock_row, mock_stock)]

    with patch("src.db.decisions.db_available", return_value=True), \
         patch("src.db.decisions.session_scope", return_value=mock_ctx):
        from importlib import reload
        import src.db.decisions as mod
        result = mod.get_decisions_for_accuracy(min_age_days=30, limit=200)

    assert len(result) == 1
    d = result[0]
    assert d["decision_id"] == 42
    assert d["symbol"] == "AAPL"
    assert d["market"] == "us"
    assert d["price"] == 150.0
    assert d["consensus_signal"] == "bullish"
    assert isinstance(d["votes_payload"], list)
