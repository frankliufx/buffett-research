# AI Analysis Depth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将委员会大师分析从 80 字平铺提升为引用数据的结构化四步推理，深度研报增加 Critic-Refine 自我批判机制，并把 CrossValidator 数据质量信息注入提示词。

**Architecture:** 三层改进，互不依赖：(1) 提示词层 — committee/hedge_fund 大师 prompt 加入 CoT 四步结构，BUFFETT_ANALYSIS_PROMPT 标准化输出格式；(2) 流程层 — summarizer.analyze_stock() 增加 critic→refine 两轮调用；(3) 数据层 — _build_data_context() 读取 `_data_quality` 和 `_warnings` 字段注入数据可信度说明。所有公共 API 签名保持不变，页面零回归。

**Tech Stack:** Python 3.9, anthropic/openai SDK（已有），现有 `_call_llm()` 统一调用中枢

---

## 文件结构

```
修改:
  src/ai/prompts.py               — 新增 CRITIC_PROMPT；更新 BUFFETT_ANALYSIS_PROMPT
  src/ai/committee.py             — 升级 5 位大师 prompt（CoT）；_build_data_context 注入质量
  src/ai/hedge_fund_agents.py     — 升级 9 组 13 位分析师 prompt（CoT）
  src/ai/summarizer.py            — analyze_stock() 加 Critic-Refine 双轮

新建:
  tests/test_ai_depth.py          — prompt 渲染测试 + Critic-Refine mock 测试
```

---

## Task 1: 新增 CRITIC_PROMPT + 标准化 BUFFETT_ANALYSIS_PROMPT

**Files:**
- Modify: `~/stock-analyst/src/ai/prompts.py`
- Create: `~/stock-analyst/tests/test_ai_depth.py`

- [ ] **Step 1: 新建 tests/test_ai_depth.py（先写失败测试）**

```python
"""测试 AI 分析深度升级：prompt 结构 + Critic-Refine 机制"""
from __future__ import annotations
import pytest
from src.ai.prompts import CRITIC_PROMPT, BUFFETT_ANALYSIS_PROMPT


def test_critic_prompt_exists():
    assert CRITIC_PROMPT is not None
    assert len(CRITIC_PROMPT) > 100


def test_critic_prompt_has_required_placeholders():
    """CRITIC_PROMPT 必须包含 {report} 和 {data} 占位符"""
    assert "{report}" in CRITIC_PROMPT
    assert "{data}" in CRITIC_PROMPT


def test_critic_prompt_renders_without_error():
    rendered = CRITIC_PROMPT.format(
        report="这是一份测试研报内容",
        data="ROE: 25%, PE: 20, 净利润增长: 15%",
    )
    assert "测试研报内容" in rendered
    assert "ROE: 25%" in rendered


def test_buffett_prompt_has_executive_summary_section():
    assert "执行摘要" in BUFFETT_ANALYSIS_PROMPT


def test_buffett_prompt_has_core_arguments_section():
    assert "核心论点" in BUFFETT_ANALYSIS_PROMPT


def test_buffett_prompt_has_risk_section():
    assert "主要风险" in BUFFETT_ANALYSIS_PROMPT


def test_buffett_prompt_has_valuation_section():
    assert "估值区间" in BUFFETT_ANALYSIS_PROMPT
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -m pytest tests/test_ai_depth.py -v 2>&1 | head -20
```

预期：`ImportError: cannot import name 'CRITIC_PROMPT'`

- [ ] **Step 3: 在 prompts.py 末尾追加 CRITIC_PROMPT**

在 `~/stock-analyst/src/ai/prompts.py` 末尾追加：

```python

# ── Critic-Refine 提示词 ─────────────────────────────────────────────────────
CRITIC_PROMPT = """你是一位严格的做空分析师，专门找出多头研报中的漏洞。

以下是对该股票的初步研报：
---
{report}
---

该股票的关键财务数据：
{data}

你的任务：
1. 找出研报中最薄弱的 2-3 个论点（哪里缺乏数据支撑？哪里过于乐观？）
2. 指出研报遗漏的最重要风险（估值风险、行业风险、财务风险中选最严重的）
3. 如果你是做空方，你会用什么论据反驳这份研报？

输出格式（纯文本，不要 JSON）：
## 薄弱论点
- [论点1]：[具体问题]
- [论点2]：[具体问题]

## 遗漏风险
[最重要的遗漏风险，30字以内，必须量化]

## 做空论据
[做空方最强的反驳，50字以内]
"""
```

- [ ] **Step 4: 更新 BUFFETT_ANALYSIS_PROMPT 格式**

找到 `prompts.py` 中的 `BUFFETT_ANALYSIS_PROMPT`（约第 97-168 行），将现有模板**完整替换**为以下版本（保留变量名 `BUFFETT_ANALYSIS_PROMPT`，只改字符串内容）：

```python
BUFFETT_ANALYSIS_PROMPT = """你是一位融合了巴菲特和段永平投资智慧的资深价值投资分析师。
请基于以下数据，生成一份机构级深度研报。

## 股票数据
{data_section}

## 护城河评分
{moat_section}

## 估值数据
{valuation_section}

## 技术面信号
{technical_section}

{history_section}
{peer_section}
{data_quality_warning}

---

请严格按以下格式输出深度研报：

## 执行摘要
[三句话：第一句给出结论（买入/增持/持有/减持/回避 + 置信度），第二句说明核心逻辑，第三句说明最大风险]

## 核心论点

**论点一：[标题]**
[论据：必须引用具体数字，如 ROE=28% 高于行业均值 15%，连续 8 年维持在 25%+]
[意义：这个数字对投资决策的实际影响]

**论点二：[标题]**
[论据：引用具体数字]
[意义：投资意义]

**论点三：[标题]**
[论据：引用具体数字]
[意义：投资意义]

## 主要风险

**风险一：[风险名称]**（影响：高/中/低）
[量化描述：如"若利率上升 100bp，DCF 估值下降约 15%"]

**风险二：[风险名称]**（影响：高/中/低）
[量化描述]

**风险三：[风险名称]**（影响：高/中/低）
[量化描述]

## 估值区间

| 情景 | 假设条件 | 目标价 |
|------|---------|--------|
| 熊市 | [核心假设] | ¥/$ [价格] |
| 基准 | [核心假设] | ¥/$ [价格] |
| 牛市 | [核心假设] | ¥/$ [价格] |

## 投资建议
**操作方向**：[买入/增持/持有/减持/回避]
**建议仓位**：[X%]
**参考买入区间**：[价格区间]
**止损参考**：[触发条件]
**持有周期**：[时间范围]

---
注意：数据标注 N/A 的字段禁止推断；所有论点必须有数字支撑。
"""
```

- [ ] **Step 5: 运行测试，确认全部通过**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -m pytest tests/test_ai_depth.py -v
```

预期：`7 passed`

- [ ] **Step 6: Commit**

```bash
cd ~/stock-analyst
git add src/ai/prompts.py tests/test_ai_depth.py
git commit -m "feat: add CRITIC_PROMPT and standardize BUFFETT_ANALYSIS_PROMPT format"
```

---

## Task 2: Committee 大师 Prompt 升级（CoT）+ 数据质量注入

**Files:**
- Modify: `~/stock-analyst/src/ai/committee.py`
- Modify: `~/stock-analyst/tests/test_ai_depth.py`

**背景**：committee.py 中 `_masters` 列表定义了 5 位大师，每个有 `prompt` 字段。当前 reasoning 限制 80 字，新版升级为四步结构化分析，JSON 增加两个可选字段 `key_evidence` 和 `main_concern`（向后兼容，老代码会忽略新字段）。

- [ ] **Step 1: 追加 committee 测试到 tests/test_ai_depth.py**

在 `tests/test_ai_depth.py` 末尾追加：

```python
from unittest.mock import patch, MagicMock
import json


def test_committee_master_prompts_contain_cot_steps():
    """每位大师的 prompt 必须包含四步推理结构"""
    from src.ai.committee import _masters
    for master in _masters:
        prompt = master["prompt"]
        assert "核心优势" in prompt or "核心论点" in prompt or "关键证据" in prompt, \
            f"{master['name']} prompt 缺少 CoT 结构"
        assert "key_evidence" in prompt, \
            f"{master['name']} prompt 缺少 key_evidence 字段"
        assert "main_concern" in prompt, \
            f"{master['name']} prompt 缺少 main_concern 字段"


def test_committee_data_context_includes_quality_warning():
    """当数据有 _warnings 时，_build_data_context 应在输出中包含质量提示"""
    from src.ai.committee import _build_data_context

    result_with_warnings = {
        "symbol": "AAPL",
        "name": "Apple",
        "price": 150.0,
        "change_pct": 1.5,
        "pe_trailing": 28.0,
        "pb": 42.0,
        "roe": 0.97,
        "profit_margin": 0.25,
        "gross_margin": 0.46,
        "operating_margin": 0.31,
        "revenue_growth": 0.04,
        "earnings_growth": 0.08,
        "debt_to_equity": 121.0,
        "current_ratio": 1.05,
        "free_cashflow": 110e9,
        "market_cap": 3200e9,
        "_warnings": ["roe: ⚠️ 数据源差异 15.3%（yfinance=0.97, sec_edgar=0.82）"],
        "_data_quality": {"roe": "uncertain"},
    }
    moat = {"total_score": 92, "grade": "A"}

    context = _build_data_context(result_with_warnings, moat)
    assert "⚠️" in context or "数据质量" in context or "uncertain" in context.lower(), \
        "数据质量警告未注入 data context"


def test_committee_json_parser_handles_new_fields():
    """committee 结果解析器应正确处理新增的 key_evidence / main_concern 字段"""
    from src.ai.committee import _parse_master_result

    raw_json = json.dumps({
        "signal": "bullish",
        "confidence": 85,
        "key_evidence": "ROE=28%，持续 10 年高于 20%",
        "main_concern": "估值偏高 PE=35x",
        "reasoning": "护城河坚实，现价有一定安全边际，但需警惕估值压缩",
    })
    result = _parse_master_result(raw_json)
    assert result["signal"] == "bullish"
    assert result["confidence"] == 85
    assert result["key_evidence"] == "ROE=28%，持续 10 年高于 20%"
    assert result["main_concern"] == "估值偏高 PE=35x"
```

- [ ] **Step 2: 运行新测试，确认失败**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -m pytest tests/test_ai_depth.py -v -k "committee" 2>&1 | head -20
```

预期：`ImportError` 或 `AssertionError`（prompt 中没有 CoT 结构）

- [ ] **Step 3: 在 committee.py 中新增 `_parse_master_result()` 函数**

在 committee.py 中，在 `_call_master()` 函数之前，新增：

```python
def _parse_master_result(text: str) -> dict:
    """解析大师 LLM 输出 JSON，兼容新旧字段格式。
    
    新格式增加 key_evidence 和 main_concern 字段（可选，老代码忽略即可）。
    """
    import re
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
```

- [ ] **Step 4: 更新 committee.py 中的 `_masters` 列表（5 位大师 prompt 升级）**

找到 `_masters` 列表定义，**逐一替换每位大师的 `prompt` 字段**：

**巴菲特（buffett）：**
```python
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
```

**芒格（munger）：**
```python
"prompt": """你是查理·芒格。你用逆向思维和多学科框架分析企业，关注 ROIC 超越 WACC 的持续性、
管理层能力圈、第一性原理、以及避免愚蠢比追求聪明更重要。
你的检查清单：先问"这家公司会怎么倒闭？"，再问"为什么不会倒闭？"。
格言："反过来想，总是反过来想。"

请按四步分析：
1. 清单检验：这家公司最可能失败的 1 个方式（引用数据）
2. 竞争优势：ROIC 是否持续超越 WACC（若无数据，用 ROE 代替）
3. 管理层判断：资本配置是否合理（FCF 用途？并购？回购？）
4. 结论：signal 和 confidence

{data}

严格按此 JSON 格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数,
  "key_evidence": "ROIC/ROE 与行业对比的关键数字（20字以内）",
  "main_concern": "最大顾虑（20字以内）",
  "reasoning": "综合判断（不超过120字，必须引用数字，体现芒格逆向思维）"}}""",
```

**彼得·林奇（lynch）：**
```python
"prompt": """你是彼得·林奇。你关注 PEG 比率（PE/成长率）、看得懂的生意、十倍股潜力、
以及"买你了解的公司"。你相信普通投资者在某些领域比机构更有优势。
你讨厌分析师广泛覆盖的公司，喜欢被忽视的成长故事。
格言："买入之前，你必须能用小学生都懂的语言解释为什么要买这只股票。"

请按四步分析：
1. 成长质量：PEG 是否 <1（PE ÷ 利润增长率），成长是否可持续
2. 生意可理解性：你能用一句话解释这家公司的商业模式吗？
3. 机构关注度：是否被分析师忽视（可能存在信息差）
4. 结论：signal 和 confidence

{data}

严格按此 JSON 格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数,
  "key_evidence": "PEG 或成长率的关键数字（20字以内）",
  "main_concern": "最大顾虑（20字以内）",
  "reasoning": "综合判断（不超过120字，必须引用数字，体现林奇成长投资视角）"}}""",
```

**迈克尔·伯里（burry）：**
```python
"prompt": """你是迈克尔·伯里。你用反向思维发现被市场错误定价的机会，深度研究财务报表，
关注 FCF Yield（自由现金流收益率）、资产价值被低估、以及市场共识错误的地方。
你不惧怕逆市场共识，但每个判断都必须有扎实的数据支撑。
格言："找到市场共识错误的地方，然后站在对面。"

请按四步分析：
1. FCF 分析：FCF Yield 是否有吸引力（FCF / 市值，>5% 为有吸引力）
2. 市场共识：当前市场对这只股票最可能犯什么错误（过于乐观或悲观）
3. 资产价值：PB 是否反映了真实资产价值，是否存在低估
4. 结论：signal 和 confidence

{data}

严格按此 JSON 格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数,
  "key_evidence": "FCF Yield 或 PB 的关键数字（20字以内）",
  "main_concern": "最大顾虑（20字以内）",
  "reasoning": "综合判断（不超过120字，必须引用数字，体现伯里逆向分析视角）"}}""",
```

**段永平（duan）：**
```python
"prompt": """你是段永平。你关注企业文化、本分经营、Stop Doing List（不该做的事不做）、
以及长期持有优秀企业。你相信"买股票就是买公司"，不关注短期波动，只关注企业长期价值。
你的核心问题："这家公司的管理层是否本分？产品是否真正为用户创造价值？"
格言："做对的事情，把事情做对。"

请按四步分析：
1. 企业文化：管理层是否有长期主义迹象（R&D 投入？员工满意度？股东回报历史？）
2. 本分经营：核心业务是否专注，是否有乱投资迹象（跨界并购？债务激进？）
3. 用户价值：产品/服务是否真正创造了用户价值（毛利率高否？复购率？护城河？）
4. 结论：signal 和 confidence

{data}

严格按此 JSON 格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数,
  "key_evidence": "反映企业文化或本分经营的关键数字（20字以内）",
  "main_concern": "最大顾虑（20字以内）",
  "reasoning": "综合判断（不超过120字，必须引用数字，体现段永平长期主义视角）"}}""",
```

- [ ] **Step 5: 更新 `_build_data_context()` 注入数据质量警告**

找到 committee.py 中的 `_build_data_context()` 函数（约 L124-181），在函数返回语句之前追加：

```python
    # ── 数据质量警告注入 ─────────────────────────────────────────
    warnings = result.get("_warnings", [])
    data_quality = result.get("_data_quality", {})
    uncertain_fields = [k for k, v in data_quality.items() if v == "uncertain"]
    
    if uncertain_fields or warnings:
        lines.append("")
        lines.append("## ⚠️ 数据质量提示")
        if uncertain_fields:
            lines.append(f"以下字段存在数据源差异，请降低该字段权重：{', '.join(uncertain_fields)}")
        for w in warnings[:3]:  # 最多显示 3 条警告
            lines.append(f"- {w}")
    # ── /数据质量警告 ─────────────────────────────────────────────
```

（将此代码块插入到 `return "\n".join(lines)` 之前）

- [ ] **Step 6: 更新 `_call_master()` 使用 `_parse_master_result()`**

找到 `_call_master()` 函数中的 JSON 解析部分，将现有的解析逻辑替换为：

```python
    result = _parse_master_result(text)
```

（替换掉原来的 `think_match` 处理 + `re.sub` + `json.loads` 代码块）

- [ ] **Step 7: 运行 committee 相关测试**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -m pytest tests/test_ai_depth.py -v -k "committee"
```

预期：`3 passed`

- [ ] **Step 8: 验证 committee 模块可正常导入**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -c "
from src.ai.committee import _masters, _build_data_context, _parse_master_result
print('大师数量:', len(_masters))
print('第一位大师:', _masters[0]['name'])
print('key_evidence 字段存在于 prompt:', 'key_evidence' in _masters[0]['prompt'])
print('✅ committee 模块正常')
"
```

- [ ] **Step 9: Commit**

```bash
cd ~/stock-analyst
git add src/ai/committee.py tests/test_ai_depth.py
git commit -m "feat: upgrade committee master prompts with CoT structure and data quality injection"
```

---

## Task 3: 深度研报 Critic-Refine 机制

**Files:**
- Modify: `~/stock-analyst/src/ai/summarizer.py`
- Modify: `~/stock-analyst/tests/test_ai_depth.py`

**背景**：`analyze_stock()` 是生成深度研报的函数（第 296-362 行）。当前是单次 LLM 调用。新增流程：初稿 → Critic（找漏洞）→ Refine（修正版）。通过 `use_critic=True` 参数控制，默认开启。

- [ ] **Step 1: 追加 Critic-Refine 测试**

在 `tests/test_ai_depth.py` 末尾追加：

```python
def test_critic_refine_calls_llm_three_times():
    """Critic-Refine 流程应调用 LLM 3 次：初稿 + critic + refine"""
    from src.ai.summarizer import analyze_stock

    call_count = [0]
    call_args = []

    def mock_call_llm(provider, messages, max_tokens=2000, timeout=60.0):
        call_count[0] += 1
        call_args.append(messages)
        if call_count[0] == 1:
            return "# 初稿研报\n## 执行摘要\n看多，置信度高。"
        elif call_count[0] == 2:
            return "## 薄弱论点\n- 估值数据缺失\n\n## 遗漏风险\n利率风险\n\n## 做空论据\nPE 偏高"
        else:
            return "# 修订版研报\n## 执行摘要\n看多，但需注意估值风险。"

    mock_provider = MagicMock()
    mock_provider.provider = "anthropic"

    mock_result = {
        "symbol": "AAPL", "name": "Apple", "price": 150.0, "change_pct": 1.5,
        "pe_trailing": 28.0, "pb": 42.0, "roe": 0.97, "profit_margin": 0.25,
        "gross_margin": 0.46, "operating_margin": 0.31, "revenue_growth": 0.04,
        "earnings_growth": 0.08, "debt_to_equity": 121.0, "current_ratio": 1.05,
        "free_cashflow": 110e9, "market_cap": 3200e9,
    }
    mock_moat = {"total_score": 92, "grade": "A", "profitability_score": 28,
                  "profitability_max": 30, "moat_score": 22, "moat_max": 25,
                  "fortress_score": 18, "fortress_max": 20, "growth_score": 13,
                  "growth_max": 15, "opportunity_score": 8, "opportunity_max": 10}
    mock_valuation = {"intrinsic_value": 160.0, "safety_margin_pct": 6.7}

    with patch("src.ai.summarizer._call_llm", side_effect=mock_call_llm):
        report = analyze_stock(
            mock_result, mock_moat, mock_valuation,
            provider=mock_provider,
            use_critic=True,
        )

    assert call_count[0] == 3, f"期望 3 次 LLM 调用，实际 {call_count[0]} 次"
    assert "修订版研报" in report or "执行摘要" in report


def test_critic_refine_skipped_when_disabled():
    """use_critic=False 时只调用 LLM 1 次"""
    from src.ai.summarizer import analyze_stock

    call_count = [0]

    def mock_call_llm(provider, messages, max_tokens=2000, timeout=60.0):
        call_count[0] += 1
        return "# 研报内容"

    mock_provider = MagicMock()
    mock_result = {
        "symbol": "AAPL", "name": "Apple", "price": 150.0, "change_pct": 1.5,
        "pe_trailing": 28.0, "pb": None, "roe": 0.97, "profit_margin": 0.25,
        "gross_margin": 0.46, "operating_margin": None, "revenue_growth": None,
        "earnings_growth": None, "debt_to_equity": None, "current_ratio": None,
        "free_cashflow": None, "market_cap": None,
    }
    mock_moat = {"total_score": 70, "grade": "B", "profitability_score": 20,
                  "profitability_max": 30, "moat_score": 18, "moat_max": 25,
                  "fortress_score": 14, "fortress_max": 20, "growth_score": 10,
                  "growth_max": 15, "opportunity_score": 8, "opportunity_max": 10}

    with patch("src.ai.summarizer._call_llm", side_effect=mock_call_llm):
        report = analyze_stock(
            mock_result, mock_moat, {},
            provider=mock_provider,
            use_critic=False,
        )

    assert call_count[0] == 1, f"期望 1 次 LLM 调用，实际 {call_count[0]} 次"
```

- [ ] **Step 2: 运行新测试，确认失败**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -m pytest tests/test_ai_depth.py -v -k "critic_refine" 2>&1 | head -20
```

预期：`TypeError: analyze_stock() got an unexpected keyword argument 'use_critic'`

- [ ] **Step 3: 修改 summarizer.py 的 `analyze_stock()` 函数签名**

找到 `analyze_stock()` 函数定义（约第 296 行），将签名改为：

```python
def analyze_stock(
    result: dict,
    moat: dict,
    valuation: dict | None = None,
    history_context: str = "",
    peer_context: str = "",
    provider=None,
    use_critic: bool = True,
) -> str:
```

- [ ] **Step 4: 在 analyze_stock() 中添加 Critic-Refine 逻辑**

找到 `analyze_stock()` 函数内生成初稿的 `_call_llm()` 调用，在它之后（`return report` 之前）插入：

```python
    # ── Critic-Refine 机制 ───────────────────────────────────────
    if use_critic and report and len(report) > 200:
        try:
            from src.ai.prompts import CRITIC_PROMPT

            # Step 1: Critic — 找出薄弱论点
            data_summary = prompt[:800]  # 取 prompt 前 800 字作为数据摘要
            critic_messages = [{"role": "user", "content": CRITIC_PROMPT.format(
                report=report,
                data=data_summary,
            )}]
            critic_feedback = _call_llm(
                provider, critic_messages, max_tokens=600, timeout=45.0
            )

            if critic_feedback and len(critic_feedback) > 50:
                # Step 2: Refine — 综合 critic 意见修订研报
                refine_messages = [{"role": "user", "content": (
                    f"以下是一份投资研报的初稿：\n\n{report}\n\n"
                    f"做空分析师提出了以下批评：\n\n{critic_feedback}\n\n"
                    "请基于上述批评，修订这份研报：\n"
                    "1. 针对批评中指出的薄弱论点，补充数据或修正措辞\n"
                    "2. 将遗漏的重要风险加入'主要风险'部分\n"
                    "3. 保持原有结构不变（执行摘要、核心论点、主要风险、估值区间、投资建议）\n"
                    "4. 在'主要风险'末尾追加一行：**空头视角**：[做空方最强论据，30字以内]\n"
                    "直接输出修订后的完整研报，不要输出任何解释。"
                )}]
                refined_report = _call_llm(
                    provider, refine_messages, max_tokens=2500, timeout=90.0
                )
                if refined_report and len(refined_report) > 200:
                    report = refined_report
        except Exception as e:
            logger.debug("Critic-Refine failed, using original report: %s", e)
    # ── /Critic-Refine ────────────────────────────────────────────

    return report
```

- [ ] **Step 5: 在 summarizer.py 顶部确认 logger 已定义**

```bash
grep -n "^logger" ~/stock-analyst/src/ai/summarizer.py | head -3
```

如果没有，在 summarizer.py 文件顶部 import 块后追加：

```python
logger = logging.getLogger(__name__)
```

- [ ] **Step 6: 运行 Critic-Refine 测试**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -m pytest tests/test_ai_depth.py -v -k "critic_refine"
```

预期：`2 passed`

- [ ] **Step 7: 验证 summarizer 模块可正常导入**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -c "
import inspect
from src.ai.summarizer import analyze_stock
sig = inspect.signature(analyze_stock)
print('参数:', list(sig.parameters.keys()))
assert 'use_critic' in sig.parameters, 'use_critic 参数未添加'
print('✅ Critic-Refine 接口正常')
"
```

- [ ] **Step 8: Commit**

```bash
cd ~/stock-analyst
git add src/ai/summarizer.py tests/test_ai_depth.py
git commit -m "feat: add Critic-Refine mechanism to analyze_stock() deep report"
```

---

## Task 4: Hedge Fund 分析师 Prompt 升级（CoT）

**Files:**
- Modify: `~/stock-analyst/src/ai/hedge_fund_agents.py`
- Modify: `~/stock-analyst/tests/test_ai_depth.py`

**背景**：hedge_fund_agents.py 定义 9 组 13 位分析师，每人有独立 prompt，当前 reasoning 限制 100 字。升级为 CoT 四步结构，同样增加 `key_evidence` 和 `main_concern` 字段。

- [ ] **Step 1: 追加 hedge fund 测试**

在 `tests/test_ai_depth.py` 末尾追加：

```python
def test_hedge_fund_analyst_prompts_contain_cot():
    """所有对冲基金分析师 prompt 必须包含 CoT 结构"""
    from src.ai.hedge_fund_agents import ANALYSTS
    for analyst in ANALYSTS:
        prompt = analyst["prompt"]
        assert "key_evidence" in prompt, \
            f"{analyst['name']} prompt 缺少 key_evidence 字段"
        assert "main_concern" in prompt, \
            f"{analyst['name']} prompt 缺少 main_concern 字段"
        assert "120字" in prompt or "150字" in prompt, \
            f"{analyst['name']} prompt 未指定 reasoning 长度限制"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -m pytest tests/test_ai_depth.py -v -k "hedge_fund" 2>&1 | head -10
```

- [ ] **Step 3: 更新 hedge_fund_agents.py 中每位分析师的 prompt**

在 `hedge_fund_agents.py` 中找到 `ANALYSTS` 列表（或等价的分析师定义列表），对每位分析师的 `prompt` 字段增加 CoT 结构。

**通用模式**（在每个 analyst prompt 的现有角色描述之后，替换 JSON 输出格式部分）：

将每个 prompt 末尾的旧 JSON 格式：
```
严格按JSON输出，不附加任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0-100整数, 
  "reasoning": "不超过100字，体现...风格"}}
```

替换为新 JSON 格式（以 Buffett 为例，其余分析师依此类推）：
```
请按四步分析：
1. 关键证据：你的核心论点最强的 1 个数字支撑
2. 最大顾虑：用你的框架看，这只股票最大的问题
3. 量化估值：估值是否合理（引用 PE/PB/FCF Yield 等具体数字）
4. 结论：signal 和 confidence

严格按此 JSON 格式输出，不输出任何其他内容：
{{"signal": "bullish或bearish或neutral", "confidence": 0到100的整数,
  "key_evidence": "最关键数字证据（20字以内）",
  "main_concern": "最大顾虑（20字以内）",
  "reasoning": "综合判断（不超过120字，必须引用数字）"}}
```

**对 Damodaran**（估值教授）的 reasoning 限制可放宽到 150 字：
```
  "reasoning": "综合判断（不超过150字，必须包含具体 WACC 或 DCF 数字）"
```

**对 Taleb**（黑天鹅理论）的四步改为：
```
请按四步分析：
1. 脆弱性检验：最可能触发尾部风险的 1 个因素（量化）
2. 反脆弱性：公司能否从波动中获益（具体机制）
3. 杠铃策略：这只股票在组合中是"安全底仓"还是"高风险押注"？
4. 结论：signal 和 confidence
```

- [ ] **Step 4: 运行 hedge fund 测试**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -m pytest tests/test_ai_depth.py -v -k "hedge_fund"
```

预期：`1 passed`

- [ ] **Step 5: 验证模块导入正常**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -c "
from src.ai.hedge_fund_agents import ANALYSTS
print('分析师数量:', len(ANALYSTS))
analyst = ANALYSTS[0]
print('第一位:', analyst['name'])
print('含 CoT:', 'key_evidence' in analyst['prompt'])
print('✅ hedge_fund_agents 正常')
"
```

- [ ] **Step 6: Commit**

```bash
cd ~/stock-analyst
git add src/ai/hedge_fund_agents.py tests/test_ai_depth.py
git commit -m "feat: upgrade hedge fund analyst prompts with CoT structure"
```

---

## Task 5: 全链路验证

**Files:**
- Modify: `~/stock-analyst/tests/test_ai_depth.py`

- [ ] **Step 1: 运行全部 AI depth 测试**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -m pytest tests/test_ai_depth.py -v
```

预期：≥ 13 个测试全部通过。

- [ ] **Step 2: 运行全部测试确认无回归**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -m pytest tests/ -v 2>&1 | tail -20
```

预期：所有之前通过的测试仍然通过，无新增失败。

- [ ] **Step 3: 验证 AI 模块关键接口**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -c "
# 验证所有 AI 模块可正常导入，接口无变化
from src.ai.committee import analyze_with_committee
from src.ai.summarizer import analyze_stock, get_ai_brief, get_ai_insights
from src.ai.hedge_fund_runner import run_hedge_fund
from src.ai.prompts import BUFFETT_ANALYSIS_PROMPT, CRITIC_PROMPT

# 验证 BUFFETT_ANALYSIS_PROMPT 有新的必需章节
assert '执行摘要' in BUFFETT_ANALYSIS_PROMPT
assert '核心论点' in BUFFETT_ANALYSIS_PROMPT
assert '主要风险' in BUFFETT_ANALYSIS_PROMPT
assert '估值区间' in BUFFETT_ANALYSIS_PROMPT

# 验证 CRITIC_PROMPT
assert '{report}' in CRITIC_PROMPT
assert '{data}' in CRITIC_PROMPT

# 验证 analyze_stock 新参数
import inspect
sig = inspect.signature(analyze_stock)
assert 'use_critic' in sig.parameters

print('✅ 所有 AI 模块接口验证通过')
print('BUFFETT_ANALYSIS_PROMPT 长度:', len(BUFFETT_ANALYSIS_PROMPT), '字符')
print('CRITIC_PROMPT 长度:', len(CRITIC_PROMPT), '字符')
"
```

- [ ] **Step 4: 检查 committee 大师 prompt 关键字**

```bash
cd ~/stock-analyst && source .venv/bin/activate
python -c "
from src.ai.committee import _masters
print('=== Committee 大师 CoT 验证 ===')
for m in _masters:
    has_cot = 'key_evidence' in m['prompt'] and 'main_concern' in m['prompt']
    print(f'{m[\"name_cn\"]}: CoT={has_cot}')
print()
print('✅ 所有大师 prompt 已升级')
"
```

- [ ] **Step 5: 最终 commit（如有遗漏文件）**

```bash
cd ~/stock-analyst
git status
# 如有未提交文件：
git add -A
git commit -m "feat: complete AI analysis depth upgrade — CoT + Critic-Refine + standardized format"
```

---

## 成功标准核查

- [ ] `CRITIC_PROMPT` 存在于 prompts.py，含 `{report}` 和 `{data}` 占位符
- [ ] `BUFFETT_ANALYSIS_PROMPT` 包含：执行摘要、核心论点、主要风险、估值区间四个章节
- [ ] Committee 5 位大师 prompt 均含 `key_evidence` 和 `main_concern` 字段
- [ ] `_parse_master_result()` 函数存在，兼容新旧 JSON 格式
- [ ] `_build_data_context()` 注入数据质量警告
- [ ] `analyze_stock()` 支持 `use_critic` 参数，True 时触发 3 次 LLM 调用
- [ ] Hedge Fund 全部分析师 prompt 含 CoT 结构
- [ ] 所有现有测试无回归
- [ ] ≥ 13 个 test_ai_depth.py 测试通过
