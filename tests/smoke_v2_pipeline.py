"""Smoke test for v2 4-stage decision pipeline (run_full_workflow).

Verifies that with mocked LLM + news, the pipeline returns a well-formed
final_decision dict with the right keys and value ranges.

Run:
    .venv/bin/python tests/smoke_v2_pipeline.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure repo root on path when run from anywhere
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Disable DB persistence side-effects for the smoke
os.environ.setdefault("DB_FIRST_ENABLED", "false")

import pandas as pd

import src.ai.summarizer as summarizer_mod
from src.ai.hedge_fund_runner import run_full_workflow
from src.config import ApiProvider


# ----------------------------------------------------------------------------
# Mock LLM: dispatch by prompt content
# ----------------------------------------------------------------------------
def _mock_llm(provider, messages, max_tokens=2000) -> str:
    prompt = (messages[0].get("content") or "") if messages else ""

    if "财经新闻分析师" in prompt:
        return json.dumps({
            "score": 35,
            "themes": ["财报超预期", "新品发布"],
            "bullish": ["营收创新高", "毛利率提升"],
            "bearish": ["供应链风险"],
            "summary": "整体偏多，财报与新品双驱动。"
        }, ensure_ascii=False)

    if "portfolio manager" in prompt:
        return "智能体推理：估值锚位偏低叠加新闻偏多，建议关注入场区间。关键前提：财报指引继续兑现。"

    # Analyst votes — return strict JSON expected by _call_analyst
    return json.dumps({
        "signal": "bullish",
        "confidence": 75,
        "reasoning": "Mock analyst sees strong fundamentals."
    }, ensure_ascii=False)


# Monkey-patch the single LLM entry point used by all three modules
summarizer_mod._call_llm = _mock_llm


# ----------------------------------------------------------------------------
# Fake fetch_news_fn (so we don't hit eastmoney/sina)
# ----------------------------------------------------------------------------
def _fake_fetch_news(symbol, market, limit=10):
    return [
        {"title": "Q1 earnings beat estimates", "source": "Reuters",
         "time": "2026-05-10", "summary": "Revenue +12% YoY"},
        {"title": "New product launch announced", "source": "WSJ",
         "time": "2026-05-08", "summary": "Expanding into AI services"},
    ]


# ----------------------------------------------------------------------------
# Synthetic inputs
# ----------------------------------------------------------------------------
fundamentals = {"free_cashflow": 1.2e10, "revenue": 5e10}
normalized = {
    "pe_trailing": 28.5, "pb": 6.2, "roe": 0.21, "roa": 0.12,
    "gross_margin": 0.45, "profit_margin": 0.22, "operating_margin": 0.28,
    "debt_to_equity": 1.4, "current_ratio": 1.1, "quick_ratio": 0.9,
    "revenue_growth": 0.12, "earnings_growth": 0.18, "earnings_quarterly_growth": 0.20,
    "dividend_yield": 0.005, "market_cap": 2.5e12, "pe_forward": 24.0,
}
moat = {"percentage": 78, "grade": "宽护城河",
        "dimensions": [{"name": "品牌", "score": 18, "max": 20},
                       {"name": "网络效应", "score": 15, "max": 20}]}
dcf = {"intrinsic_value": 220.0, "safety_margin_pct": 12.5}
tech = {"trend": "上行", "momentum": "正", "rsi": 58.0, "macd": "金叉"}

# fake history (180 days) for volatility calc
import numpy as np
np.random.seed(42)
dates = pd.date_range("2025-11-13", periods=180, freq="D")
prices = 195 + np.cumsum(np.random.randn(180) * 1.5)
df_history = pd.DataFrame({"Close": prices, "High": prices + 1, "Low": prices - 1,
                           "Open": prices, "Volume": 1_000_000}, index=dates)

# minimal provider stub — _call_llm is fully mocked so attributes are unused
provider = ApiProvider(name="mock", provider="openai_compatible",
                      api_key="sk-mock", base_url="http://mock",
                      model="mock-model", is_active=True)


# ----------------------------------------------------------------------------
# Run + assert
# ----------------------------------------------------------------------------
result = run_full_workflow(
    symbol="AAPL", name="Apple Inc", market="us",
    price=195.42,
    fundamentals=fundamentals, normalized=normalized,
    moat=moat, dcf=dcf, tech=tech, df_history=df_history,
    analyst_ids=["buffett", "munger", "burry"],
    provider=provider,
    fetch_news_fn=_fake_fetch_news,
    max_workers=3,
)

assert result is not None, "run_full_workflow returned None"
assert "final_decision" in result, "missing final_decision"
assert "news_sentiment" in result, "missing news_sentiment"
assert "risk" in result, "missing risk"
assert "analysts" in result, "missing analysts list"

fd = result["final_decision"]
required = {"action", "conviction", "combined_score", "position_pct",
            "entry_zone", "stop_loss", "take_profit", "horizon",
            "vote_aggregate", "news_sentiment", "risk_summary", "reasoning"}
missing = required - set(fd.keys())
assert not missing, f"final_decision missing keys: {missing}"

assert fd["action"] in {"买入", "加仓", "持有", "减仓", "卖出"}, f"bad action: {fd['action']}"
assert fd["conviction"] in {"高", "中", "低"}, f"bad conviction: {fd['conviction']}"
assert -100 <= fd["combined_score"] <= 100, f"combined_score out of range: {fd['combined_score']}"
assert 0.0 <= float(fd["position_pct"]) <= 100.0, f"position_pct out of range: {fd['position_pct']}"

ez = fd["entry_zone"]
assert {"ideal", "acceptable", "expensive_above", "anchor"}.issubset(ez.keys())
sl = fd["stop_loss"]
assert "price" in sl and "rationale" in sl
tp = fd["take_profit"]
assert "price" in tp and "rationale" in tp

ns = result["news_sentiment"]
assert -100 <= ns["score"] <= 100
assert ns["article_count"] == 2
assert ns["label"] in {"极度看多", "看多", "中性", "看空", "极度看空"}

rk = result["risk"]
assert rk["annual_vol_pct"] is not None
assert rk["risk_level"] in {"低", "中", "高", "极高"} or rk["risk_level"] is None
assert rk["max_position_pct"] is not None

print("=" * 60)
print("v2 pipeline smoke OK")
print("=" * 60)
print(f"  action         = {fd['action']}  (信心 {fd['conviction']})")
print(f"  combined_score = {fd['combined_score']:+d}")
print(f"  position_pct   = {fd['position_pct']}%")
print(f"  horizon        = {fd['horizon']}")
print(f"  entry          = {ez['ideal']} ~ {ez['acceptable']}")
print(f"  stop_loss      = {sl['price']}  ({sl.get('drop_pct', '—')}%)")
print(f"  take_profit    = {tp['price']}")
print(f"  news           = {ns['label']} ({ns['score']:+d}, n={ns['article_count']})")
print(f"  risk           = {rk['risk_level']} · 年化 {rk['annual_vol_pct']}% · 上限 {rk['max_position_pct']}%")
print(f"  analysts voted = {len(result['analysts'])}")
print(f"  reasoning len  = {len(fd['reasoning'])}")
