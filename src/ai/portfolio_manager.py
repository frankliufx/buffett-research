"""Portfolio Manager — 综合所有信号 → 给出可执行的最终决策

输入：
- 13 大师投票（runner 已聚合的 votes / consensus）
- 新闻情绪（NewsSentiment）
- 风险指标（calculate_volatility + calculate_position_limit）
- 估值快照（DCF intrinsic_value, safety_margin_pct）
- 当前行情（price）

输出：FinalDecision dict，结构见 _build_default_decision()。

设计原则：
1. 量化优先：仓位/止损/止盈用规则算出，不全靠 LLM 猜
2. LLM 只负责"reasoning chain"——把数字串成一段可读的解释
3. 数据缺失时降级而非编造
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from src.config import ApiProvider

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# 数值聚合（不依赖 LLM）
# ----------------------------------------------------------------------------

def _aggregate_votes(votes: list[dict]) -> dict:
    """对 13 大师投票做加权合计。

    返回：
        bullish_weight, bearish_weight, neutral_weight  ∈ [0, sum_conf]
        score: -100..+100  最终量化情绪
        unanimity: "一致" | "多数一致" | "分歧"
    """
    bull, bear, neut = 0.0, 0.0, 0.0
    valid = 0
    for v in votes or []:
        sig = (v.get("signal") or "neutral").lower()
        conf = float(v.get("confidence") or 0)
        if conf <= 0:
            continue
        valid += 1
        if sig == "bullish":
            bull += conf
        elif sig == "bearish":
            bear += conf
        else:
            neut += conf

    total_signed = bull + bear
    if total_signed <= 0:
        score = 0
    else:
        score = int(round((bull - bear) / (bull + bear + neut) * 100))

    # 一致性：取多数票占比
    sig_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    for v in votes or []:
        if (v.get("confidence") or 0) > 0:
            sig_counts[(v.get("signal") or "neutral").lower()] = \
                sig_counts.get((v.get("signal") or "neutral").lower(), 0) + 1
    if valid == 0:
        unanimity = "无效投票"
    else:
        max_share = max(sig_counts.values()) / valid
        if max_share >= 0.85:
            unanimity = "一致"
        elif max_share >= 0.55:
            unanimity = "多数一致"
        else:
            unanimity = "分歧"

    return {
        "score": score,
        "bullish_weight": int(bull),
        "bearish_weight": int(bear),
        "neutral_weight": int(neut),
        "unanimity": unanimity,
        "valid_votes": valid,
    }


def _combined_signal(vote_score: int, news_score: int) -> int:
    """综合大师票 (70%) + 新闻情绪 (30%) → -100..+100 总分。"""
    return int(round(vote_score * 0.7 + news_score * 0.3))


def _decide_action(combined: int, safety_margin_pct: Optional[float]) -> tuple[str, str]:
    """规则决定动作 + 置信度等级。

    安全边际加权：高边际 (>30%) 在偏多时给加仓建议，深度负边际抑制买入。
    """
    margin = safety_margin_pct if safety_margin_pct is not None else 0

    if combined >= 50 and margin >= 20:
        return "买入", "高"
    if combined >= 30 or (combined >= 20 and margin >= 30):
        return "加仓", "中"
    if combined <= -50 and margin <= 0:
        return "卖出", "高"
    if combined <= -30 or (combined <= -20 and margin <= -20):
        return "减仓", "中"
    return "持有", "中" if abs(combined) >= 15 else "低"


def _decide_position_pct(action: str, max_position_pct: float, conviction: str) -> float:
    """基于动作、风险上限、置信度 → 建议仓位比例。"""
    base = {"买入": 0.85, "加仓": 0.6, "持有": 0.4, "减仓": 0.2, "卖出": 0.0}.get(action, 0.4)
    conv_mult = {"高": 1.0, "中": 0.75, "低": 0.5}.get(conviction, 0.75)
    pct = max_position_pct * base * conv_mult
    return round(pct, 1)


def _decide_entry_zone(price: float, intrinsic_value: Optional[float]) -> dict:
    """入场区间：估值锚 ± 5%，无估值时用现价 ± 3%。"""
    if intrinsic_value and intrinsic_value > 0:
        anchor = min(price, intrinsic_value * 0.9)  # 9折以内更优
        return {
            "ideal": round(anchor * 0.97, 2),
            "acceptable": round(anchor * 1.0, 2),
            "expensive_above": round(anchor * 1.05, 2),
            "anchor": "估值 90% 折扣区",
        }
    return {
        "ideal": round(price * 0.97, 2),
        "acceptable": round(price, 2),
        "expensive_above": round(price * 1.03, 2),
        "anchor": "当前价格区间",
    }


def _decide_stop_loss(price: float, vol_annual_pct: float, action: str) -> dict:
    """止损：买入/加仓 → 现价 - max(8%, 1×日波动)；持有/减仓 → 现价 - 12%。

    日波动 ≈ 年化波动 / sqrt(252)。
    """
    if action in ("卖出",):
        return {"price": None, "rationale": "已卖出，无需止损"}
    daily_vol = vol_annual_pct / 100 / 15.87  # sqrt(252) ≈ 15.87
    pct_drop = max(0.08, daily_vol * 2.5)
    if action in ("持有", "减仓"):
        pct_drop = max(0.12, pct_drop)
    stop = price * (1 - pct_drop)
    return {
        "price": round(stop, 2),
        "drop_pct": round(pct_drop * 100, 1),
        "rationale": "现价下跌 {:.0f}% 触发，约 2.5× 日波动安全垫".format(pct_drop * 100),
    }


def _decide_take_profit(price: float, intrinsic_value: Optional[float]) -> dict:
    """止盈：估值锚附近为目标价；无估值时用 +25%。"""
    if intrinsic_value and intrinsic_value > 0:
        target = max(intrinsic_value, price * 1.15)
        return {
            "price": round(target, 2),
            "rationale": "估值上限 {:.2f} 或现价 +15%（取较大者）".format(intrinsic_value),
        }
    return {
        "price": round(price * 1.25, 2),
        "rationale": "现价 +25%（无估值锚时的默认目标）",
    }


# ----------------------------------------------------------------------------
# LLM reasoning chain
# ----------------------------------------------------------------------------

def _build_reasoning_prompt(symbol: str, name: str, agg: dict, news: dict,
                            risk: dict, valuation: dict, action: str) -> str:
    return (
        "你是一位 portfolio manager。基于以下信号，写一段 200-280 字的中文推理链，"
        "解释为什么对 {sym}（{name}）给出'{action}'的建议。\n\n"
        "## 大师团队投票\n"
        "score={score}（-100极空，+100极多）  bullish={bull}  bearish={bear}  neutral={neut}  一致性={una}\n\n"
        "## 新闻情绪\n"
        "score={n_score}（{n_label}）  主题={themes}\n"
        "利好: {bullish}\n利空: {bearish}\n摘要: {n_summary}\n\n"
        "## 风险与估值\n"
        "年化波动={vol:.0f}%  风险={risk_level}  仓位上限={max_pos:.1f}%\n"
        "现价={price}  内在价值={iv}  安全边际={margin}%\n\n"
        "要求：\n"
        "1. 第一句直接给出关键判断（不要套话，不要'综合来看'开头）\n"
        "2. 中间分析最重要的 2-3 条事实及它们的相互印证或冲突\n"
        "3. 最后说明这个建议的关键前提，以及什么会改变结论\n"
        "4. 不要重复输入数据，要有判断有取舍"
    ).format(
        sym=symbol, name=name, action=action,
        score=agg["score"], bull=agg["bullish_weight"], bear=agg["bearish_weight"],
        neut=agg["neutral_weight"], una=agg["unanimity"],
        n_score=news.get("score", 0), n_label=news.get("label", "中性"),
        themes=", ".join(news.get("themes", []) or ["无"]),
        bullish="; ".join(news.get("bullish", []) or ["无"]),
        bearish="; ".join(news.get("bearish", []) or ["无"]),
        n_summary=news.get("summary", "")[:120],
        vol=risk.get("annual_vol_pct", 0),
        risk_level=risk.get("risk_level", "未知"),
        max_pos=risk.get("max_position_pct", 10),
        price=valuation.get("price", 0),
        iv=valuation.get("intrinsic_value") or "N/A",
        margin=valuation.get("safety_margin_pct") or 0,
    )


def _strip_llm(text: str) -> str:
    text = (text or "").strip()
    m = re.search(r"</think>\s*(.*)", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    text = re.sub(r"^```\w*\n?", "", text)
    text = re.sub(r"\n?```$", "", text).strip()
    return text


def _generate_reasoning(prompt: str, provider: Optional[ApiProvider]) -> str:
    if provider is None:
        return "（AI provider 未配置，跳过推理生成）"
    try:
        from src.ai.summarizer import _call_llm
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=600)
        return _strip_llm(text)
    except Exception as e:
        logger.warning("Reasoning LLM failed: %s", e)
        return "（推理生成失败：{}）".format(str(e)[:80])


# ----------------------------------------------------------------------------
# 公开入口
# ----------------------------------------------------------------------------

def make_final_decision(
    symbol: str,
    name: str,
    price: float,
    votes: list[dict],
    news: dict,
    risk: dict,
    valuation: dict,
    provider: Optional[ApiProvider] = None,
) -> dict:
    """综合所有信号 → FinalDecision。

    Args:
        votes: hedge_fund_runner 输出的 votes
        news: NewsSentiment.to_dict() 或 {} 表示缺数据
        risk: {annual_vol_pct, risk_level, max_position_pct}
        valuation: {price, intrinsic_value, safety_margin_pct}
    """
    agg = _aggregate_votes(votes)
    combined = _combined_signal(agg["score"], int(news.get("score") or 0))

    safety_margin = valuation.get("safety_margin_pct")
    action, conviction = _decide_action(combined, safety_margin)
    max_pos = float(risk.get("max_position_pct") or 10.0)
    position_pct = _decide_position_pct(action, max_pos, conviction)
    entry = _decide_entry_zone(price, valuation.get("intrinsic_value"))
    stop = _decide_stop_loss(price, float(risk.get("annual_vol_pct") or 25.0), action)
    take = _decide_take_profit(price, valuation.get("intrinsic_value"))

    prompt = _build_reasoning_prompt(symbol, name, agg, news or {}, risk or {}, valuation or {}, action)
    reasoning = _generate_reasoning(prompt, provider)

    horizon = (
        "短期(1-3月)" if abs(combined) >= 50
        else "中期(3-12月)" if abs(combined) >= 20
        else "长期(>1年)"
    )

    return {
        "action": action,
        "conviction": conviction,
        "combined_score": combined,
        "position_pct": position_pct,
        "entry_zone": entry,
        "stop_loss": stop,
        "take_profit": take,
        "horizon": horizon,
        "vote_aggregate": agg,
        "news_sentiment": news or {},
        "risk_summary": risk or {},
        "reasoning": reasoning,
    }
