"""Stock-level data contracts."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Market = Literal["US", "CN", "HK"]


class _Loose(BaseModel):
    """Base model that accepts extra fields without raising.

    Several upstream analyzers return rich, evolving payloads. We anchor the
    well-known keys with types but pass through anything else unchanged so
    one analyzer extending its output doesn't break the API contract.
    """

    model_config = ConfigDict(extra="allow")


class Quote(_Loose):
    ticker: str
    name: str
    price: float
    change_pct: Optional[float] = None
    market: Market = "US"


class MoatDimension(_Loose):
    name: Optional[str] = None
    score: Optional[float] = None
    weight: Optional[float] = None
    notes: Optional[str] = None


class MoatScore(_Loose):
    percentage: float = 0.0
    grade: str = "N/A"
    dimensions: list[MoatDimension] = Field(default_factory=list)


class DCFResult(_Loose):
    intrinsic_value: Optional[float] = None
    safety_margin_pct: Optional[float] = None
    method: Optional[str] = None


class TechSignal(_Loose):
    trend: Optional[str] = None
    momentum: Optional[str] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None


class StockData(_Loose):
    ticker: str
    market: Market
    name: str
    price: float
    change_pct: Optional[float] = None
    normalized: dict[str, Optional[float]] = Field(default_factory=dict)
    buffett: dict[str, Any] = Field(default_factory=dict)
    moat: MoatScore = Field(default_factory=MoatScore)
    dcf: DCFResult = Field(default_factory=DCFResult)
    tech: TechSignal = Field(default_factory=TechSignal)
