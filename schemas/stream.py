"""SSE event payload contracts.

Each event sent by /api/analysis/{ticker}/stream has shape:

    event: <name>
    data:  <json payload>

We type the *payload* shapes here. The TypeScript discriminated union over
event names is hand-assembled in `web/lib/types.ts` so the union literal
type names match the FastAPI emitter exactly.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


class StepPayload(_Loose):
    step: str
    msg: str


class QuotePayload(_Loose):
    ticker: str
    name: str
    price: float


class FundamentalsPayload(_Loose):
    normalized: dict[str, Optional[float]] = Field(default_factory=dict)


class TechnicalPayload(_Loose):
    tech: dict[str, Any] = Field(default_factory=dict)
    ensemble: Optional[Any] = None


class ValuationPayload(_Loose):
    buffett: Any = None
    moat: Any = None
    dcf: Any = None
    multi_val: Optional[Any] = None


class RiskPayload(_Loose):
    volatility: Optional[Any] = None
    position: Optional[Any] = None
    risk_report: Optional[Any] = None


class AISummaryPayload(_Loose):
    summary: str


class MessagePayload(_Loose):
    """Generic single-message payload used by `error`, `ai_error`, `done`."""

    msg: str
