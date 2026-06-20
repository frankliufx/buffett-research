"""AI-powered stock screener using 10 hardcoded investment principles."""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from src.config import ApiProvider

_logger = logging.getLogger(__name__)

INVESTMENT_PRINCIPLES: List[str] = [
    "只投资自己能理解的业务模式，商业逻辑必须清晰简单",
    "关注护城河：品牌、网络效应、成本优势或转换成本至少具备其一",
    "ROE连续5年超过15%，说明资本配置效率高",
    "自由现金流为正且持续增长，现金是企业的血液",
    "管理层诚信、股东导向，回避利润注水或高管薪酬失控的公司",
    "合理估值：PE低于25或PEG低于1.5，不为增长支付过高溢价",
    "低杠杆：资产负债率D/E低于0.5，财务安全边际足够",
    "行业空间足够大，未来5~10年仍有结构性增长驱动力",
    "有定价权：毛利率超过30%，说明产品/服务具备稀缺性",
    "以5年以上长期视角持有，回避短周期炒作标的",
]

_SYSTEM_PROMPT = """你是一位严格遵循价值投资原则的基金经理。
你将根据以下10条投资原则对股票进行评估：

{principles}

请严格、客观地评分，不要因为公司知名度而高估。""".format(
    principles="\n".join(
        f"{i + 1}. {p}" for i, p in enumerate(INVESTMENT_PRINCIPLES)
    )
)

_USER_PROMPT_TEMPLATE = """请评估以下股票是否符合上述10条投资原则。

**股票**: {symbol} — {name}
**市场**: {market}

**基本财务数据**:
{data_str}

请返回 JSON（只返回JSON，不要其他内容）：
{{
  "score": <0-100的整数，越高越符合原则>,
  "category": "<强烈关注|持续观察|回避>",
  "rationale": "<简明中文理由，不超过80字>"
}}

评分参考：80-100强烈关注，50-79持续观察，0-49回避。"""

_FIELD_LABELS: Dict[str, str] = {
    "pe": "市盈率(PE)",
    "pb": "市净率(PB)",
    "roe": "ROE(%)",
    "gross_margin": "毛利率(%)",
    "debt_to_equity": "资产负债率(D/E)",
    "revenue_growth": "营收增速(%)",
    "fcf": "自由现金流(亿)",
    "market_cap": "市值(亿)",
}

_PERCENTAGE_FIELDS = {"roe", "gross_margin", "revenue_growth"}


def _parse_response(raw: str) -> Dict[str, Any]:
    """Extract JSON from AI response, with fallback defaults."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        data = json.loads(cleaned)
        score = int(data.get("score", 50))
        category = data.get("category", "持续观察")
        if category not in ("强烈关注", "持续观察", "回避"):
            category = "持续观察"
        return {
            "score": max(0, min(100, score)),
            "category": category,
            "rationale": str(data.get("rationale", "")),
        }
    except (json.JSONDecodeError, ValueError):
        return {"score": 50, "category": "持续观察", "rationale": "解析失败，数据不足"}


def _format_data(fundamentals: Dict[str, Any]) -> str:
    """Format fundamentals dict into a readable string for the prompt."""
    lines = []
    for key, label in _FIELD_LABELS.items():
        val = fundamentals.get(key)
        if val is None:
            continue
        if key in _PERCENTAGE_FIELDS:
            fval = float(val)
            formatted = f"{fval * 100:.1f}%" if abs(fval) < 1 else f"{fval:.1f}%"
        else:
            formatted = str(round(float(val), 2))
        lines.append(f"- {label}: {formatted}")
    return "\n".join(lines) if lines else "- 数据不足"


def evaluate_stock(
    symbol: str,
    name: str,
    fundamentals: Dict[str, Any],
    provider: ApiProvider,
) -> Dict[str, Any]:
    """Evaluate a single stock against the 10 investment principles."""
    import openai

    market = "A股" if symbol.startswith(("sh", "sz")) else "美股"
    user_msg = _USER_PROMPT_TEMPLATE.format(
        symbol=symbol,
        name=name,
        market=market,
        data_str=_format_data(fundamentals),
    )

    client = openai.OpenAI(api_key=provider.api_key, base_url=provider.base_url or None)
    try:
        resp = client.chat.completions.create(
            model=provider.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content or ""
    except Exception as exc:
        _logger.warning("AI call failed for %s: %s", symbol, exc)
        return {
            "symbol": symbol,
            "name": name,
            "score": 0,
            "category": "回避",
            "rationale": f"API调用失败: {str(exc)[:60]}",
        }

    parsed = _parse_response(raw)
    return {"symbol": symbol, "name": name, **parsed}


def batch_evaluate(
    stocks: List[tuple],
    fundamentals_map: Dict[str, Dict[str, Any]],
    provider: ApiProvider,
    max_workers: int = 5,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[Dict[str, Any]]:
    """Evaluate multiple stocks concurrently, return sorted by score descending."""
    total = len(stocks)
    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                evaluate_stock,
                sym,
                nm,
                fundamentals_map.get(sym, {}),
                provider,
            ): (sym, nm)
            for sym, nm in stocks
        }
        done = 0
        for future in as_completed(futures):
            results.append(future.result())
            done += 1
            if progress_callback:
                progress_callback(done, total)

    return sorted(results, key=lambda r: r["score"], reverse=True)
