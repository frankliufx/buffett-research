"""SQLAlchemy 2.0 ORM models — mirror docs/SCHEMA.md.

Only the tables we actively use are mapped. Adding more is a matter of
creating new classes; the schema itself is authoritative (see migrations).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index,
    Integer, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DataSource(Base):
    __tablename__ = "data_sources"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[Optional[str]] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    listing_date: Mapped[Optional[date]] = mapped_column(Date)
    delisting_date: Mapped[Optional[date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("market IN ('a_share','us','hk')", name="chk_market"),
    )


class RawFundamentals(Base):
    __tablename__ = "raw_fundamentals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stocks.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(20), ForeignKey("data_sources.code"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class Fundamentals(Base):
    __tablename__ = "fundamentals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stocks.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[str] = mapped_column(String(20), ForeignKey("data_sources.code"), nullable=False)

    # 盈利能力
    revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    net_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    gross_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    operating_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    eps: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # 比率
    roe: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    roa: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    gross_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    operating_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    net_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # 财务结构
    total_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    total_liabilities: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    total_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    debt_to_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    debt_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    current_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    quick_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # 成长
    revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    net_income_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # 现金流
    operating_cash_flow: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    free_cash_flow: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    capex: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    dividend_per_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # 元数据
    quality: Mapped[str] = mapped_column(String(20), nullable=False, default="single_source")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("stock_id", "period", "period_type", "source", name="uq_fund"),
    )


class FetchAudit(Base):
    __tablename__ = "fetch_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(20), ForeignKey("data_sources.code"), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    stock_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("stocks.id"))
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    http_status: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())


class HedgeFundDecision(Base):
    __tablename__ = "hedge_fund_decisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stocks.id"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)

    # 13 大师投票
    analyst_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    bullish_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bearish_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weighted_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    consensus_signal: Mapped[Optional[str]] = mapped_column(String(20))
    consensus_verdict: Mapped[Optional[str]] = mapped_column(String(40))
    unanimity: Mapped[Optional[str]] = mapped_column(String(20))
    votes_payload: Mapped[list] = mapped_column(JSONB, nullable=False)

    # 新闻情绪
    news_score: Mapped[Optional[int]] = mapped_column(Integer)
    news_label: Mapped[Optional[str]] = mapped_column(String(20))
    news_article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    news_payload: Mapped[Optional[dict]] = mapped_column(JSONB)

    # 风险
    annual_vol_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    risk_regime: Mapped[Optional[str]] = mapped_column(String(40))
    risk_level: Mapped[Optional[str]] = mapped_column(String(20))
    max_position_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    risk_payload: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Portfolio Manager 决策
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    conviction: Mapped[str] = mapped_column(String(10), nullable=False)
    combined_score: Mapped[int] = mapped_column(Integer, nullable=False)
    position_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    horizon: Mapped[Optional[str]] = mapped_column(String(40))
    entry_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    stop_loss_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    take_profit_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)

    algorithm_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1.0")
    provider_name: Mapped[Optional[str]] = mapped_column(String(40))
    extra: Mapped[Optional[dict]] = mapped_column(JSONB)
