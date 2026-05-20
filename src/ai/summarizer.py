"""AI 分析引擎 — 支持多 Provider"""

import json
import logging
import math
import re
from typing import Optional, List

from src.ai.prompts import (BUFFETT_ANALYSIS_PROMPT, MARKET_OVERVIEW_PROMPT,
                             CHAT_SYSTEM_PROMPT, DIMENSION_BRIEF_PROMPT,
                             INSIGHT_CARDS_PROMPT, WEEKLY_REPORT_PROMPT,
                             ASHARE_BRIEF_PROMPT, ASHARE_ANALYSIS_PROMPT)
from src.config import ApiProvider

logger = logging.getLogger(__name__)


_client_cache = {}  # key: (provider_type, api_key, base_url) -> (client_type, client)


def _create_client(provider: ApiProvider):
    """根据 provider 类型创建对应的 client（带缓存，避免重复创建连接池）"""
    cache_key = (provider.provider, provider.api_key, provider.base_url)
    if cache_key in _client_cache:
        return _client_cache[cache_key]

    if provider.provider == "anthropic":
        from anthropic import Anthropic
        result = "anthropic", Anthropic(api_key=provider.api_key)
    elif provider.provider in ("openai_compatible", "openai", "deepseek"):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("需要安装 openai 包: pip install openai")
        kwargs = {"api_key": provider.api_key}
        if provider.base_url:
            kwargs["base_url"] = provider.base_url
        result = "openai", OpenAI(**kwargs)
    else:
        raise ValueError("Unknown provider: {}".format(provider.provider))

    _client_cache[cache_key] = result
    return result


def _call_llm(
    provider: ApiProvider,
    messages: list,
    max_tokens: int = 2000,
    timeout: float = 60.0,
) -> str:
    """统一 LLM 调用接口

    Args:
        timeout: 单次请求超时（秒）。Settings 页 ping 用 15s；批量委员会用默认 60s。
    """
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

        response = client.with_options(timeout=timeout).messages.create(**kwargs)
        return response.content[0].text

    else:
        # OpenAI 兼容格式
        response = client.with_options(timeout=timeout).chat.completions.create(
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


# 关键字段分级（用于数据完整性检查）
_CRITICAL_FIELDS = ["roe", "profit_margin", "debt_to_equity", "free_cashflow"]
_IMPORTANT_FIELDS = ["gross_margin", "current_ratio", "revenue_growth", "earnings_growth", "pb", "pe_trailing"]

_FIELD_LABELS = {
    "roe": "ROE",
    "profit_margin": "净利率",
    "debt_to_equity": "负债权益比",
    "free_cashflow": "自由现金流",
    "gross_margin": "毛利率",
    "current_ratio": "流动比率",
    "revenue_growth": "营收增速",
    "earnings_growth": "利润增速",
    "pb": "PB",
    "pe_trailing": "PE",
}


def _check_data_quality(fundamentals: dict) -> dict:
    """检查关键财务字段完整性，生成数据质量报告。

    Returns dict with:
      - completeness_pct: 0-100
      - missing_critical: list of missing critical field labels
      - missing_important: list of missing important field labels
      - warning_block: 注入 prompt 的警告段落（空字符串 = 数据完整）
    """
    missing_critical = [
        _FIELD_LABELS[f] for f in _CRITICAL_FIELDS
        if fundamentals.get(f) is None
    ]
    missing_important = [
        _FIELD_LABELS[f] for f in _IMPORTANT_FIELDS
        if fundamentals.get(f) is None
    ]

    total = len(_CRITICAL_FIELDS) + len(_IMPORTANT_FIELDS)
    missing_total = len(missing_critical) + len(missing_important)
    completeness_pct = round((total - missing_total) / total * 100)

    if not missing_critical and not missing_important:
        warning_block = ""
    else:
        parts = []
        if missing_critical:
            parts.append("⚠️ 关键数据缺失（{}）：{}".format(
                len(missing_critical), "、".join(missing_critical)))
        if missing_important:
            parts.append("⚠️ 重要数据缺失（{}）：{}".format(
                len(missing_important), "、".join(missing_important)))
        parts.append("数据完整度：{}%".format(completeness_pct))
        warning_block = "\n".join(parts)

    return {
        "completeness_pct": completeness_pct,
        "missing_critical": missing_critical,
        "missing_important": missing_important,
        "warning_block": warning_block,
    }


def get_ai_brief(result, moat: dict, provider: Optional[ApiProvider] = None,
                 history_context: str = "", peer_context: str = "") -> Optional[dict]:
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

    dq = _check_data_quality(fund)

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
        data_quality_warning=dq["warning_block"],
        history_context=history_context,
        peer_context=peer_context,
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


def get_ai_insights(symbol: str, name: str, price: float,
                     fundamentals: dict, normalized: dict,
                     tech_signal: dict, dcf: dict,
                     provider: Optional[ApiProvider] = None) -> Optional[dict]:
    """AI 驱动的 6 维度洞察 — 返回 JSON dict 或 None

    Returns: {"timing": "...", "return_outlook": "...", "risk_assessment": "...",
              "dividend_view": "...", "analyst_consensus": "...", "buffett_verdict": "..."}
    """
    if not provider or not provider.api_key:
        return None

    dq = _check_data_quality(normalized or {})
    sm = dcf.get("safety_margin_pct", "N/A") if dcf and dcf.get("method") != "insufficient" else "N/A"
    iv = dcf.get("intrinsic_value", "N/A") if dcf and dcf.get("method") != "insufficient" else "N/A"

    prompt = INSIGHT_CARDS_PROMPT.format(
        symbol=symbol, name=name, price=price,
        pe=_fmt(normalized.get("pe_trailing") if normalized else None),
        pb=_fmt(normalized.get("pb") if normalized else None),
        roe=_fmt(normalized.get("roe") if normalized else None, pct=True),
        gross_margin=_fmt(normalized.get("gross_margin") if normalized else None, pct=True),
        profit_margin=_fmt(normalized.get("profit_margin") if normalized else None, pct=True),
        debt_to_equity=_fmt(normalized.get("debt_to_equity") if normalized else None),
        current_ratio=_fmt(normalized.get("current_ratio") if normalized else None),
        revenue_growth=_fmt(normalized.get("revenue_growth") if normalized else None, pct=True),
        earnings_growth=_fmt(normalized.get("earnings_growth") if normalized else None, pct=True),
        free_cashflow=_fmt(fundamentals.get("free_cashflow") if fundamentals else None),
        dividend_yield=_fmt(fundamentals.get("dividend_yield") if fundamentals else None, pct=True),
        rsi=_fmt(tech_signal.get("rsi") if tech_signal else None),
        trend=tech_signal.get("trend", "N/A") if tech_signal else "N/A",
        momentum=tech_signal.get("momentum", "N/A") if tech_signal else "N/A",
        intrinsic_value=iv,
        safety_margin=sm,
        analyst_target=_fmt(fundamentals.get("target_mean_price") if fundamentals else None),
        data_quality_warning=dq["warning_block"],
    )

    try:
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=1500)
        text = text.strip()
        # DeepSeek R1 返回 <think>...</think> 推理过程后跟 JSON，需要剥离
        think_match = re.search(r'</think>\s*(.*)', text, re.DOTALL)
        if think_match:
            text = think_match.group(1).strip()
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text).strip()
        return json.loads(text)
    except Exception as e:
        logger.warning("AI insights failed for %s: %s", symbol, e)
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

    dq = _check_data_quality(fundamentals)

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
        data_quality_warning_section=("\n" + dq["warning_block"]) if dq["warning_block"] else "",
        data_completeness=dq["completeness_pct"],
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


def generate_weekly_report(market_data: str, watchlist_summary: str,
                           buffett_indicator: str,
                           provider: Optional[ApiProvider] = None) -> str:
    """生成每周 AI 市场周报"""
    if not provider or not provider.api_key:
        return "API not configured. Please set up API key in Settings."

    prompt = WEEKLY_REPORT_PROMPT.format(
        market_data=market_data,
        watchlist_summary=watchlist_summary,
        buffett_indicator=buffett_indicator,
    )

    try:
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=2000)
        # Handle DeepSeek R1 think tags
        think_match = re.search(r'</think>\s*(.*)', text, re.DOTALL)
        if think_match:
            text = think_match.group(1).strip()
        return text
    except Exception as e:
        logger.error("Weekly report generation failed: %s", e)
        return "Weekly report generation failed: {}".format(e)


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


def get_ashare_brief(result, moat: dict, policy_data: dict,
                     provider: Optional[ApiProvider] = None,
                     history_context: str = "", peer_context: str = "",
                     policy_news: Optional[List] = None) -> Optional[dict]:
    """A股政策驱动结构化投资简报（JSON 格式）

    Args:
        result: 股票分析结果对象
        moat: 护城河评分 dict
        policy_data: get_fifteen_five_alignment() 返回值，含 level/tier1/tier2/all_tags/score 字段
        provider: API provider
        history_context: 历史分析上下文
        peer_context: 同行比较上下文（保留参数，当前未注入 prompt）
        policy_news: 政策新闻列表，每项含 title 字段，最多取前3条

    Returns:
        dict with: verdict, confidence, reason, dimensions, bull_points, bear_points
        Returns None if API unavailable or parsing failed.
    """
    if not provider or not provider.api_key:
        return None

    fund = result.fundamentals

    dq = _check_data_quality(fund)

    # 政策标签，最多8个
    policy_tags = ", ".join(policy_data.get("all_tags", [])[:8]) if policy_data else "N/A"

    # 政策级别
    policy_level = policy_data.get("level", "N/A") if policy_data else "N/A"

    # 政策新闻标题，最多3条，用"|"分隔
    if policy_news:
        titles = [n.get("title", "") for n in policy_news[:3] if n.get("title")]
        policy_news_titles = " | ".join(titles) if titles else "暂无"
    else:
        policy_news_titles = "暂无"

    prompt = ASHARE_BRIEF_PROMPT.format(
        symbol=result.symbol,
        name=result.name,
        total_score=moat.get("percentage", 0),
        grade=moat.get("grade", "N/A"),
        pe=_fmt(fund.get("pe_trailing")),
        pb=_fmt(fund.get("pb")),
        roe=_fmt(fund.get("roe"), pct=True),
        profit_margin=_fmt(fund.get("profit_margin"), pct=True),
        revenue_growth=_fmt(fund.get("revenue_growth"), pct=True),
        earnings_growth=_fmt(fund.get("earnings_growth"), pct=True),
        trend=result.tech_signal.get("trend", "N/A"),
        rsi=_fmt(result.tech_signal.get("rsi")),
        policy_level=policy_level,
        policy_tags=policy_tags,
        policy_news_titles=policy_news_titles,
        data_quality_warning=dq["warning_block"],
        history_context=history_context,
    )

    try:
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=700)
        text = text.strip()
        # Strip DeepSeek R1 think tags
        think_match = re.search(r'</think>\s*(.*)', text, re.DOTALL)
        if think_match:
            text = think_match.group(1).strip()
        # Strip markdown code blocks
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text).strip()
        return json.loads(text)
    except Exception as e:
        logger.warning("A股 AI brief failed for %s: %s", result.symbol, e)
        return None


def analyze_ashare_stock(result, provider: Optional[ApiProvider] = None,
                         moat: Optional[dict] = None,
                         policy_data: Optional[dict] = None,
                         policy_news: Optional[List] = None) -> str:
    """对单只A股进行政策驱动深度分析

    Args:
        result: 股票分析结果对象
        provider: API provider
        moat: 护城河评分 dict
        policy_data: get_fifteen_five_alignment() 返回值，含 level/tier1/tier2/all_tags/score 字段
        policy_news: 政策新闻列表，每项含 title/content 等字段

    Returns:
        str: Markdown 格式深度研报，失败返回默认提示字符串
    """
    if not provider or not provider.api_key:
        return _fallback_analysis(result)

    fund = result.buffett_result
    tech = result.tech_signal
    fundamentals = result.fundamentals

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

    dq = _check_data_quality(fundamentals)

    # 政策字段处理
    if policy_data:
        policy_level = policy_data.get("level", "N/A")
        policy_tags = ", ".join(policy_data.get("all_tags", [])[:8])
    else:
        policy_level = "N/A"
        policy_tags = "N/A"

    # 政策新闻，最多5条，格式化为列表
    if policy_news:
        news_lines = []
        for n in policy_news[:5]:
            title = n.get("title", "")
            if title:
                news_lines.append("- {}".format(title))
        policy_news_str = "\n".join(news_lines) if news_lines else "暂无相关政策新闻"
    else:
        policy_news_str = "暂无相关政策新闻"

    # 申万行业，尝试从 fundamentals 获取，字段名可能为 sw_industry 或 industry
    sw_industry = (fundamentals.get("sw_industry")
                   or fundamentals.get("industry")
                   or "N/A")

    prompt = ASHARE_ANALYSIS_PROMPT.format(
        symbol=result.symbol,
        name=result.name,
        price=result.price,
        change_pct="{:.2f}".format(result.change_pct) if result.change_pct else "N/A",
        sw_industry=sw_industry,
        policy_level=policy_level,
        policy_tags=policy_tags,
        policy_news=policy_news_str,
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
        data_quality_warning_section=("\n" + dq["warning_block"]) if dq["warning_block"] else "",
        data_completeness=dq["completeness_pct"],
    )

    try:
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=2500)
        # Handle DeepSeek R1 think tags
        think_match = re.search(r'</think>\s*(.*)', text, re.DOTALL)
        if think_match:
            text = think_match.group(1).strip()
        return text
    except Exception as e:
        logger.error("A股 AI analysis failed for %s: %s", result.symbol, e)
        return _fallback_analysis(result) + "\n\n(AI 分析不可用: {})".format(e)


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
