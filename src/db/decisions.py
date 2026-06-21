"""Hedge fund decision persistence — write workflow output to PG.

Single entry: persist_decision(symbol, market, name, hedge_result, provider_name)

设计原则:
- 容错：任何写库失败都打日志后返回 None，不影响 UI 主流程
- 真实：votes/news/risk/decision 全量 JSONB 落盘，便于回归与审计
- 可选：DB_FIRST_ENABLED=false 或 DB 不可用时静默跳过
"""
from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from .models import HedgeFundDecision
    from .repository import get_or_create_stock
    from .session import db_available, session_scope
except Exception as _exc:
    logger.warning("SQLAlchemy unavailable, decision persistence disabled: %s", _exc)
    HedgeFundDecision = None  # type: ignore[assignment,misc]
    get_or_create_stock = None  # type: ignore[assignment]
    def db_available() -> bool:  # type: ignore[misc]
        return False
    def session_scope():  # type: ignore[misc]
        raise ImportError("SQLAlchemy unavailable")

ALGO_VERSION = "v1.0"

# Page-level market codes → DB canonical codes
_MARKET_CANON = {
    "us": "us", "US": "us",
    "hk": "hk", "HK": "hk",
    "cn": "a_share", "CN": "a_share",
    "a_share": "a_share", "A_SHARE": "a_share",
}


def _canon_market(market: str) -> str:
    return _MARKET_CANON.get((market or "").strip(), (market or "").lower())


def _to_decimal(val) -> Optional[Decimal]:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _to_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _is_enabled() -> bool:
    return os.environ.get("DB_FIRST_ENABLED", "false").lower() in ("true", "1", "yes")


def persist_decision(
    symbol: str,
    market: str,
    name: str,
    hedge_result: dict,
    provider_name: Optional[str] = None,
) -> Optional[int]:
    """落库一次 run_full_workflow 的输出。返回 decision_id 或 None。"""
    if not hedge_result:
        return None
    if not _is_enabled():
        logger.debug("DB_FIRST_ENABLED=false, skipping decision persistence")
        return None
    if not db_available():
        logger.warning("DB unavailable, skipping decision persistence for %s", symbol)
        return None

    final = hedge_result.get("final_decision") or {}
    if not final.get("action"):
        logger.warning("No final decision in hedge_result for %s, skipping", symbol)
        return None

    news = hedge_result.get("news_sentiment") or {}
    risk = hedge_result.get("risk") or {}
    consensus = hedge_result.get("consensus") or {}
    analysts = hedge_result.get("analysts") or []

    # 提取 votes payload（精简版，不存大段 reasoning）
    votes_payload = [
        {
            "id": a.get("id"),
            "name": a.get("name"),
            "signal": a.get("signal"),
            "confidence": a.get("confidence"),
            "reasoning": (a.get("reasoning") or "")[:500],
        }
        for a in analysts
    ]

    market_canon = _canon_market(market)
    try:
        with session_scope() as s:
            stock_id = get_or_create_stock(symbol, market_canon, name)
            row = HedgeFundDecision(
                stock_id=stock_id,
                price=_to_decimal(hedge_result.get("price") or 0) or Decimal("0"),
                analyst_ids=[a.get("id") for a in analysts if a.get("id")],
                bullish_count=hedge_result.get("bullish_count", 0),
                bearish_count=hedge_result.get("bearish_count", 0),
                neutral_count=hedge_result.get("neutral_count", 0),
                weighted_score=_to_decimal(hedge_result.get("weighted_score")),
                consensus_signal=consensus.get("signal"),
                consensus_verdict=consensus.get("verdict"),
                unanimity=consensus.get("unanimity"),
                votes_payload=votes_payload,
                news_score=_to_int(news.get("score")),
                news_label=news.get("label"),
                news_article_count=_to_int(news.get("article_count")) or 0,
                news_payload=news or None,
                annual_vol_pct=_to_decimal(risk.get("annual_vol_pct")),
                risk_regime=risk.get("regime"),
                risk_level=risk.get("risk_level"),
                max_position_pct=_to_decimal(risk.get("max_position_pct")),
                risk_payload=risk or None,
                action=final["action"],
                conviction=final.get("conviction") or "中",
                combined_score=_to_int(final.get("combined_score")) or 0,
                position_pct=_to_decimal(final.get("position_pct")),
                horizon=final.get("horizon"),
                entry_payload=final.get("entry_zone"),
                stop_loss_payload=final.get("stop_loss"),
                take_profit_payload=final.get("take_profit"),
                reasoning=final.get("reasoning"),
                algorithm_version=ALGO_VERSION,
                provider_name=provider_name,
            )
            s.add(row)
            s.flush()
            logger.info("Persisted hedge fund decision id=%s for %s (%s)", row.id, symbol, final["action"])
            return row.id
    except Exception as e:
        logger.error("Failed to persist decision for %s: %s", symbol, e, exc_info=True)
        return None


def get_latest_for_watchlist(stocks: list[dict]) -> dict:
    """批量返回 watchlist 中每只股票的最新决策。

    Args:
        stocks: [{"symbol": "AAPL", "market": "us", "name": "Apple"}, ...]
                market 接受 us/hk/a_share 或 US/HK/CN（自动归一化）

    Returns:
        {(symbol, market_canon): decision_dict_or_None, ...}
        每个 dict 形如 get_recent_decisions 返回值的单元素，附 stock_id。
    """
    if not stocks or not db_available():
        return {}

    try:
        from sqlalchemy import select, and_, or_, tuple_
        from .models import Stock
        with session_scope() as s:
            # 先查 stock_id 映射
            pairs = []
            for it in stocks:
                sym = it.get("symbol")
                mk = _canon_market(it.get("market") or "")
                if sym and mk:
                    pairs.append((sym, mk))
            if not pairs:
                return {}

            stock_rows = s.execute(
                select(Stock).where(
                    tuple_(Stock.symbol, Stock.market).in_(pairs),
                    Stock.is_active == True,  # noqa: E712
                )
            ).scalars().all()
            id_to_pair = {st.id: (st.symbol, st.market) for st in stock_rows}
            if not id_to_pair:
                return {(sym, mk): None for sym, mk in pairs}

            # 每只股票的最新决策（窗口函数取每组第一条）
            from sqlalchemy import func as sa_func
            rn = sa_func.row_number().over(
                partition_by=HedgeFundDecision.stock_id,
                order_by=HedgeFundDecision.decided_at.desc(),
            ).label("rn")
            subq = select(HedgeFundDecision, rn).where(
                HedgeFundDecision.stock_id.in_(id_to_pair.keys())
            ).subquery()

            from sqlalchemy.orm import aliased
            HFD = aliased(HedgeFundDecision, subq)
            rows = s.execute(
                select(HFD).where(subq.c.rn == 1)
            ).scalars().all()

            result: dict = {(sym, mk): None for sym, mk in pairs}
            for r in rows:
                pair = id_to_pair.get(r.stock_id)
                if pair is None:
                    continue
                result[pair] = {
                    "stock_id": r.stock_id,
                    "decision_id": r.id,
                    "decided_at": r.decided_at,
                    "price": float(r.price),
                    "action": r.action,
                    "conviction": r.conviction,
                    "combined_score": r.combined_score,
                    "position_pct": float(r.position_pct) if r.position_pct else None,
                    "consensus_verdict": r.consensus_verdict,
                    "unanimity": r.unanimity,
                    "news_label": r.news_label,
                    "news_score": r.news_score,
                    "risk_level": r.risk_level,
                    "horizon": r.horizon,
                    "entry_payload": r.entry_payload,
                    "stop_loss_payload": r.stop_loss_payload,
                    "take_profit_payload": r.take_profit_payload,
                }
            return result
    except Exception as e:
        logger.warning("get_latest_for_watchlist failed: %s", e, exc_info=True)
        return {}


def get_recent_decisions(stock_id: int, limit: int = 20) -> list[dict]:
    """Read-back helper for history views."""
    if not db_available():
        return []
    try:
        from sqlalchemy import select
        with session_scope() as s:
            rows = s.execute(
                select(HedgeFundDecision)
                .where(HedgeFundDecision.stock_id == stock_id)
                .order_by(HedgeFundDecision.decided_at.desc())
                .limit(limit)
            ).scalars().all()
            return [
                {
                    "id": r.id,
                    "decided_at": r.decided_at,
                    "price": float(r.price),
                    "action": r.action,
                    "conviction": r.conviction,
                    "combined_score": r.combined_score,
                    "position_pct": float(r.position_pct) if r.position_pct else None,
                    "consensus_verdict": r.consensus_verdict,
                    "unanimity": r.unanimity,
                    "news_label": r.news_label,
                    "risk_level": r.risk_level,
                    "horizon": r.horizon,
                    "reasoning": r.reasoning,
                }
                for r in rows
            ]
    except Exception as e:
        logger.warning("get_recent_decisions failed: %s", e)
        return []
