"""Shared schema contracts.

Single source of truth for data shapes flowing between the Python backend
(FastAPI + Streamlit) and the Next.js frontend.

The Pydantic v2 models defined here are:
- Imported directly by FastAPI routes (via `response_model=`)
- Importable from Streamlit pages (gradual adoption)
- Auto-converted to `web/lib/types.generated.ts` via `make types`
"""

from schemas.stock import (
    Market,
    Quote,
    MoatDimension,
    MoatScore,
    DCFResult,
    TechSignal,
    StockData,
)
from schemas.analyst import (
    Signal,
    Analyst,
    AnalystResult,
    HedgeFundConsensus,
    HedgeFundResult,
    HedgeFundRunRequest,
)
from schemas.stream import (
    StepPayload,
    QuotePayload,
    FundamentalsPayload,
    TechnicalPayload,
    ValuationPayload,
    RiskPayload,
    AISummaryPayload,
    MessagePayload,
)

__all__ = [
    # stock
    "Market",
    "Quote",
    "MoatDimension",
    "MoatScore",
    "DCFResult",
    "TechSignal",
    "StockData",
    # analyst
    "Signal",
    "Analyst",
    "AnalystResult",
    "HedgeFundConsensus",
    "HedgeFundResult",
    "HedgeFundRunRequest",
    # stream
    "StepPayload",
    "QuotePayload",
    "FundamentalsPayload",
    "TechnicalPayload",
    "ValuationPayload",
    "RiskPayload",
    "AISummaryPayload",
    "MessagePayload",
]
