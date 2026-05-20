"""AI 对冲基金接口"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import load_config, get_active_provider
from src.data.price import fetch_quote, fetch_history
from src.data.financial import fetch_fundamentals
from src.analysis.fundamental import analyze_buffett, _normalize_fundamentals
from src.analysis.moat import score_moat
from src.analysis.valuation import calc_dcf
from src.analysis.technical import compute_indicators, generate_technical_signal
from src.ai.hedge_fund_runner import run_hedge_fund
from src.ai.hedge_fund_agents import HEDGE_FUND_ANALYSTS

router = APIRouter()


class RunRequest(BaseModel):
    ticker: str
    market: str = "US"
    analyst_ids: Optional[List[str]] = None  # None = 全部


@router.get("/analysts")
def list_analysts():
    """返回所有可用分析师列表"""
    return [
        {
            "id": a["id"],
            "name": a["name"],
            "name_cn": a["name_cn"],
            "icon": a["icon"],
            "group": a["group"],
            "style": a["style"],
        }
        for a in HEDGE_FUND_ANALYSTS
    ]


@router.post("/run")
def run_analysis(req: RunRequest):
    """运行多大师并行分析"""
    ticker = req.ticker.upper()
    market = req.market

    config = load_config()
    provider = get_active_provider(config)
    if not provider:
        raise HTTPException(status_code=400, detail="未配置 API Key")

    # 默认全选
    analyst_ids = req.analyst_ids or [a["id"] for a in HEDGE_FUND_ANALYSTS]

    # 拉取数据
    quote = fetch_quote(ticker, market) or {}
    if not quote:
        raise HTTPException(status_code=404, detail=f"找不到股票: {ticker}")

    price = float(quote.get("price") or quote.get("regularMarketPrice") or 0)
    name = quote.get("shortName") or quote.get("longName") or ticker
    fundamentals = fetch_fundamentals(ticker, market) or {}
    normalized = _normalize_fundamentals(fundamentals)
    buffett = analyze_buffett(fundamentals, normalized)
    moat = score_moat(fundamentals, normalized)
    dcf = calc_dcf(price, fundamentals, normalized) if price > 0 else {}

    tech: dict = {}
    df = fetch_history(ticker, market, 365)
    if df is not None and not df.empty:
        df_ind = compute_indicators(df)
        sig = generate_technical_signal(df_ind)
        tech = {
            "trend": sig.get("trend"),
            "momentum": sig.get("momentum"),
            "rsi": sig.get("rsi"),
            "macd": sig.get("macd"),
        }

    from src.config import load_config
    result = run_hedge_fund(
        symbol=ticker,
        name=name,
        price=price,
        fundamentals=fundamentals,
        normalized=normalized,
        moat=moat,
        dcf=dcf,
        tech=tech,
        analyst_ids=analyst_ids,
        provider=provider,
        max_workers=load_config().parallel.hedgefund_workers,
    )

    if not result:
        raise HTTPException(status_code=500, detail="分析失败")

    return result
