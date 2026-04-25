"""AI 分析接口 — 支持 SSE 流式输出"""

import json
import asyncio
from typing import Union

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from schemas import (
    StepPayload,
    QuotePayload,
    FundamentalsPayload,
    TechnicalPayload,
    ValuationPayload,
    RiskPayload,
    AISummaryPayload,
    MessagePayload,
)
from src.config import load_config, get_active_provider
from src.data.price import fetch_quote, fetch_history
from src.data.financial import fetch_fundamentals
from src.analysis.fundamental import analyze_buffett, _normalize_fundamentals
from src.analysis.moat import score_moat
from src.analysis.technical import compute_indicators, generate_technical_signal, generate_ensemble_signal
from src.analysis.valuation import calc_dcf, calc_multi_model_valuation
from src.analysis.risk import calculate_volatility, calculate_position_limit, generate_risk_report

router = APIRouter()


def _sse(event: str, data: Union[BaseModel, dict]) -> str:
    """Format an SSE frame. Pydantic models are model_dump'd; dicts pass through."""
    payload = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _stream_analysis(ticker: str, market: str):
    """异步生成分析步骤，逐步 yield SSE 事件"""
    config = load_config()
    provider = get_active_provider(config)

    yield _sse("step", StepPayload(step="quote", msg="获取行情数据..."))
    await asyncio.sleep(0)

    quote = fetch_quote(ticker, market) or {}
    if not quote:
        yield _sse("error", MessagePayload(msg=f"找不到股票: {ticker}"))
        return

    price = float(quote.get("price") or quote.get("regularMarketPrice") or 0)
    name = quote.get("shortName") or quote.get("longName") or ticker
    yield _sse("quote", QuotePayload(ticker=ticker, name=name, price=price))
    await asyncio.sleep(0)

    yield _sse("step", StepPayload(step="fundamentals", msg="加载基本面..."))
    fundamentals = fetch_fundamentals(ticker, market) or {}
    normalized = _normalize_fundamentals(fundamentals)
    yield _sse("fundamentals", FundamentalsPayload(normalized=normalized))
    await asyncio.sleep(0)

    yield _sse("step", StepPayload(step="technical", msg="计算技术指标..."))
    tech: dict = {}
    ensemble = None
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
        ensemble = generate_ensemble_signal(df)
    yield _sse("technical", TechnicalPayload(tech=tech, ensemble=ensemble))
    await asyncio.sleep(0)

    yield _sse("step", StepPayload(step="valuation", msg="估值计算..."))
    buffett = analyze_buffett(fundamentals, normalized)
    moat = score_moat(fundamentals, normalized)
    dcf = calc_dcf(price, fundamentals, normalized) if price > 0 else {}
    multi_val = calc_multi_model_valuation(price, fundamentals, normalized) if price > 0 else None
    yield _sse("valuation", ValuationPayload(buffett=buffett, moat=moat, dcf=dcf, multi_val=multi_val))
    await asyncio.sleep(0)

    yield _sse("step", StepPayload(step="risk", msg="风险评估..."))
    volatility = calculate_volatility(df) if df is not None and not df.empty else None
    position = calculate_position_limit(volatility) if volatility else None
    risk_report = generate_risk_report(volatility, position, dcf=dcf) if volatility else None
    yield _sse("risk", RiskPayload(volatility=volatility, position=position, risk_report=risk_report))
    await asyncio.sleep(0)

    if not provider:
        yield _sse("done", MessagePayload(msg="未配置 API Key，跳过 AI 分析"))
        return

    yield _sse("step", StepPayload(step="ai", msg="AI 综合分析..."))

    # 调用 AI 分析（同步转异步）
    try:
        from src.ai.summarizer import analyze_stock
        from src.analysis.signals import AnalysisResult

        result = AnalysisResult(
            symbol=ticker,
            name=name,
            market=market,
            price=price,
            change_pct=quote.get("regularMarketChangePercent") or 0,
            fundamentals=fundamentals,
            buffett_result=buffett,
            tech_signal=tech,
        )
        loop = asyncio.get_event_loop()
        ai_result = await loop.run_in_executor(
            None,
            lambda: analyze_stock(result, normalized, moat, dcf, provider)
        )
        yield _sse("ai", AISummaryPayload(summary=ai_result))
    except Exception as e:
        yield _sse("ai_error", MessagePayload(msg=str(e)))

    yield _sse("done", MessagePayload(msg="分析完成"))


@router.get("/{ticker}/stream")
def stream_analysis(
    ticker: str,
    market: str = Query("US", description="US / CN / HK"),
):
    """SSE 流式分析 — 逐步返回每个分析阶段的结果"""
    ticker = ticker.upper()

    return StreamingResponse(
        _stream_analysis(ticker, market),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
