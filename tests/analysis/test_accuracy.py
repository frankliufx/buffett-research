# tests/analysis/test_accuracy.py
import pytest
from src.analysis.accuracy import compute_hedge_fund_accuracy


DECISIONS = [
    {
        "decision_id": 1,
        "symbol": "AAPL",
        "market": "us",
        "decided_at": "2026-05-01",
        "price": 150.0,
        "consensus_signal": "bullish",
        "votes_payload": [
            {"id": "buffett", "name": "Warren Buffett", "signal": "bullish", "confidence": 80},
            {"id": "graham",  "name": "Ben Graham",     "signal": "bearish", "confidence": 60},
            {"id": "lynch",   "name": "Peter Lynch",    "signal": "neutral", "confidence": 50},
        ],
    },
    {
        "decision_id": 2,
        "symbol": "TSLA",
        "market": "us",
        "decided_at": "2026-05-03",
        "price": 200.0,
        "consensus_signal": "bearish",
        "votes_payload": [
            {"id": "buffett", "name": "Warren Buffett", "signal": "bearish", "confidence": 70},
            {"id": "graham",  "name": "Ben Graham",     "signal": "bullish", "confidence": 55},
        ],
    },
]

# AAPL went up (bullish hit, bearish miss), TSLA went down (bearish hit, bullish miss)
CURRENT_PRICES = {
    "us:AAPL": 165.0,  # +10%
    "us:TSLA": 180.0,  # -10%
}


def test_compute_returns_dict_keyed_by_analyst_id():
    result = compute_hedge_fund_accuracy(DECISIONS, CURRENT_PRICES)
    assert "buffett" in result
    assert "graham" in result


def test_neutral_votes_are_skipped():
    result = compute_hedge_fund_accuracy(DECISIONS, CURRENT_PRICES)
    # lynch voted neutral on AAPL — should have 0 total evaluated
    assert result.get("lynch", {}).get("total", 0) == 0


def test_buffett_two_hits():
    # buffett: bullish AAPL (price went up) = hit; bearish TSLA (price went down) = hit
    result = compute_hedge_fund_accuracy(DECISIONS, CURRENT_PRICES)
    assert result["buffett"]["hits"] == 2
    assert result["buffett"]["total"] == 2
    assert result["buffett"]["hit_rate"] == pytest.approx(1.0)


def test_graham_two_misses():
    # graham: bearish AAPL (price went up) = miss; bullish TSLA (price went down) = miss
    result = compute_hedge_fund_accuracy(DECISIONS, CURRENT_PRICES)
    assert result["graham"]["hits"] == 0
    assert result["graham"]["total"] == 2
    assert result["graham"]["hit_rate"] == pytest.approx(0.0)


def test_avg_confidence_is_computed():
    result = compute_hedge_fund_accuracy(DECISIONS, CURRENT_PRICES)
    # buffett: confidence 80 + 70 = avg 75
    assert result["buffett"]["avg_confidence"] == pytest.approx(75.0)


def test_returns_empty_for_no_decisions():
    result = compute_hedge_fund_accuracy([], {})
    assert result == {}


def test_missing_price_skips_decision():
    result = compute_hedge_fund_accuracy(DECISIONS, {"us:AAPL": 165.0})  # TSLA missing
    # buffett: only AAPL decision evaluated → 1 total, 1 hit
    assert result["buffett"]["total"] == 1
    assert result["buffett"]["hits"] == 1
