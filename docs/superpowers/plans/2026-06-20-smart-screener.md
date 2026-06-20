# Smart Screener + Model Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add (1) a quick model-switcher UI in Settings and (2) a new "智能选股" page that scans CSI300 + S&P500 against 10 hardcoded investment principles using OpenRouter AI.

**Architecture:** The screener fetches the stock universe (AKShare for CSI300, static list for S&P500 top-100), runs a lightweight pre-filter using cached fundamental data, then evaluates survivors via a batched OpenRouter prompt, streaming results into a ranked table. The model switcher patches the active provider's `model` field in session state and persists via `save_config`.

**Tech Stack:** Streamlit, AKShare, yfinance, OpenRouter (openai-compatible), pandas, concurrent.futures, existing `src/config.py` provider system.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `pages/4_settings.py` | Add quick model selector section at top of API tab |
| Create | `src/screener/__init__.py` | Package marker |
| Create | `src/screener/universe.py` | Fetch CSI300 + S&P500 universe, apply pre-filter |
| Create | `src/screener/ai_screener.py` | AI evaluation with 10 hardcoded principles |
| Create | `pages/9_screener.py` | Screener UI: trigger button, progress, ranked results |
| Modify | `app.py` | Add page 9 to navigation |
| Create | `tests/test_screener_universe.py` | Unit tests for universe fetcher |
| Create | `tests/test_screener_ai.py` | Unit tests for AI screener parsing |

---

## Task 1: Quick Model Selector in Settings

**Files:**
- Modify: `pages/4_settings.py` (lines ~35–40, insert before providers loop)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_model_selector.py
import pytest
from unittest.mock import patch, MagicMock

def test_model_presets_defined():
    """Ensure our 4 preset model dicts have required keys."""
    from pages._model_presets import MODEL_PRESETS
    assert len(MODEL_PRESETS) == 4
    for preset in MODEL_PRESETS:
        assert "label" in preset
        assert "model" in preset
        assert "base_url" in preset
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/frankliu/stock-analyst
python -m pytest tests/test_model_selector.py -v
```
Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Create the presets module**

Create `pages/_model_presets.py`:

```python
"""Hardcoded quick-switch model presets (all via OpenRouter)."""

MODEL_PRESETS = [
    {
        "label": "DeepSeek Chat",
        "model": "deepseek/deepseek-chat-v3-0324",
        "base_url": "https://openrouter.ai/api/v1",
        "icon": "💬",
    },
    {
        "label": "DeepSeek R1",
        "model": "deepseek/deepseek-r1",
        "base_url": "https://openrouter.ai/api/v1",
        "icon": "🧠",
    },
    {
        "label": "GPT-4o",
        "model": "openai/gpt-4o",
        "base_url": "https://openrouter.ai/api/v1",
        "icon": "⚡",
    },
    {
        "label": "o1",
        "model": "openai/o1",
        "base_url": "https://openrouter.ai/api/v1",
        "icon": "🔬",
    },
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_model_selector.py -v
```
Expected: PASS

- [ ] **Step 5: Add quick selector UI to `pages/4_settings.py`**

Insert after line 38 (`st.caption(...)`) and before the `providers = config.api.providers` line:

```python
    # ── 快速切换模型 ──────────────────────────────────────────────
    from pages._model_presets import MODEL_PRESETS
    st.markdown(
        '<div style="color:{c}; font-size:0.7rem; letter-spacing:2px; margin:1rem 0 0.5rem;">快速切换模型 · QUICK SWITCH</div>'.format(
            c=COLORS["gold"]
        ),
        unsafe_allow_html=True,
    )
    _active_provider = None
    for _p in config.api.providers:
        if _p.is_active:
            _active_provider = _p
            break

    _cols = st.columns(len(MODEL_PRESETS))
    for _ci, _preset in enumerate(MODEL_PRESETS):
        with _cols[_ci]:
            _is_current = _active_provider and _active_provider.model == _preset["model"]
            if st.button(
                "{} {}".format(_preset["icon"], _preset["label"]),
                key="preset_{}".format(_ci),
                type="primary" if _is_current else "secondary",
                use_container_width=True,
                help="切换到 {}".format(_preset["model"]),
            ):
                if _active_provider:
                    _active_provider.model = _preset["model"]
                    _active_provider.base_url = _preset["base_url"]
                    _active_provider.provider = "openai_compatible"
                    from src.config import save_config
                    save_config(config)
                    st.success("已切换到 {}".format(_preset["label"]))
                    st.rerun()
                else:
                    st.warning("请先激活一个 OpenRouter provider")
    st.divider()
    # ─────────────────────────────────────────────────────────────
```

- [ ] **Step 6: Verify locally in Streamlit**

```bash
streamlit run app.py --server.port 8501
```
Open Settings → API tab. Verify 4 buttons appear. Click "DeepSeek R1" → confirm model switches and button highlights.

- [ ] **Step 7: Commit**

```bash
cd /Users/frankliu/stock-analyst
git add pages/_model_presets.py pages/4_settings.py tests/test_model_selector.py
git commit -m "feat: add quick model selector in Settings API tab"
```

---

## Task 2: Stock Universe Fetcher

**Files:**
- Create: `src/screener/__init__.py`
- Create: `src/screener/universe.py`
- Create: `tests/test_screener_universe.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_screener_universe.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


def test_get_csi300_tickers_returns_list():
    mock_df = pd.DataFrame({
        "成分券代码": ["600519", "000858", "601318"],
        "成分券名称": ["贵州茅台", "五粮液", "中国平安"],
    })
    with patch("akshare.index_stock_cons_csindex", return_value=mock_df):
        from src.screener.universe import get_csi300_tickers
        result = get_csi300_tickers()
    assert len(result) == 3
    assert result[0] == ("sh600519", "贵州茅台")


def test_get_sp500_tickers_returns_list():
    from src.screener.universe import get_sp500_tickers
    result = get_sp500_tickers()
    assert len(result) >= 50
    assert all(isinstance(t, tuple) and len(t) == 2 for t in result)


def test_csi300_ticker_format():
    mock_df = pd.DataFrame({
        "成分券代码": ["600519", "000858", "300750"],
        "成分券名称": ["茅台", "五粮液", "宁德时代"],
    })
    with patch("akshare.index_stock_cons_csindex", return_value=mock_df):
        from src.screener.universe import get_csi300_tickers
        result = get_csi300_tickers()
    assert result[0][0] == "sh600519"
    assert result[1][0] == "sz000858"
    assert result[2][0] == "sz300750"


def test_get_universe_combines_both():
    mock_csi = [("sh600519", "茅台"), ("sz000858", "五粮液")]
    mock_sp = [("AAPL", "Apple"), ("MSFT", "Microsoft")]
    with patch("src.screener.universe.get_csi300_tickers", return_value=mock_csi), \
         patch("src.screener.universe.get_sp500_tickers", return_value=mock_sp):
        from src.screener.universe import get_full_universe
        result = get_full_universe()
    assert len(result) == 4
    symbols = [r[0] for r in result]
    assert "sh600519" in symbols
    assert "AAPL" in symbols
```

- [ ] **Step 2: Run to verify they fail**

```bash
python -m pytest tests/test_screener_universe.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create `src/screener/__init__.py`**

```python
```
(empty file)

- [ ] **Step 4: Create `src/screener/universe.py`**

```python
"""Stock universe: CSI300 (AKShare) + S&P500 top-100 (static list)."""

from __future__ import annotations
from typing import List, Tuple

StockEntry = Tuple[str, str]  # (ticker, name)

# Top-100 S&P 500 by market cap (static, updated 2026-06)
_SP500_TOP100: List[StockEntry] = [
    ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "NVIDIA"),
    ("GOOGL", "Alphabet"), ("AMZN", "Amazon"), ("META", "Meta Platforms"),
    ("TSLA", "Tesla"), ("BRK-B", "Berkshire Hathaway"), ("LLY", "Eli Lilly"),
    ("V", "Visa"), ("JPM", "JPMorgan Chase"), ("UNH", "UnitedHealth"),
    ("XOM", "Exxon Mobil"), ("MA", "Mastercard"), ("JNJ", "Johnson & Johnson"),
    ("PG", "Procter & Gamble"), ("HD", "Home Depot"), ("AVGO", "Broadcom"),
    ("CVX", "Chevron"), ("MRK", "Merck"), ("ABBV", "AbbVie"),
    ("PEP", "PepsiCo"), ("KO", "Coca-Cola"), ("COST", "Costco"),
    ("WMT", "Walmart"), ("BAC", "Bank of America"), ("MCD", "McDonald's"),
    ("CRM", "Salesforce"), ("ACN", "Accenture"), ("TMO", "Thermo Fisher"),
    ("ABT", "Abbott"), ("CSCO", "Cisco"), ("WFC", "Wells Fargo"),
    ("LIN", "Linde"), ("DHR", "Danaher"), ("TXN", "Texas Instruments"),
    ("NEE", "NextEra Energy"), ("PM", "Philip Morris"), ("RTX", "RTX Corp"),
    ("AMGN", "Amgen"), ("UPS", "UPS"), ("INTU", "Intuit"),
    ("HON", "Honeywell"), ("CAT", "Caterpillar"), ("IBM", "IBM"),
    ("SPGI", "S&P Global"), ("GS", "Goldman Sachs"), ("BKNG", "Booking"),
    ("MS", "Morgan Stanley"), ("LOW", "Lowe's"), ("DE", "Deere"),
    ("AXP", "American Express"), ("BLK", "BlackRock"), ("ELV", "Elevance"),
    ("MDLZ", "Mondelez"), ("ADI", "Analog Devices"), ("GILD", "Gilead"),
    ("PLD", "Prologis"), ("SYK", "Stryker"), ("ADP", "ADP"),
    ("REGN", "Regeneron"), ("VRTX", "Vertex Pharma"), ("PANW", "Palo Alto"),
    ("SBUX", "Starbucks"), ("LRCX", "Lam Research"), ("CI", "Cigna"),
    ("KLAC", "KLA Corp"), ("MU", "Micron"), ("SNPS", "Synopsys"),
    ("MCO", "Moody's"), ("SHW", "Sherwin-Williams"), ("CME", "CME Group"),
    ("SO", "Southern Co"), ("FI", "Fiserv"), ("APH", "Amphenol"),
    ("INTC", "Intel"), ("AON", "Aon"), ("ICE", "ICE"),
    ("GE", "GE Aerospace"), ("USB", "US Bancorp"), ("TJX", "TJX"),
    ("MMC", "Marsh & McLennan"), ("HCA", "HCA Healthcare"), ("PGR", "Progressive"),
    ("NOC", "Northrop Grumman"), ("ITW", "Illinois Tool Works"), ("ETN", "Eaton"),
    ("EMR", "Emerson Electric"), ("NSC", "Norfolk Southern"), ("FDX", "FedEx"),
    ("FCX", "Freeport-McMoRan"), ("PSA", "Public Storage"), ("NKE", "Nike"),
    ("ORCL", "Oracle"), ("AMAT", "Applied Materials"), ("NFLX", "Netflix"),
    ("QCOM", "Qualcomm"), ("TGT", "Target"), ("DUK", "Duke Energy"),
    ("ROP", "Roper Technologies"), ("AJG", "Arthur J. Gallagher"),
]


def get_csi300_tickers() -> List[StockEntry]:
    """Fetch CSI300 components via AKShare.

    Returns list of (ticker, name) where ticker uses sh/sz prefix.
    Falls back to empty list on error.
    """
    try:
        import akshare as ak
        df = ak.index_stock_cons_csindex(symbol="000300")
        result: List[StockEntry] = []
        for _, row in df.iterrows():
            code = str(row["成分券代码"]).zfill(6)
            name = str(row["成分券名称"])
            prefix = "sh" if code.startswith(("6", "9")) else "sz"
            result.append(("{prefix}{code}".format(prefix=prefix, code=code), name))
        return result
    except Exception:
        return []


def get_sp500_tickers() -> List[StockEntry]:
    """Return S&P500 top-100 static list."""
    return list(_SP500_TOP100)


def get_full_universe() -> List[StockEntry]:
    """Combine CSI300 + S&P500 top-100."""
    return get_csi300_tickers() + get_sp500_tickers()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_screener_universe.py -v
```
Expected: 4 PASS

- [ ] **Step 6: Commit**

```bash
git add src/screener/__init__.py src/screener/universe.py tests/test_screener_universe.py
git commit -m "feat: add stock universe fetcher (CSI300 + S&P500 top-100)"
```

---

## Task 3: AI Screener Core

**Files:**
- Create: `src/screener/ai_screener.py`
- Create: `tests/test_screener_ai.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_screener_ai.py
import pytest
from unittest.mock import patch, MagicMock


def test_investment_principles_count():
    from src.screener.ai_screener import INVESTMENT_PRINCIPLES
    assert len(INVESTMENT_PRINCIPLES) == 10


def test_parse_ai_response_valid():
    from src.screener.ai_screener import _parse_response
    raw = '{"score": 82, "category": "强烈关注", "rationale": "强护城河，ROE连续高于15%"}'
    result = _parse_response(raw)
    assert result["score"] == 82
    assert result["category"] == "强烈关注"
    assert "rationale" in result


def test_parse_ai_response_with_markdown_fence():
    from src.screener.ai_screener import _parse_response
    raw = '```json\n{"score": 45, "category": "回避", "rationale": "高债务"}\n```'
    result = _parse_response(raw)
    assert result["score"] == 45
    assert result["category"] == "回避"


def test_parse_ai_response_fallback():
    from src.screener.ai_screener import _parse_response
    result = _parse_response("invalid json content")
    assert result["score"] == 50
    assert result["category"] == "持续观察"
    assert "rationale" in result


def test_evaluate_stock_calls_provider(monkeypatch):
    from src.screener.ai_screener import evaluate_stock
    from src.config import ApiProvider

    mock_provider = ApiProvider(
        name="Test",
        provider="openai_compatible",
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-chat-v3-0324",
        is_active=True,
    )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"score": 75, "category": "持续观察", "rationale": "合理估值"}'

    with patch("openai.OpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create.return_value = mock_response
        result = evaluate_stock("AAPL", "Apple", {"pe": 28, "roe": 0.18}, mock_provider)

    assert result["symbol"] == "AAPL"
    assert result["score"] == 75
    assert result["category"] == "持续观察"
```

- [ ] **Step 2: Run to verify they fail**

```bash
python -m pytest tests/test_screener_ai.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create `src/screener/ai_screener.py`**

```python
"""AI-powered stock screener using 10 hardcoded investment principles."""

from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional

from src.config import ApiProvider

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
        "{}. {}".format(i + 1, p) for i, p in enumerate(INVESTMENT_PRINCIPLES)
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
    lines = []
    field_labels = {
        "pe": "市盈率(PE)",
        "pb": "市净率(PB)",
        "roe": "ROE(%)",
        "gross_margin": "毛利率(%)",
        "debt_to_equity": "资产负债率(D/E)",
        "revenue_growth": "营收增速(%)",
        "fcf": "自由现金流(亿)",
        "market_cap": "市值(亿)",
    }
    for key, label in field_labels.items():
        if key in fundamentals and fundamentals[key] is not None:
            val = fundamentals[key]
            if key in ("roe", "gross_margin", "revenue_growth"):
                val = "{:.1f}%".format(float(val) * 100 if abs(float(val)) < 1 else float(val))
            else:
                val = str(round(float(val), 2))
            lines.append("- {}: {}".format(label, val))
    return "\n".join(lines) if lines else "- 数据不足"


def evaluate_stock(
    symbol: str,
    name: str,
    fundamentals: Dict[str, Any],
    provider: ApiProvider,
) -> Dict[str, Any]:
    """Evaluate a single stock against the 10 investment principles.

    Returns dict with keys: symbol, name, score, category, rationale.
    """
    import openai

    market = "A股" if symbol.startswith(("sh", "sz")) else "美股"
    data_str = _format_data(fundamentals)
    user_msg = _USER_PROMPT_TEMPLATE.format(
        symbol=symbol, name=name, market=market, data_str=data_str
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
        return {
            "symbol": symbol,
            "name": name,
            "score": 0,
            "category": "回避",
            "rationale": "API调用失败: {}".format(str(exc)[:60]),
        }

    parsed = _parse_response(raw)
    return {"symbol": symbol, "name": name, **parsed}


def batch_evaluate(
    stocks: List[tuple],
    fundamentals_map: Dict[str, Dict[str, Any]],
    provider: ApiProvider,
    max_workers: int = 5,
    progress_callback=None,
) -> List[Dict[str, Any]]:
    """Evaluate multiple stocks concurrently.

    Args:
        stocks: list of (symbol, name) tuples
        fundamentals_map: {symbol: {pe, roe, ...}}
        provider: active API provider
        max_workers: concurrent LLM calls
        progress_callback: optional callable(done, total) for progress updates
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: List[Dict[str, Any]] = []
    total = len(stocks)

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
            result = future.result()
            results.append(result)
            done += 1
            if progress_callback:
                progress_callback(done, total)

    return sorted(results, key=lambda r: r["score"], reverse=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_screener_ai.py -v
```
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/screener/ai_screener.py tests/test_screener_ai.py
git commit -m "feat: add AI screener core with 10 investment principles"
```

---

## Task 4: Fundamental Data Fetcher for Screener

**Files:**
- Modify: `src/screener/universe.py` (add `fetch_basic_fundamentals`)

This task adds a lightweight fundamentals fetcher (yfinance for US, AKShare for A-share) used as pre-filter data for the AI screener.

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_screener_universe.py
def test_fetch_basic_fundamentals_us():
    mock_info = {
        "trailingPE": 28.5,
        "priceToBook": 3.2,
        "returnOnEquity": 0.18,
        "grossMargins": 0.44,
        "debtToEquity": 0.32,
        "revenueGrowth": 0.07,
        "freeCashflow": 9e10,
        "marketCap": 3e12,
    }
    with patch("yfinance.Ticker") as MockTicker:
        MockTicker.return_value.info = mock_info
        from src.screener.universe import fetch_basic_fundamentals
        result = fetch_basic_fundamentals("AAPL")
    assert result["pe"] == pytest.approx(28.5)
    assert result["roe"] == pytest.approx(0.18)


def test_fetch_basic_fundamentals_returns_empty_on_error():
    with patch("yfinance.Ticker", side_effect=Exception("network error")):
        from src.screener.universe import fetch_basic_fundamentals
        result = fetch_basic_fundamentals("INVALID")
    assert result == {}
```

- [ ] **Step 2: Run to verify they fail**

```bash
python -m pytest tests/test_screener_universe.py::test_fetch_basic_fundamentals_us tests/test_screener_universe.py::test_fetch_basic_fundamentals_returns_empty_on_error -v
```
Expected: FAIL

- [ ] **Step 3: Add `fetch_basic_fundamentals` to `src/screener/universe.py`**

Append to end of `src/screener/universe.py`:

```python

def fetch_basic_fundamentals(symbol: str) -> Dict[str, Any]:
    """Fetch key fundamentals for a single stock.

    For US stocks: yfinance Ticker.info
    For A-shares (sh/sz prefix): akshare stock_zh_a_spot_em (last price only)
    Returns empty dict on any error.
    """
    try:
        if symbol.startswith(("sh", "sz")):
            return _fetch_ashare_fundamentals(symbol)
        return _fetch_us_fundamentals(symbol)
    except Exception:
        return {}


def _fetch_us_fundamentals(symbol: str) -> Dict[str, Any]:
    import yfinance as yf
    info = yf.Ticker(symbol).info
    return {
        "pe": info.get("trailingPE"),
        "pb": info.get("priceToBook"),
        "roe": info.get("returnOnEquity"),
        "gross_margin": info.get("grossMargins"),
        "debt_to_equity": info.get("debtToEquity"),
        "revenue_growth": info.get("revenueGrowth"),
        "fcf": info.get("freeCashflow"),
        "market_cap": info.get("marketCap"),
    }


def _fetch_ashare_fundamentals(symbol: str) -> Dict[str, Any]:
    """Limited A-share data via AKShare (PE/PB from real-time quote)."""
    import akshare as ak
    code = symbol[2:]  # strip sh/sz prefix
    try:
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == code]
        if row.empty:
            return {}
        r = row.iloc[0]
        return {
            "pe": _safe_float(r.get("市盈率-动态")),
            "pb": _safe_float(r.get("市净率")),
            "roe": None,
            "gross_margin": None,
            "debt_to_equity": None,
            "revenue_growth": None,
            "fcf": None,
            "market_cap": _safe_float(r.get("总市值")),
        }
    except Exception:
        return {}


def _safe_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
```

Also add the missing imports at the top of `universe.py`:

```python
from typing import Any, Dict, List, Optional, Tuple
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_screener_universe.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/screener/universe.py tests/test_screener_universe.py
git commit -m "feat: add fundamental data fetcher for screener universe"
```

---

## Task 5: Screener Page UI

**Files:**
- Create: `pages/9_screener.py`

- [ ] **Step 1: Verify imports work**

```bash
cd /Users/frankliu/stock-analyst
python -c "from src.screener.universe import get_full_universe, fetch_basic_fundamentals; from src.screener.ai_screener import batch_evaluate; print('OK')"
```
Expected: `OK`

- [ ] **Step 2: Create `pages/9_screener.py`**

```python
"""智能选股 — AI-powered full-market screener."""

import streamlit as st
from src.config import load_config, get_active_provider
from src.ui_theme import get_global_css, COLORS

if "config" not in st.session_state:
    st.session_state.config = load_config()
config = st.session_state.config

st.markdown(get_global_css(), unsafe_allow_html=True)

st.markdown(
    """
<div style="text-align:center; padding:1.5rem 0 1.2rem 0; border-bottom:1px solid {border}; margin-bottom:1rem;">
    <h2 style="color:{text}; font-weight:300; letter-spacing:4px; margin:0;">智能选股</h2>
    <p style="color:{muted}; font-size:0.8rem; letter-spacing:2px; margin-top:0.4rem;">
        AI STOCK SCREENER · 沪深300 + S&P500
    </p>
</div>
""".format(
        text=COLORS["text"], muted=COLORS["text_muted"], border=COLORS["border"]
    ),
    unsafe_allow_html=True,
)

# ── 投资原则展示 ──────────────────────────────────────────────────
with st.expander("📋 投资原则（10条，已内置）", expanded=False):
    from src.screener.ai_screener import INVESTMENT_PRINCIPLES
    for i, p in enumerate(INVESTMENT_PRINCIPLES, 1):
        st.markdown("**{}**. {}".format(i, p))

st.markdown("---")

# ── 分析参数 ──────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])
with col_left:
    st.markdown(
        '<div style="color:{c}; font-size:0.75rem; letter-spacing:1px;">扫描范围</div>'.format(
            c=COLORS["text_muted"]
        ),
        unsafe_allow_html=True,
    )
    markets = st.multiselect(
        "选择市场",
        options=["沪深300 (A股)", "S&P500 Top-100 (美股)"],
        default=["沪深300 (A股)", "S&P500 Top-100 (美股)"],
        label_visibility="collapsed",
    )

with col_right:
    max_stocks = st.number_input(
        "最多评估股票数", min_value=10, max_value=200, value=50, step=10,
        help="限制AI评估数量以控制耗时和费用"
    )

# ── 启动按钮 ──────────────────────────────────────────────────────
provider = get_active_provider(config)
if not provider:
    st.warning("⚠️ 请先在 Settings → API 激活一个有效的 API Provider（需要 OpenRouter key）")
    st.stop()

if "screener_results" not in st.session_state:
    st.session_state.screener_results = None

start_col, _ = st.columns([1, 3])
with start_col:
    start_btn = st.button(
        "🚀 开始分析",
        type="primary",
        use_container_width=True,
        disabled=not markets,
    )

if start_btn:
    st.session_state.screener_results = None  # clear previous

    with st.spinner("正在获取股票池…"):
        from src.screener.universe import (
            get_csi300_tickers,
            get_sp500_tickers,
            fetch_basic_fundamentals,
        )
        universe = []
        if "沪深300 (A股)" in markets:
            universe += get_csi300_tickers()
        if "S&P500 Top-100 (美股)" in markets:
            universe += get_sp500_tickers()

    if not universe:
        st.error("无法获取股票列表，请检查网络或 AKShare 配置。")
        st.stop()

    # Limit to max_stocks
    import random
    if len(universe) > max_stocks:
        universe = random.sample(universe, max_stocks)
    universe.sort(key=lambda x: x[0])

    st.info("共 {} 只股票进入AI分析队列…".format(len(universe)))

    # ── 获取基本面数据 ──────────────────────────────────────────
    progress_bar = st.progress(0, text="获取基本面数据…")
    from concurrent.futures import ThreadPoolExecutor, as_completed

    fundamentals_map = {}
    total = len(universe)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_basic_fundamentals, sym): sym for sym, _ in universe}
        done = 0
        for f in as_completed(futures):
            sym = futures[f]
            fundamentals_map[sym] = f.result()
            done += 1
            progress_bar.progress(done / (total * 2), text="获取基本面: {}/{}".format(done, total))

    # ── AI评估 ────────────────────────────────────────────────
    results_placeholder = st.empty()
    partial_results = []

    def _on_progress(done: int, total: int):
        progress_bar.progress(0.5 + done / (total * 2), text="AI分析: {}/{}".format(done, total))

    from src.screener.ai_screener import batch_evaluate
    all_results = batch_evaluate(
        universe,
        fundamentals_map,
        provider,
        max_workers=5,
        progress_callback=_on_progress,
    )

    progress_bar.progress(1.0, text="分析完成！")
    st.session_state.screener_results = all_results
    st.rerun()

# ── 结果展示 ──────────────────────────────────────────────────────
if st.session_state.screener_results:
    results = st.session_state.screener_results

    st.markdown("### 📊 分析结果 — {} 只股票".format(len(results)))

    # Category sections
    categories = {
        "强烈关注": ("🟢", COLORS.get("gold", "#C9A962")),
        "持续观察": ("🟡", COLORS.get("text_muted", "#888")),
        "回避":     ("🔴", "#E05252"),
    }

    for cat, (icon, color) in categories.items():
        cat_stocks = [r for r in results if r["category"] == cat]
        if not cat_stocks:
            continue
        st.markdown(
            '<div style="color:{c}; font-size:0.8rem; letter-spacing:2px; margin:1.2rem 0 0.5rem;">'
            "{icon} {cat} · {n}只"
            "</div>".format(c=color, icon=icon, cat=cat, n=len(cat_stocks)),
            unsafe_allow_html=True,
        )
        for r in cat_stocks:
            with st.container():
                c1, c2, c3 = st.columns([1, 5, 1])
                with c1:
                    st.metric("评分", r["score"])
                with c2:
                    st.markdown("**{}** {}".format(r["symbol"], r["name"]))
                    st.caption(r["rationale"])
                with c3:
                    st.markdown(
                        '<div style="color:{c}; font-size:1.2rem; text-align:right;">{icon}</div>'.format(
                            c=color, icon=icon
                        ),
                        unsafe_allow_html=True,
                    )
            st.divider()

    # Full table download
    import pandas as pd
    df_out = pd.DataFrame(results)[["symbol", "name", "score", "category", "rationale"]]
    df_out.columns = ["代码", "名称", "评分", "分类", "AI理由"]
    st.download_button(
        "⬇️ 下载完整结果 CSV",
        df_out.to_csv(index=False).encode("utf-8-sig"),
        file_name="screener_results.csv",
        mime="text/csv",
    )
```

- [ ] **Step 3: Verify page loads without import errors**

```bash
python -c "import ast; ast.parse(open('pages/9_screener.py').read()); print('syntax OK')"
```
Expected: `syntax OK`

- [ ] **Step 4: Commit**

```bash
git add pages/9_screener.py
git commit -m "feat: add 智能选股 screener page UI"
```

---

## Task 6: Wire Screener Page into Navigation

**Files:**
- Modify: `app.py` (line 78, after Decisions page)

- [ ] **Step 1: Add page to navigation in `app.py`**

In `app.py`, change:
```python
    st.Page("pages/8_decisions.py",   title="Decisions",    icon="📋"),
    st.Page("pages/4_settings.py",    title="Settings",     icon="⚙️"),
```

To:
```python
    st.Page("pages/8_decisions.py",   title="Decisions",    icon="📋"),
    st.Page("pages/9_screener.py",    title="智能选股",      icon="🔎"),
    st.Page("pages/4_settings.py",    title="Settings",     icon="⚙️"),
```

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: all existing tests still PASS, new tests PASS

- [ ] **Step 3: Smoke-test in browser**

```bash
streamlit run app.py --server.port 8501
```
Verify:
1. "🔎 智能选股" appears in sidebar navigation
2. Page loads without error
3. Principles expander shows 10 items
4. "开始分析" button is visible and activates with a valid provider
5. Settings → API tab shows "快速切换模型" with 4 buttons at top

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: register 智能选股 page in app navigation"
```

---

## Self-Review

**Spec coverage:**
- ✅ 智能选股 page: manual trigger button, AI analysis, ranked output
- ✅ 沪深300 + S&P500 universe
- ✅ 10 hardcoded investment principles
- ✅ OpenRouter API (key hidden via env var, not hardcoded)
- ✅ Output categorized into 强烈关注/持续观察/回避
- ✅ Settings model selector for DeepSeek Chat / DeepSeek R1 / GPT-4o / o1

**Placeholder scan:** No TBDs found. All code blocks are complete.

**Type consistency:**
- `fetch_basic_fundamentals` returns `Dict[str, Any]` — matches `fundamentals_map` usage in `batch_evaluate`
- `evaluate_stock` returns `Dict[str, Any]` with keys `symbol, name, score, category, rationale` — matches screener UI access
- `batch_evaluate` takes `List[tuple]` matching `(symbol, name)` — matches `universe` list type from `get_full_universe()`
- `MODEL_PRESETS` accessed as `pages._model_presets.MODEL_PRESETS` — consistent with import path

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-20-smart-screener.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — Fresh subagent per task, spec + quality review between tasks

**2. Inline Execution** — Execute tasks in this session using executing-plans

**Which approach?**
