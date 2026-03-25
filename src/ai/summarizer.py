"""AI 分析引擎 — 支持多 Provider"""

import json
import logging
import re
from typing import Optional, List

from src.ai.prompts import (BUFFETT_ANALYSIS_PROMPT, MARKET_OVERVIEW_PROMPT,
                             CHAT_SYSTEM_PROMPT, DIMENSION_BRIEF_PROMPT)
from src.config import ApiProvider

logger = logging.getLogger(__name__)


def _create_client(provider: ApiProvider):
    """根据 provider 类型创建对应的 client"""
    if provider.provider == "anthropic":
        from anthropic import Anthropic
        return "anthropic", Anthropic(api_key=provider.api_key)
    elif provider.provider in ("openai_compatible", "openai", "deepseek"):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("需要安装 openai 包: pip install openai")
        kwargs = {"api_key": provider.api_key}
        if provider.base_url:
            kwargs["base_url"] = provider.base_url
        return "openai", OpenAI(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider.provider}")


def _call_llm(provider: ApiProvider, messages: list, max_tokens: int = 2000) -> str:
    """统一 LLM 调用接口"""
    client_type, client = _create_client(provider)

    if client_type == "anthropic":
        # Anthropic 格式：system 放在参数里，messages 只有 user/assistant
        system = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                chat_messages.append(m)

        kwargs = {
            "model": provider.model,
            "max_tokens": max_tokens,
            "messages": chat_messages,
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        return response.content[0].text

    else:
        # OpenAI 兼容格式
        response = client.chat.completions.create(
            model=provider.model,
            max_tokens=max_tokens,
            messages=messages,
        )
        return response.choices[0].message.content


def _fmt(val, pct=False) -> str:
    if val is None:
        return "N/A"
    if pct and isinstance(val, (int, float)):
        return "{:.1f}%".format(val)
    return str(val)


def get_ai_brief(result, moat: dict, provider: Optional[ApiProvider] = None) -> Optional[dict]:
    """自动加载的结构化 AI 投资简报（JSON 格式）

    Returns dict with: verdict, confidence, reason, dimensions, bull_points, bear_points
    Returns None if API unavailable or parsing failed.
    """
    if not provider or not provider.api_key:
        return None

    fund = result.fundamentals
    scores = moat.get("scores", {})

    def sc(name):
        d = scores.get(name, {})
        return d.get("score", 0), d.get("max", 1)

    p_s, p_m = sc("盈利质量")
    md_s, md_m = sc("护城河深度")
    f_s, f_m = sc("财务堡垒")
    g_s, g_m = sc("成长确定性")
    op_s, op_m = sc("市场先生机会")

    prompt = DIMENSION_BRIEF_PROMPT.format(
        symbol=result.symbol,
        name=result.name,
        total_score=moat.get("percentage", 0),
        grade=moat.get("grade", "N/A"),
        pe=_fmt(fund.get("pe_trailing")),
        pb=_fmt(fund.get("pb")),
        roe=_fmt(fund.get("roe"), pct=True),
        profit_margin=_fmt(fund.get("profit_margin"), pct=True),
        gross_margin=_fmt(fund.get("gross_margin"), pct=True),
        debt_to_equity=_fmt(fund.get("debt_to_equity")),
        current_ratio=_fmt(fund.get("current_ratio")),
        revenue_growth=_fmt(fund.get("revenue_growth"), pct=True),
        earnings_growth=_fmt(fund.get("earnings_growth"), pct=True),
        trend=result.tech_signal.get("trend", "N/A"),
        rsi=_fmt(result.tech_signal.get("rsi")),
        profitability_score=p_s, profitability_max=p_m,
        moat_depth_score=md_s, moat_depth_max=md_m,
        fortress_score=f_s, fortress_max=f_m,
        growth_score=g_s, growth_max=g_m,
        opportunity_score=op_s, opportunity_max=op_m,
    )

    try:
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=700)
        text = text.strip()
        # Strip markdown code blocks if present
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text).strip()
        return json.loads(text)
    except Exception as e:
        logger.warning("AI brief failed for %s: %s", result.symbol, e)
        return None


def analyze_stock(result, provider: Optional[ApiProvider] = None,
                  moat: Optional[dict] = None) -> str:
    """对单只股票进行 AI 深度分析"""
    if not provider or not provider.api_key:
        return _fallback_analysis(result)

    fund = result.buffett_result
    tech = result.tech_signal
    fundamentals = result.fundamentals

    market_labels = {"us": "美股", "hk": "港股", "a_share": "A股"}

    # Extract moat dimension scores if available
    scores = moat.get("scores", {}) if moat else {}
    def sc(name):
        d = scores.get(name, {})
        return d.get("score", 0), d.get("max", 1)
    p_s, p_m = sc("盈利质量")
    md_s, md_m = sc("护城河深度")
    f_s, f_m = sc("财务堡垒")
    g_s, g_m = sc("成长确定性")
    op_s, op_m = sc("市场先生机会")

    prompt = BUFFETT_ANALYSIS_PROMPT.format(
        symbol=result.symbol,
        name=result.name,
        price=result.price,
        change_pct="{:.2f}".format(result.change_pct) if result.change_pct else "N/A",
        market_label=market_labels.get(result.market, result.market),
        moat_total=moat.get("percentage", 0) if moat else "N/A",
        moat_grade=moat.get("grade", "N/A") if moat else "N/A",
        profitability_score=p_s, profitability_max=p_m,
        moat_depth_score=md_s, moat_depth_max=md_m,
        fortress_score=f_s, fortress_max=f_m,
        growth_score=g_s, growth_max=g_m,
        opportunity_score=op_s, opportunity_max=op_m,
        buffett_grade=fund.get("grade", "N/A"),
        buffett_score=fund.get("total_score", 0),
        buffett_max=fund.get("max_score", 100),
        buffett_pct=fund.get("percentage", 0),
        buffett_details="\n".join(fund.get("details", [])),
        trend=tech.get("trend", "N/A"),
        momentum=tech.get("momentum", "N/A"),
        rsi=_fmt(tech.get("rsi")),
        tech_signals="\n".join("- {}".format(s) for s in tech.get("signals", [])),
        pe=_fmt(fundamentals.get("pe_trailing")),
        pb=_fmt(fundamentals.get("pb")),
        roe=_fmt(fundamentals.get("roe"), pct=True),
        profit_margin=_fmt(fundamentals.get("profit_margin"), pct=True),
        gross_margin=_fmt(fundamentals.get("gross_margin"), pct=True),
        debt_to_equity=_fmt(fundamentals.get("debt_to_equity")),
        current_ratio=_fmt(fundamentals.get("current_ratio")),
        revenue_growth=_fmt(fundamentals.get("revenue_growth"), pct=True),
        earnings_growth=_fmt(fundamentals.get("earnings_growth"), pct=True),
        dividend_yield=_fmt(fundamentals.get("dividend_yield"), pct=True),
        free_cashflow=_fmt(fundamentals.get("free_cashflow")),
    )

    try:
        return _call_llm(provider, [{"role": "user", "content": prompt}])
    except Exception as e:
        logger.error(f"AI analysis failed for {result.symbol}: {e}")
        return _fallback_analysis(result) + "\n\n(AI 分析不可用: {})".format(e)


def generate_market_overview(results: list, provider: Optional[ApiProvider] = None) -> str:
    """生成市场总览"""
    summary_lines = []
    for r in results:
        grade = r.buffett_result.get("grade", "?")
        pct = r.buffett_result.get("percentage", 0)
        trend = r.tech_signal.get("trend", "?")
        summary_lines.append(
            "- {} ({}): 巴菲特评级 {} ({}%) | 趋势 {} | 建议: {}".format(
                r.symbol, r.name, grade, pct, trend, r.recommendation)
        )

    stocks_summary = "\n".join(summary_lines)

    if not provider or not provider.api_key:
        return "## 今日关注列表\n\n{}".format(stocks_summary)

    prompt = MARKET_OVERVIEW_PROMPT.format(stocks_summary=stocks_summary)
    try:
        return _call_llm(provider, [{"role": "user", "content": prompt}])
    except Exception as e:
        logger.error(f"Market overview AI failed: {e}")
        return "## 今日关注列表\n\n{}\n\n(AI 总览不可用: {})".format(stocks_summary, e)


def chat_with_analyst(messages: list, provider: Optional[ApiProvider] = None,
                      context: str = "") -> str:
    """与 AI 分析师对话

    Args:
        messages: 对话历史 [{"role": "user"/"assistant", "content": "..."}]
        provider: API provider
        context: 当前股票分析数据上下文
    """
    if not provider or not provider.api_key:
        return "请先在「设置」页面配置 API Key 后使用 AI 对话功能。"

    system = CHAT_SYSTEM_PROMPT
    if context:
        system += "\n\n## 当前分析数据\n" + context

    full_messages = [{"role": "system", "content": system}] + messages

    try:
        return _call_llm(provider, full_messages, max_tokens=3000)
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return "AI 对话出错: {}".format(e)


def _fallback_analysis(result) -> str:
    """无 API Key 时的本地分析"""
    fund = result.buffett_result
    tech = result.tech_signal

    lines = [
        "## {} ({}) -- 本地分析".format(result.symbol, result.name),
        "",
        "**巴菲特评级: {}** ({}%)".format(fund.get('grade', 'N/A'), fund.get('percentage', 0)),
        "**建议: {}**".format(fund.get('recommendation', 'N/A')),
        "",
        "### 基本面评估",
    ]
    for d in fund.get("details", []):
        lines.append("- {}".format(d))

    lines.extend([
        "",
        "### 技术面参考",
        "- 趋势: {}".format(tech.get('trend', 'N/A')),
        "- 动量: {}".format(tech.get('momentum', 'N/A')),
    ])
    for s in tech.get("signals", []):
        lines.append("- {}".format(s))

    lines.extend(["", "### 操作建议", fund.get("action", "")])
    return "\n".join(lines)
