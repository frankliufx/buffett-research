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

from src.config import ApiProvider, load_config

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
你讨厌高负债、频繁并购、看不懂的生意。
格言："用合理的价格买入优秀的公司，远胜于用便宜的价格买入平庸的公司。"

请按四步分析以下数据：
1. 关键证据：护城河最强的 1 个数字证据（引用具体指标和数值）
2. 最大顾虑：你最不接受这只股票的 1 个理由
3. 估值判断：现价是否在合理安全边际内（结合 PE/PB/ROE）
4. 结论：给出 signal 和 confidence

{data}

严格按此 JSON 格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数,
  "key_evidence": "最关键的1个数字证据（20字以内，如：ROE=28%连续10年>20%）",
  "main_concern": "最大顾虑（20字以内）",
  "reasoning": "综合判断（不超过120字，必须引用具体数字，体现巴菲特风格）"}}""",
    },
    {
        "id": "munger",
        "name": "Charlie Munger",
        "name_cn": "芒格",
        "icon": "🧠",
        "weight": 0.20,
        "style": "逆向思维大师",
        "prompt": """你是查理·芒格。你用逆向思维和多学科框架分析企业，关注 ROIC 超越 WACC 的持续性、
管理层能力圈、第一性原理、以及避免愚蠢比追求聪明更重要。
你的检查清单：先问"这家公司会怎么倒闭？"，再问"为什么不会倒闭？"。
格言："反过来想，总是反过来想。"

请按四步分析：
1. 清单检验：这家公司最可能失败的 1 个方式（引用数据）
2. 核心优势：ROIC 是否持续超越 WACC（若无数据，用 ROE 代替）
3. 管理层判断：资本配置是否合理（FCF 用途？并购？回购？）
4. 结论：signal 和 confidence

{data}

严格按此 JSON 格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数,
  "key_evidence": "ROIC/ROE 与行业对比的关键数字（20字以内）",
  "main_concern": "最大顾虑（20字以内）",
  "reasoning": "综合判断（不超过120字，必须引用数字，体现芒格逆向思维）"}}""",
    },
    {
        "id": "lynch",
        "name": "Peter Lynch",
        "name_cn": "彼得·林奇",
        "icon": "📈",
        "weight": 0.20,
        "style": "十倍股猎手",
        "prompt": """你是彼得·林奇。你关注 PEG 比率（PE/成长率）、看得懂的生意、十倍股潜力、
以及"买你了解的公司"。你相信普通投资者在某些领域比机构更有优势。
你讨厌分析师广泛覆盖的公司，喜欢被忽视的成长故事。
格言："买入之前，你必须能用小学生都懂的语言解释为什么要买这只股票。"

请按四步分析：
1. 关键证据（成长质量）：PEG 是否 <1（PE ÷ 利润增长率），成长是否可持续
2. 生意可理解性：你能用一句话解释这家公司的商业模式吗？
3. 机构关注度：是否被分析师忽视（可能存在信息差）
4. 结论：signal 和 confidence

{data}

严格按此 JSON 格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数,
  "key_evidence": "PEG 或成长率的关键数字（20字以内）",
  "main_concern": "最大顾虑（20字以内）",
  "reasoning": "综合判断（不超过120字，必须引用数字，体现林奇成长投资视角）"}}""",
    },
    {
        "id": "burry",
        "name": "Michael Burry",
        "name_cn": "迈克尔·伯里",
        "icon": "🔍",
        "weight": 0.15,
        "style": "逆向深度价值",
        "prompt": """你是迈克尔·伯里。你用反向思维发现被市场错误定价的机会，深度研究财务报表，
关注 FCF Yield（自由现金流收益率）、资产价值被低估、以及市场共识错误的地方。
你不惧怕逆市场共识，但每个判断都必须有扎实的数据支撑。
格言："找到市场共识错误的地方，然后站在对面。"

请按四步分析：
1. 关键证据（FCF 分析）：FCF Yield 是否有吸引力（FCF / 市值，>5% 为有吸引力）
2. 市场共识：当前市场对这只股票最可能犯什么错误（过于乐观或悲观）
3. 资产价值：PB 是否反映了真实资产价值，是否存在低估
4. 结论：signal 和 confidence

{data}

严格按此 JSON 格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数,
  "key_evidence": "FCF Yield 或 PB 的关键数字（20字以内）",
  "main_concern": "最大顾虑（20字以内）",
  "reasoning": "综合判断（不超过120字，必须引用数字，体现伯里逆向分析视角）"}}""",
    },
    {
        "id": "duan",
        "name": "段永平",
        "name_cn": "段永平",
        "icon": "🀄",
        "weight": 0.20,
        "style": "本分投资哲学",
        "prompt": """你是段永平。你关注企业文化、本分经营、Stop Doing List（不该做的事不做）、
以及长期持有优秀企业。你相信"买股票就是买公司"，不关注短期波动，只关注企业长期价值。
你的核心问题："这家公司的管理层是否本分？产品是否真正为用户创造价值？"
格言："做对的事情，把事情做对。"

请按四步分析：
1. 关键证据（企业文化）：管理层是否有长期主义迹象（R&D 投入？员工满意度？股东回报历史？）
2. 本分经营：核心业务是否专注，是否有乱投资迹象（跨界并购？债务激进？）
3. 用户价值：产品/服务是否真正创造了用户价值（毛利率高否？复购率？护城河？）
4. 结论：signal 和 confidence

{data}

严格按此 JSON 格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数,
  "key_evidence": "反映企业文化或本分经营的关键数字（20字以内）",
  "main_concern": "最大顾虑（20字以内）",
  "reasoning": "综合判断（不超过120字，必须引用数字，体现段永平长期主义视角）"}}""",
    },
]

# Alias for tests and internal use
_masters = MASTERS


def _build_data_context(result, moat_or_fundamentals: dict = None,
                        normalized: dict = None, moat: dict = None,
                        dcf: dict = None) -> str:
    """构建传给每位大师的数据摘要。

    支持两种调用方式：
    1. 旧版（5参数）: _build_data_context(result_obj, fundamentals, normalized, moat, dcf)
    2. 新版（2参数）: _build_data_context(result_dict, moat)  — result 为扁平 dict
    """
    def _f(val, pct=False):
        if val is None:
            return "N/A"
        if pct:
            return "{:.1f}%".format(val * 100 if isinstance(val, float) and val < 1.1 and pct else val)
        return str(val)

    # 判断调用方式
    if isinstance(result, dict):
        # 新版：result 为扁平 dict，moat_or_fundamentals 即 moat
        flat = result
        effective_moat = moat_or_fundamentals or {}

        def _fv(val, pct=False):
            if val is None:
                return "N/A"
            if pct and isinstance(val, float) and abs(val) <= 10:
                return "{:.1f}%".format(val * 100)
            if pct:
                return "{:.1f}%".format(val)
            return str(val)

        lines = [
            "股票: {} ({})".format(flat.get("symbol", "N/A"), flat.get("name", "N/A")),
            "当前价: {}  涨跌: {}%".format(
                flat.get("price", "N/A"),
                "{:.2f}".format(flat["change_pct"]) if flat.get("change_pct") else "N/A"),
            "",
            "## 关键指标",
            "PE: {}  PB: {}  ROE: {}".format(
                _fv(flat.get("pe_trailing")),
                _fv(flat.get("pb")),
                _fv(flat.get("roe"), True)),
            "毛利率: {}  净利率: {}  负债权益比: {}".format(
                _fv(flat.get("gross_margin"), True),
                _fv(flat.get("profit_margin"), True),
                _fv(flat.get("debt_to_equity"))),
            "流动比率: {}  自由现金流: {}".format(
                _fv(flat.get("current_ratio")),
                _fv(flat.get("free_cashflow"))),
            "营收增长: {}  利润增长: {}".format(
                _fv(flat.get("revenue_growth"), True),
                _fv(flat.get("earnings_growth"), True)),
            "",
            "## 护城河评分",
            "总分: {}/100 (等级: {})".format(
                effective_moat.get("total_score", effective_moat.get("percentage", 0)),
                effective_moat.get("grade", "N/A")),
        ]
    else:
        # 旧版：result 为对象，参数按原始顺序
        fundamentals = moat_or_fundamentals or {}
        effective_normalized = normalized or {}
        effective_moat = moat or {}
        effective_dcf = dcf

        fund = result.buffett_result
        tech = result.tech_signal

        lines = [
            "股票: {} ({})".format(result.symbol, result.name),
            "当前价: {}  涨跌: {}%".format(
                result.price,
                "{:.2f}".format(result.change_pct) if result.change_pct else "N/A"),
            "",
            "## 关键指标",
            "PE: {}  PB: {}  ROE: {}".format(
                _f(effective_normalized.get("pe_trailing")),
                _f(effective_normalized.get("pb")),
                _f(effective_normalized.get("roe"), True)),
            "毛利率: {}  净利率: {}  负债权益比: {}".format(
                _f(effective_normalized.get("gross_margin"), True),
                _f(effective_normalized.get("profit_margin"), True),
                _f(effective_normalized.get("debt_to_equity"))),
            "流动比率: {}  自由现金流: {}".format(
                _f(effective_normalized.get("current_ratio")),
                _f(fundamentals.get("free_cashflow"))),
            "营收增长: {}  利润增长: {}".format(
                _f(effective_normalized.get("revenue_growth"), True),
                _f(effective_normalized.get("earnings_growth"), True)),
            "",
            "## 护城河评分",
            "总分: {}/100 (等级: {})".format(
                effective_moat.get("percentage", 0), effective_moat.get("grade", "N/A")),
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
        if effective_dcf and effective_dcf.get("method") != "insufficient":
            lines.extend([
                "",
                "## DCF 估值",
                "方法: {}  内在价值: {}  安全边际: {}%".format(
                    effective_dcf.get("method", "N/A"),
                    effective_dcf.get("intrinsic_value", "N/A"),
                    effective_dcf.get("safety_margin_pct", "N/A")),
            ])

        flat = {}  # 旧版 result 为对象，无 _warnings/_data_quality 属性

    # ── 数据质量警告注入 ─────────────────────────────────────────
    warnings = flat.get("_warnings", []) if isinstance(result, dict) else []
    data_quality = flat.get("_data_quality", {}) if isinstance(result, dict) else {}
    uncertain_fields = [k for k, v in data_quality.items() if v == "uncertain"]

    if uncertain_fields or warnings:
        lines.append("")
        lines.append("## ⚠️ 数据质量提示")
        if uncertain_fields:
            lines.append(f"以下字段存在数据源差异，请降低该字段权重：{', '.join(uncertain_fields)}")
        for w in warnings[:3]:  # 最多显示 3 条警告
            lines.append(f"- {w}")
    # ── /数据质量警告 ─────────────────────────────────────────────

    return "\n".join(lines)


def _parse_master_result(text: str) -> dict:
    """解析大师 LLM 输出 JSON，兼容新旧字段格式。"""
    # 剥离 DeepSeek R1 think 标签
    think_match = re.search(r"</think>\s*(.*)", text, re.DOTALL)
    if think_match:
        text = think_match.group(1).strip()
    # 剥离 markdown code fence
    text = re.sub(r"^```\w*\n?", "", text)
    text = re.sub(r"\n?```$", "", text).strip()

    result = json.loads(text)
    # 确保必须字段存在
    if "signal" not in result:
        result["signal"] = "neutral"
    if "confidence" not in result:
        result["confidence"] = 50
    if "reasoning" not in result:
        result["reasoning"] = ""
    # 新字段默认空字符串（向后兼容）
    result.setdefault("key_evidence", "")
    result.setdefault("main_concern", "")
    return result


def _call_master(master: dict, data_context: str, provider: ApiProvider) -> dict:
    """调用单个大师Agent"""
    from src.ai.summarizer import _call_llm

    prompt = master["prompt"].format(data=data_context)
    try:
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=300)
        text = text.strip()
        result = _parse_master_result(text)
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
            "key_evidence": result.get("key_evidence", ""),
            "main_concern": result.get("main_concern", ""),
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
    workers = load_config().parallel.committee_workers
    with ThreadPoolExecutor(max_workers=workers) as executor:
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
