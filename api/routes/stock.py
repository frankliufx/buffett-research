"""股票数据接口"""

from fastapi import APIRouter, HTTPException, Query

from src.data.price import fetch_quote, fetch_history
from src.data.financial import fetch_fundamentals
from src.analysis.fundamental import analyze_buffett, _normalize_fundamentals
from src.analysis.moat import score_moat
from src.analysis.technical import compute_indicators, generate_technical_signal
from src.analysis.valuation import calc_dcf

router = APIRouter()


@router.get("/{ticker}")
def get_stock(
    ticker: str,
    market: str = Query("US", description="US / CN / HK"),
):
    """返回股票的完整数据快照（行情 + 基本面 + 技术面 + 估值）"""
    ticker = ticker.upper()

    quote = fetch_quote(ticker, market) or {}
    if not quote:
        raise HTTPException(status_code=404, detail=f"找不到股票: {ticker}")

    price = float(quote.get("price") or quote.get("regularMarketPrice") or 0)
    fundamentals = fetch_fundamentals(ticker, market) or {}
    normalized = _normalize_fundamentals(fundamentals)

    # 技术面
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

    # 估值
    buffett = analyze_buffett(fundamentals, normalized)
    moat = score_moat(fundamentals, normalized)
    dcf = calc_dcf(price, fundamentals, normalized) if price > 0 else {}

    return {
        "ticker": ticker,
        "market": market,
        "name": quote.get("shortName") or quote.get("longName") or ticker,
        "price": price,
        "change_pct": quote.get("regularMarketChangePercent"),
        "normalized": normalized,
        "buffett": buffett,
        "moat": moat,
        "dcf": dcf,
        "tech": tech,
    }
