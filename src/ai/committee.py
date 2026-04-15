"""投资委员会 — 多Agent并行分析，加权投票决策

借鉴 ai-hedge-fund 的多Agent架构：
每位投资大师独立分析同一只股票，输出信号+置信度+理由，
最终加权综合，给出委员会决议。

5位大师：
1. 巴菲特 — 护城河+Owner Earnings+安全边际
2. 芒格 — 逆向清单思维+ROIC+排除法
3. Peter Lynch — PEG+生活化选股+十倍股潜力
4. Michael Burry — 逆向深度价值+做空视角+尾部风险
5. 段永平 — 本分+商业模式+Stop Doing List
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from src.config import ApiProvider

logger = logging.getLogger(__name__)

# ── 大师定义 ────────────────────────────────────────────────────────────────

MASTERS = [
    {
        "id": "buffett",
        "name": "Warren Buffett",
        "name_cn": "巴菲特",
        "icon": "🏛️",
        "weight": 0.25,
        "style": "价值投资之王",
        "prompt": """你是沃伦·巴菲特。你只买自己能看懂的生意，关注护城河的深度和宽度、
Owner Earnings（净利润+折旧-维护性资本开支）、管理层诚信、以及安全边际。
你讨厌高负债、讨厌频繁并购、讨厌看不懂的生意。
你的格言："用合理的价格买入优秀的公司，远胜于用便宜的价格买入平庸的公司。"

基于以下数据，以巴菲特的视角分析这只股票：
{data}

严格按此JSON格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数, "reasoning": "不超过80字的分析理由，必须体现巴菲特风格"}}""",
    },
    {
        "id": "munger",
        "name": "Charlie Munger",
        "name_cn": "芒格",
        "icon": "🧠",
        "weight": 0.20,
        "style": "逆向思维大师",
        "prompt": """你是查理·芒格。你用逆向思维——"告诉我会死在哪里，我就不去那里"。
你关注 ROIC（投资资本回报率）、商业模式的可预测性、管理层是否理性配置资本。
你用排除法：先排除所有可能亏钱的理由，剩下的才值得投资。
你讨厌：高杠杆、周期性太强、依赖单一客户、管理层过度激励。

基于以下数据，以芒格的视角分析这只股票：
{data}

严格按此JSON格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数, "reasoning": "不超过80字的分析理由，必须体现芒格的逆向清单风格"}}""",
    },
    {
        "id": "lynch",
        "name": "Peter Lynch",
        "name_cn": "彼得·林奇",
        "icon": "📈",
        "weight": 0.20,
        "style": "十倍股猎手",
        "prompt": """你是彼得·林奇。你相信"买你了解的公司"，善于从日常生活中发现投资机会。
你最看重 PEG（PE/增长率），PEG<1是你最爱的信号。
你把股票分为6类：慢速增长、稳定增长、快速增长、周期、困境反转、资产隐蔽。
你喜欢：高增长+低PE、机构持仓少的被忽略股票、有明确故事可讲的公司。
你讨厌：热门股、多元化收购狂、没有盈利的概念股。

基于以下数据，以林奇的视角分析这只股票：
{data}

严格按此JSON格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数, "reasoning": "不超过80字的分析理由，必须体现林奇的实用主义风格"}}""",
    },
    {
        "id": "burry",
        "name": "Michael Burry",
        "name_cn": "迈克尔·伯里",
        "icon": "🔍",
        "weight": 0.15,
        "style": "逆向深度价值",
        "prompt": """你是迈克尔·伯里（"大空头"）。你是极端的逆向投资者，专门寻找市场定价严重错误的机会。
你擅长：深挖财报细节发现隐藏风险、识别资产泡沫、在别人贪婪时恐惧。
你关注：自由现金流与市值比（FCF Yield）、企业价值/EBITDA、隐含的做空理由。
你的风格是"先找出可能爆雷的理由"，如果找不到，才考虑买入。
你对高估值极度警惕，对财务造假嗅觉灵敏。

基于以下数据，以伯里的视角分析这只股票（注意：重点找出风险和问题）：
{data}

严格按此JSON格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数, "reasoning": "不超过80字的分析理由，必须体现伯里的怀疑论风格"}}""",
    },
    {
        "id": "duan",
        "name": "段永平",
        "name_cn": "段永平",
        "icon": "🀄",
        "weight": 0.20,
        "style": "本分投资哲学",
        "prompt": """你是段永平。你的核心哲学是"本分"——做对的事情，把事情做对。
你关注：商业模式是否简单可持续、企业文化是否"本分"、是否在自己的能力圈内。
你的 Stop Doing List：不碰看不懂的、不碰短期投机、不碰管理层不靠谱的。
你喜欢：消费品牌（强复购）、平台型公司、有定价权的公司。
你的名言："买股票就是买公司，买公司就是买其未来现金流的折现。"

基于以下数据，以段永平的视角分析这只股票：
{data}

严格按此JSON格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数, "reasoning": "不超过80字的分析理由，必须体现段永平的本分哲学"}}""",
    },
]


def _build_data_context(result, fundamentals: dict, normalized: dict,
                        moat: dict, dcf: dict) -> str:
    """构建传给每位大师的数据摘要"""
    fund = result.buffett_result
    tech = result.tech_signal

    def _f(val, pct=False):
        if val is None:
            return "N/A"
        if pct:
            return "{:.1f}%".format(val)
        return str(val)

    lines = [
        "股票: {} ({})".format(result.symbol, result.name),
        "当前价: {}  涨跌: {}%".format(result.price, "{:.2f}".format(result.change_pct) if result.change_pct else "N/A"),
        "",
        "## 关键指标",
        "PE: {}  PB: {}  ROE: {}".format(
            _f(normalized.get("pe_trailing")),
            _f(normalized.get("pb")),
            _f(normalized.get("roe"), True)),
        "毛利率: {}  净利率: {}  负债权益比: {}".format(
            _f(normalized.get("gross_margin"), True),
            _f(normalized.get("profit_margin"), True),
            _f(normalized.get("debt_to_equity"))),
        "流动比率: {}  自由现金流: {}".format(
            _f(normalized.get("current_ratio")),
            _f(fundamentals.get("free_cashflow"))),
        "营收增长: {}  利润增长: {}".format(
            _f(normalized.get("revenue_growth"), True),
            _f(normalized.get("earnings_growth"), True)),
        "",
        "## 护城河评分",
        "总分: {}/100 (等级: {})".format(
            moat.get("percentage", 0), moat.get("grade", "N/A")),
        "巴菲特评级: {} ({}%)".format(
            fund.get("grade", "N/A"), fund.get("percentage", 0)),
        "",
        "## 技术面",
        "趋势: {}  动量: {}  RSI: {}".format(
            tech.get("trend", "N/A"),
            tech.get("momentum", "N/A"),
            _f(tech.get("rsi"))),
    ]

    # DCF 估值
    if dcf and dcf.get("method") != "insufficient":
        lines.extend([
            "",
            "## DCF 估值",
            "方法: {}  内在价值: {}  安全边际: {}%".format(
                dcf.get("method", "N/A"),
                dcf.get("intrinsic_value", "N/A"),
                dcf.get("safety_margin_pct", "N/A")),
        ])

    return "\n".join(lines)


def _call_master(master: dict, data_context: str, provider: ApiProvider) -> dict:
    """调用单个大师Agent"""
    from src.ai.summarizer import _call_llm

    prompt = master["prompt"].format(data=data_context)
    try:
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=300)
        text = text.strip()
        # Strip DeepSeek R1 think tags
        think_match = re.search(r'</think>\s*(.*)', text, re.DOTALL)
        if think_match:
            text = think_match.group(1).strip()
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text).strip()
        result = json.loads(text)
        return {
            "id": master["id"],
            "name": master["name"],
            "name_cn": master["name_cn"],
            "icon": master["icon"],
            "weight": master["weight"],
            "style": master["style"],
            "signal": result.get("signal", "neutral"),
            "confidence": min(100, max(0, int(result.get("confidence", 50)))),
            "reasoning": result.get("reasoning", ""),
            "error": None,
        }
    except Exception as e:
        logger.warning("Committee member %s failed: %s", master["name"], e)
        return {
            "id": master["id"],
            "name": master["name"],
            "name_cn": master["name_cn"],
            "icon": master["icon"],
            "weight": master["weight"],
            "style": master["style"],
            "signal": "neutral",
            "confidence": 0,
            "reasoning": "分析失败: {}".format(str(e)[:40]),
            "error": str(e),
        }


def convene_committee(result, fundamentals: dict, normalized: dict,
                      moat: dict, dcf: dict,
                      provider: Optional[ApiProvider] = None) -> Optional[dict]:
    """召集投资委员会，5位大师并行分析

    Returns dict with:
        - members: list of individual master results
        - consensus: {signal, confidence, verdict}
        - bullish_count, bearish_count, neutral_count
        - weighted_score: -100 (极度看空) to +100 (极度看多)
    """
    if not provider or not provider.api_key:
        return None

    data_context = _build_data_context(result, fundamentals, normalized, moat, dcf)

    # 并行调用5位大师
    members = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_call_master, m, data_context, provider): m
            for m in MASTERS
        }
        for future in as_completed(futures):
            members.append(future.result())

    # 按 MASTERS 原始顺序排序
    id_order = {m["id"]: i for i, m in enumerate(MASTERS)}
    members.sort(key=lambda x: id_order.get(x["id"], 99))

    # 加权投票
    bullish_count = sum(1 for m in members if m["signal"] == "bullish")
    bearish_count = sum(1 for m in members if m["signal"] == "bearish")
    neutral_count = sum(1 for m in members if m["signal"] == "neutral")

    # 加权得分: bullish=+1, bearish=-1, neutral=0, 乘以 confidence 和 weight
    weighted_score = 0.0
    total_weight = 0.0
    for m in members:
        signal_val = {"bullish": 1, "bearish": -1, "neutral": 0}.get(m["signal"], 0)
        w = m["weight"] * (m["confidence"] / 100.0)
        weighted_score += signal_val * w
        total_weight += m["weight"]

    # 归一化到 -100 ~ +100
    if total_weight > 0:
        weighted_score = round(weighted_score / total_weight * 100, 1)
    else:
        weighted_score = 0

    # 综合置信度
    avg_confidence = round(sum(m["confidence"] for m in members) / len(members))

    # 共识判定
    if weighted_score >= 30:
        consensus_signal = "bullish"
        if weighted_score >= 60:
            verdict = "强烈看多"
        else:
            verdict = "看多"
    elif weighted_score <= -30:
        consensus_signal = "bearish"
        if weighted_score <= -60:
            verdict = "强烈看空"
        else:
            verdict = "看空"
    else:
        consensus_signal = "neutral"
        verdict = "分歧较大，建议观望"

    # 一致性评估
    if bullish_count >= 4 or bearish_count >= 4:
        unanimity = "高度一致"
    elif bullish_count >= 3 or bearish_count >= 3:
        unanimity = "多数一致"
    else:
        unanimity = "分歧明显"

    return {
        "members": members,
        "consensus": {
            "signal": consensus_signal,
            "confidence": avg_confidence,
            "verdict": verdict,
            "unanimity": unanimity,
        },
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "neutral_count": neutral_count,
        "weighted_score": weighted_score,
    }
