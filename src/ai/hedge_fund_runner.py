"""AI 对冲基金运行器

接受已有的数据摘要，并行调用选定的 analyst agents，返回投票结果。
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from src.config import ApiProvider
from src.ai.hedge_fund_agents import ANALYST_BY_ID, HEDGE_FUND_ANALYSTS

logger = logging.getLogger(__name__)


def build_data_context(symbol: str, name: str, price: float,
                       fundamentals: dict, normalized: dict,
                       moat: dict, dcf: dict, tech: dict,
                       line_items=None, insider_trades=None, news_articles=None) -> str:
    """将现有分析数据构造成大师可读的文本摘要"""
    def _f(val, pct=False):
        if val is None:
            return "N/A"
        if pct:
            return "{:.1f}%".format(val)
        return "{:.2f}".format(val) if isinstance(val, float) else str(val)

    lines = [
        "股票: {} ({})  当前价格: {}".format(symbol, name, price),
        "",
        "## 关键财务指标",
        "PE: {}  PB: {}  ROE: {}  ROA: {}".format(
            _f(normalized.get("pe_trailing")),
            _f(normalized.get("pb")),
            _f(normalized.get("roe"), True),
            _f(normalized.get("roa"), True)),
        "毛利率: {}  净利率: {}  营业利润率: {}".format(
            _f(normalized.get("gross_margin"), True),
            _f(normalized.get("profit_margin"), True),
            _f(normalized.get("operating_margin"), True)),
        "负债权益比: {}  流动比率: {}  速动比率: {}".format(
            _f(normalized.get("debt_to_equity")),
            _f(normalized.get("current_ratio")),
            _f(normalized.get("quick_ratio"))),
        "营收增长: {}  利润增长: {}  EPS增长: {}".format(
            _f(normalized.get("revenue_growth"), True),
            _f(normalized.get("earnings_growth"), True),
            _f(normalized.get("earnings_quarterly_growth"), True)),
        "自由现金流: {}  股息率: {}".format(
            _f(fundamentals.get("free_cashflow")),
            _f(normalized.get("dividend_yield"), True)),
        "市值: {}  市盈率(前瞻): {}".format(
            _f(normalized.get("market_cap")),
            _f(normalized.get("pe_forward"))),
    ]

    if moat and moat.get("percentage") is not None:
        lines.extend([
            "",
            "## 护城河评估",
            "总分: {}/100  等级: {}".format(
                moat.get("percentage", 0), moat.get("grade", "N/A")),
        ])
        if moat.get("dimensions"):
            dims = moat["dimensions"]
            dim_str = "  ".join(
                "{}: {}/{}".format(d["name"], d["score"], d["max"])
                for d in dims[:4]
            )
            lines.append("维度: " + dim_str)

    if tech:
        lines.extend([
            "",
            "## 技术面信号",
            "趋势: {}  动量: {}  RSI: {}  MACD: {}".format(
                tech.get("trend", "N/A"),
                tech.get("momentum", "N/A"),
                _f(tech.get("rsi")),
                _f(tech.get("macd"))),
        ])

    if dcf and dcf.get("method") != "insufficient":
        lines.extend([
            "",
            "## DCF 估值",
            "方法: {}  内在价值: {}  安全边际: {}%".format(
                dcf.get("method", "N/A"),
                _f(dcf.get("intrinsic_value")),
                _f(dcf.get("safety_margin_pct"))),
        ])

    parts = lines

    if line_items:
        parts.append("\n[财务报表详细数据]")
        for k, v in line_items.items():
            if v is not None:
                if isinstance(v, (int, float)):
                    parts.append(f"  {k}: {v:,.0f}")
                else:
                    parts.append(f"  {k}: {v}")

    if insider_trades:
        buys = sum(1 for t in insider_trades
                   if (t.get("transaction_type") or "").lower() in ("buy", "purchase"))
        sells = sum(1 for t in insider_trades
                    if (t.get("transaction_type") or "").lower() in ("sell", "sale"))
        parts.append(f"\n[内幕交易（近期）] 买入:{buys}笔 卖出:{sells}笔")

    if news_articles:
        parts.append("\n[最新新闻]")
        for a in news_articles[:8]:
            title = a.get("title", "")
            time = a.get("time", "")
            sentiment = a.get("sentiment", "")
            time_str = time[:10] if time else ""
            sentiment_str = f" [{sentiment}]" if sentiment else ""
            parts.append(f"  [{time_str}] {title}{sentiment_str}")

    return "\n".join(parts)


def _call_analyst(analyst: dict, data_context: str, provider: ApiProvider) -> dict:
    """调用单个分析师 agent"""
    from src.ai.summarizer import _call_llm

    prompt = analyst["prompt"].format(data=data_context)
    try:
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=350)
        text = text.strip()
        # 去除 DeepSeek R1 think 标签
        think_match = re.search(r'</think>\s*(.*)', text, re.DOTALL)
        if think_match:
            text = think_match.group(1).strip()
        # 去除 markdown code fence
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text).strip()
        result = json.loads(text)
        return {
            **analyst,
            "signal": result.get("signal", "neutral"),
            "confidence": min(100, max(0, int(result.get("confidence", 50)))),
            "reasoning": result.get("reasoning", ""),
            "error": None,
        }
    except Exception as e:
        logger.warning("Analyst %s failed: %s", analyst["name"], e)
        return {
            **analyst,
            "signal": "neutral",
            "confidence": 0,
            "reasoning": "分析失败: {}".format(str(e)[:60]),
            "error": str(e),
        }


def run_hedge_fund(
    symbol: str,
    name: str,
    price: float,
    fundamentals: dict,
    normalized: dict,
    moat: dict,
    dcf: dict,
    tech: dict,
    analyst_ids: list[str],
    provider: ApiProvider,
    max_workers: int = 6,
    line_items=None,
    insider_trades=None,
    news_articles=None,
) -> Optional[dict]:
    """
    并行调用选定的 analysts，返回完整的投票结果。

    Returns:
        {
          "symbol": str,
          "analysts": [...],      # 每位分析师结果
          "consensus": {...},     # 综合信号
          "weighted_score": float,
          "bullish_count": int,
          "bearish_count": int,
          "neutral_count": int,
          "data_context": str,    # 用于调试
        }
    """
    if not provider or not provider.api_key:
        return None

    selected = [ANALYST_BY_ID[aid] for aid in analyst_ids if aid in ANALYST_BY_ID]
    if not selected:
        return None

    data_context = build_data_context(
        symbol, name, price, fundamentals, normalized, moat, dcf, tech,
        line_items=line_items,
        insider_trades=insider_trades,
        news_articles=news_articles,
    )

    results = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(selected))) as executor:
        futures = {
            executor.submit(_call_analyst, a, data_context, provider): a
            for a in selected
        }
        for future in as_completed(futures):
            results.append(future.result())

    # 按原始顺序排序
    id_order = {a["id"]: i for i, a in enumerate(HEDGE_FUND_ANALYSTS)}
    results.sort(key=lambda x: id_order.get(x["id"], 99))

    # 统计票数
    bullish = [r for r in results if r["signal"] == "bullish"]
    bearish = [r for r in results if r["signal"] == "bearish"]
    neutral = [r for r in results if r["signal"] == "neutral"]

    # 加权得分（等权重）
    score_sum = 0.0
    conf_sum = 0.0
    for r in results:
        sv = {"bullish": 1, "bearish": -1, "neutral": 0}.get(r["signal"], 0)
        c = r["confidence"] / 100.0
        score_sum += sv * c
        conf_sum += c

    n = len(results)
    weighted_score = round(score_sum / n * 100, 1) if n > 0 else 0
    avg_conf = round(conf_sum / n * 100) if n > 0 else 0

    # 共识判定
    if weighted_score >= 25:
        consensus_signal = "bullish"
        verdict = "强烈看多" if weighted_score >= 55 else "看多"
    elif weighted_score <= -25:
        consensus_signal = "bearish"
        verdict = "强烈看空" if weighted_score <= -55 else "看空"
    else:
        consensus_signal = "neutral"
        verdict = "分歧，建议观望"

    bull_n, bear_n, neut_n = len(bullish), len(bearish), len(neutral)
    if bull_n >= n * 0.7 or bear_n >= n * 0.7:
        unanimity = "高度一致"
    elif bull_n >= n * 0.5 or bear_n >= n * 0.5:
        unanimity = "多数一致"
    else:
        unanimity = "分歧明显"

    return {
        "symbol": symbol,
        "analysts": results,
        "consensus": {
            "signal": consensus_signal,
            "verdict": verdict,
            "unanimity": unanimity,
            "confidence": avg_conf,
        },
        "weighted_score": weighted_score,
        "bullish_count": bull_n,
        "bearish_count": bear_n,
        "neutral_count": neut_n,
        "data_context": data_context,
    }


# ----------------------------------------------------------------------------
# Full workflow v2: 4 阶段管道
#   1) 13 大师并行（已有 run_hedge_fund）
#   2) 新闻情绪（news_analyst）
#   3) 风险评估（analysis.risk）
#   4) Portfolio Manager 综合 → 最终决策
# ----------------------------------------------------------------------------

def run_full_workflow(
    symbol: str,
    name: str,
    market: str,
    price: float,
    fundamentals: dict,
    normalized: dict,
    moat: dict,
    dcf: dict,
    tech: dict,
    df_history,
    analyst_ids: list[str],
    provider: ApiProvider,
    fetch_news_fn=None,
    max_workers: int = 6,
) -> Optional[dict]:
    """完整工作流：13 大师 → 新闻 → 风险 → Portfolio Manager。

    Args:
        df_history: 历史行情 DataFrame（用于波动率）
        fetch_news_fn: 注入式（默认懒加载 fetch_stock_news），便于测试与解耦

    Returns:
        在原 run_hedge_fund 输出基础上追加：
        - news_sentiment: dict
        - risk: dict
        - final_decision: dict (来自 portfolio_manager)
    """
    # ---- Fetch enriched data via provider router ----
    try:
        from src.data.provider import (
            get_enhanced_fundamentals, get_line_items,
            get_insider_trades, get_news_for_analysts,
        )
        from src.config import load_config as _load_cfg
        try:
            _fd_key = getattr(_load_cfg().api, "financial_datasets_api_key", "") or ""
        except Exception:
            _fd_key = ""

        fundamentals = get_enhanced_fundamentals(symbol, market, fundamentals, _fd_key)

        _line_items = get_line_items(symbol, market, [
            "capital_expenditure", "depreciation_and_amortization",
            "free_cash_flow", "dividends_and_equivalents",
            "research_and_development", "revenue", "net_income",
        ], _fd_key)

        _insider_trades = get_insider_trades(symbol, market, _fd_key)
        _news_articles = get_news_for_analysts(symbol, market, _fd_key, limit=10)
    except Exception:
        _line_items = {}
        _insider_trades = []
        _news_articles = []
        _fd_key = ""

    # ---- Stage 1: 13 大师投票 ----
    hedge = run_hedge_fund(symbol, name, price, fundamentals, normalized, moat, dcf, tech,
                           analyst_ids, provider, max_workers=max_workers,
                           line_items=_line_items,
                           insider_trades=_insider_trades,
                           news_articles=_news_articles)
    if not hedge:
        return None
    votes = hedge["analysts"]

    # ---- Stage 2: 新闻情绪 ----
    from src.ai.news_analyst import analyze_news_sentiment
    if fetch_news_fn is None:
        from src.data.news import fetch_stock_news
        fetch_news_fn = fetch_stock_news
    try:
        articles = fetch_news_fn(symbol, market, limit=10) or []
    except Exception as e:
        logger.warning("Fetch news failed for %s: %s", symbol, e)
        articles = []
    news_sentiment = analyze_news_sentiment(symbol, name, articles, provider).to_dict()

    # ---- Stage 3: 风险评估 ----
    from src.analysis.risk import calculate_volatility, calculate_position_limit
    vol = calculate_volatility(df_history) if df_history is not None else None
    pos = calculate_position_limit(vol or {})
    risk = {
        "annual_vol_pct": round((vol or {}).get("annual_vol", 0) * 100, 1) if vol else None,
        "regime": (vol or {}).get("regime"),
        "risk_level": pos.get("risk_level"),
        "max_position_pct": pos.get("max_position_pct"),
        "rationale": pos.get("rationale"),
    }

    # ---- Stage 4: Portfolio Manager ----
    from src.ai.portfolio_manager import make_final_decision
    valuation = {
        "price": price,
        "intrinsic_value": (dcf or {}).get("intrinsic_value"),
        "safety_margin_pct": (dcf or {}).get("safety_margin_pct"),
    }
    final = make_final_decision(
        symbol=symbol, name=name, price=price,
        votes=votes, news=news_sentiment, risk=risk,
        valuation=valuation, provider=provider,
    )

    result = {
        **hedge,
        "price": price,
        "market": market,
        "name": name,
        "news_sentiment": news_sentiment,
        "risk": risk,
        "final_decision": final,
        "data_source": fundamentals.get("_data_source", "yfinance"),
    }

    # ---- Stage 5: 决策落库（容错，不影响 UI 主流程）----
    try:
        from src.db.decisions import persist_decision
        provider_name = getattr(provider, "model", None) or getattr(provider, "name", None) or str(type(provider).__name__)
        decision_id = persist_decision(symbol, market, name, result, provider_name=provider_name)
        if decision_id:
            result["decision_id"] = decision_id
    except Exception as e:
        logger.warning("Decision persistence skipped for %s: %s", symbol, e)

    return result
