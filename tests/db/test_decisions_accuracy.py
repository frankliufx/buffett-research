import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal


@pytest.mark.unit
def test_get_decisions_for_accuracy_returns_empty_when_db_unavailable():
    with patch("src.db.decisions.db_available", return_value=False):
        from src.db.decisions import get_decisions_for_accuracy
        result = get_decisions_for_accuracy(min_age_days=30, limit=200)
    assert result == []


@pytest.mark.unit
def test_get_decisions_for_accuracy_returns_empty_on_exception():
    """Returns [] and does not raise when session_scope raises an exception."""
    with patch("src.db.decisions.db_available", return_value=True), \
         patch("src.db.decisions.session_scope", side_effect=RuntimeError("db gone")):
        from src.db.decisions import get_decisions_for_accuracy
        result = get_decisions_for_accuracy(min_age_days=30, limit=200)
    assert result == []


@pytest.mark.unit
def test_get_decisions_for_accuracy_accepts_params():
    """Function accepts min_age_days and limit params and returns a list."""
    with patch("src.db.decisions.db_available", return_value=False):
        from src.db.decisions import get_decisions_for_accuracy
        result = get_decisions_for_accuracy(min_age_days=60, limit=50)
    assert isinstance(result, list)
    assert result == []
