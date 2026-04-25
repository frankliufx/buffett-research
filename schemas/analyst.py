"""Hedge-fund / analyst contracts."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Signal = Literal["bullish", "bearish", "neutral"]


class _Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


class Analyst(_Loose):
    id: str
    name: str
    name_cn: str
    icon: str
    group: str
    style: str


class AnalystResult(Analyst):
    # The hedge-fund runner always emits these — they're not optional in
    # practice, even on a per-analyst error (where `error` is set and the
    # other fields fall back to neutral/0/"").
    signal: Signal
    confidence: float
    reasoning: str
    error: Optional[str] = None


class HedgeFundConsensus(_Loose):
    signal: Signal
    verdict: str
    unanimity: str
    confidence: float


class HedgeFundResult(_Loose):
    # All these are populated by `run_hedge_fund(...)` on every successful
    # run; HTTP errors are raised before this struct is built. Kept required
    # so TS consumers don't need null-checks.
    symbol: str
    analysts: list[AnalystResult]
    consensus: HedgeFundConsensus
    weighted_score: float
    bullish_count: int
    bearish_count: int
    neutral_count: int


class HedgeFundRunRequest(BaseModel):
    """Request body for POST /api/hedge-fund/run."""

    ticker: str
    market: str = "US"
    analyst_ids: Optional[list[str]] = None
