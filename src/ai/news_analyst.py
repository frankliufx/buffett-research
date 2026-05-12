"""News Analyst — 新闻情绪打分

输入：新闻列表（来自 src.data.news.fetch_stock_news）
输出：dict {sentiment_score: -100..+100, label, themes, bullish, bearish, summary}

设计原则：
- 时间衰减：近 7 天权重高，30 天前权重低
- 单 LLM 批量打分（成本控制）
- 数据不足时返回 neutral，不强行编造
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from src.config import ApiProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NewsSentiment:
    score: int                # -100 (极度看空) .. +100 (极度看好)
    label: str                # "极度看空" | "看空" | "中性" | "看多" | "极度看多"
    themes: tuple[str, ...]   # 主要主题 (如 "财报超预期", "高管减持")
    bullish: tuple[str, ...]  # 利好要点
    bearish: tuple[str, ...]  # 利空要点
    article_count: int
    summary: str

    @classmethod
    def neutral(cls, reason: str = "新闻数据不足") -> "NewsSentiment":
        return cls(0, "中性", (), (), (), 0, reason)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "label": self.label,
            "themes": list(self.themes),
            "bullish": list(self.bullish),
            "bearish": list(self.bearish),
            "article_count": self.article_count,
            "summary": self.summary,
        }


def _label_from_score(score: int) -> str:
    if score >= 60:
        return "极度看多"
    if score >= 20:
        return "看多"
    if score <= -60:
        return "极度看空"
    if score <= -20:
        return "看空"
    return "中性"


def _format_articles(articles: list[dict], max_chars: int = 4000) -> str:
    """构造给 LLM 的精简文本。按时间倒排，截断长度避免 token 浪费。"""
    if not articles:
        return ""
    lines = []
    used = 0
    for i, a in enumerate(articles, 1):
        title = (a.get("title") or "").strip()
        src = (a.get("source") or "").strip()
        when = (a.get("time") or "").strip()
        summary = (a.get("summary") or "").strip()
        snippet = "[{}] {} | {} | {}".format(i, title, src, when)
        if summary and summary != title:
            snippet += "  摘要: " + summary[:120]
        if used + len(snippet) > max_chars:
            break
        lines.append(snippet)
        used += len(snippet)
    return "\n".join(lines)


def _strip_llm_artifacts(text: str) -> str:
    """去掉 think 标签、markdown fence、前后 whitespace。"""
    text = (text or "").strip()
    m = re.search(r"</think>\s*(.*)", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    text = re.sub(r"^```\w*\n?", "", text)
    text = re.sub(r"\n?```$", "", text).strip()
    return text


def analyze_news_sentiment(symbol: str, name: str, articles: list[dict],
                           provider: Optional[ApiProvider]) -> NewsSentiment:
    """打分流程：构造 prompt → LLM → 解析 JSON。"""
    if not articles:
        return NewsSentiment.neutral("无新闻数据")
    if provider is None:
        return NewsSentiment.neutral("AI provider 未配置")

    formatted = _format_articles(articles)
    if not formatted:
        return NewsSentiment.neutral("新闻列表为空")

    prompt = (
        "你是一位资深财经新闻分析师。请对以下关于 {sym}（{name}）的新闻做情绪分析。\n\n"
        "新闻列表（按时间倒排，越靠前越新）：\n{news}\n\n"
        "要求：\n"
        "1. 综合判断这些新闻整体反映的市场情绪，越近的新闻权重越高。\n"
        "2. 区分硬信息（财报、合同、监管）和软信息（分析师观点、传闻）。\n"
        "3. 严格输出 JSON，不要 markdown 包裹，不要解释：\n"
        "{{\n"
        '  "score": -100到100的整数（-100极度看空，0中性，+100极度看多）,\n'
        '  "themes": ["主题1", "主题2"]最多4条,\n'
        '  "bullish": ["利好要点1", ...]最多3条,\n'
        '  "bearish": ["利空要点1", ...]最多3条,\n'
        '  "summary": "1-2句话整体结论，要具体不要套话"\n'
        "}}"
    ).format(sym=symbol, name=name, news=formatted)

    try:
        from src.ai.summarizer import _call_llm
        raw = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=500)
        text = _strip_llm_artifacts(raw)
        data = json.loads(text)
    except Exception as e:
        logger.warning("News sentiment LLM failed for %s: %s", symbol, e)
        return NewsSentiment.neutral("LLM 调用失败")

    try:
        score = int(data.get("score", 0))
        score = max(-100, min(100, score))
    except (TypeError, ValueError):
        score = 0

    return NewsSentiment(
        score=score,
        label=_label_from_score(score),
        themes=tuple(str(t) for t in (data.get("themes") or [])[:4]),
        bullish=tuple(str(t) for t in (data.get("bullish") or [])[:3]),
        bearish=tuple(str(t) for t in (data.get("bearish") or [])[:3]),
        article_count=len(articles),
        summary=str(data.get("summary") or "").strip()[:200],
    )
