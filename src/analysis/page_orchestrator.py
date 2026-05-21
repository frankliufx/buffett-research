"""Data-orchestration helpers shared by pages/2_analysis.py and scanners.

Wraps the raw data layer in `@st.cache_data` so repeated views and parallel
scans of the same symbol don't re-hit upstream APIs. Each wrapper swallows
exceptions and returns a safe empty value so a single bad symbol can't break
the page render.
"""

from __future__ import annotations

import logging
import os

import pandas as pd
import streamlit as st

from src.analysis.fundamental import _normalize_fundamentals, analyze_buffett
from src.analysis.moat import score_moat
from src.analysis.signals import AnalysisResult
from src.analysis.technical import compute_indicators, generate_technical_signal
from src.cache_config import CACHE_TTL
from src.data.financial import fetch_fundamentals
from src.data.news import fetch_earnings_calendar, fetch_market_news, fetch_stock_news
from src.data.policy import get_fifteen_five_alignment, get_policy_news
from src.data.price import fetch_history, fetch_quote

logger = logging.getLogger(__name__)


@st.cache_data(ttl=CACHE_TTL["policy"], show_spinner=False)
def cached_get_policy_data(symbol):
    """A股专用：获取政策概念数据（24h缓存）"""
    try:
        alignment = get_fifteen_five_alignment(symbol)
        news = get_policy_news(limit=5)
        return alignment, news
    except Exception as e:
        logger.warning("policy data failed %s: %s", symbol, e)
        return {"level": "暂无明显政策主题", "score": 0, "color": "#5A5A6A",
                "tier1": [], "tier2": [], "all_tags": []}, []


@st.cache_data(ttl=CACHE_TTL["history"], show_spinner=False)
def cached_fetch_history(symbol, market, days):
    try:
        return fetch_history(symbol, market, days)
    except Exception as e:
        logger.warning("fetch_history failed %s: %s", symbol, e)
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL["quote"], show_spinner=False)
def cached_fetch_quote(symbol, market):
    try:
        return fetch_quote(symbol, market)
    except Exception as e:
        logger.warning("fetch_quote failed %s: %s", symbol, e)
        return {}


@st.cache_data(ttl=CACHE_TTL["fundamentals"], show_spinner=False)
def cached_fetch_fundamentals(symbol, market):
    try:
        if os.getenv("DB_FIRST_ENABLED", "").lower() in ("1", "true", "yes"):
            from src.db.repository import get_or_fetch_fundamentals
            return get_or_fetch_fundamentals(symbol, market)
        return fetch_fundamentals(symbol, market)
    except Exception as e:
        logger.warning("fetch_fundamentals failed %s: %s", symbol, e)
        return {}


@st.cache_data(ttl=CACHE_TTL["market_news"], show_spinner=False)
def cached_fetch_news(symbol, market, limit=8):
    try:
        return fetch_stock_news(symbol, market, limit)
    except Exception as e:
        logger.warning("fetch_news failed %s: %s", symbol, e)
        return []


@st.cache_data(ttl=CACHE_TTL["calendar"], show_spinner=False)
def cached_fetch_calendar(symbol, market):
    try:
        return fetch_earnings_calendar(symbol, market)
    except Exception as e:
        logger.warning("fetch_calendar failed %s: %s", symbol, e)
        return []


@st.cache_data(ttl=CACHE_TTL["market_news"], show_spinner=False)
def cached_fetch_market_news(market, limit=6):
    try:
        return fetch_market_news(market, limit)
    except Exception as e:
        logger.warning("fetch_market_news failed %s: %s", market, e)
        return []


def run_analysis(symbol, name, market, config):
    """Full single-stock analysis pipeline → AnalysisResult + supporting data.

    Returns (result, df, fundamentals, normalized, moat_result, quote).
    """
    df = cached_fetch_history(symbol, market, config.technical.lookback_days)
    quote = cached_fetch_quote(symbol, market)
    fundamentals = cached_fetch_fundamentals(symbol, market)
    normalized = _normalize_fundamentals(fundamentals)

    if not df.empty:
        df = compute_indicators(df.copy(), config.technical)
        tech_signal = generate_technical_signal(df)
    else:
        tech_signal = {"trend": "unknown", "momentum": "unknown", "signals": [], "trend_score": 0}

    buffett_result = analyze_buffett(fundamentals, config.buffett_strategy)
    moat_result = score_moat(fundamentals, normalized, tech_signal)

    result = AnalysisResult(
        symbol=symbol, name=name, market=market,
        price=quote.get("price", 0) or tech_signal.get("price", 0),
        change_pct=quote.get("change_pct", 0),
        tech_signal=tech_signal, buffett_result=buffett_result,
        fundamentals=fundamentals,
    )
    result.compute_overall()
    return result, df, fundamentals, normalized, moat_result, quote
