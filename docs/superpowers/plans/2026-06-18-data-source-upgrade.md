# Data Source Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 接入 Tushare Pro（A股）和 SEC EDGAR（美股）作为权威数据源，新增 CrossValidator 多源校验层，保持 `fetch_fundamentals / fetch_quote / fetch_history` 公共接口不变，分析页零回归。

**Architecture:** 适配器模式 — `src/data/adapters/` 目录存放各数据源适配器，统一实现 `BaseAdapter` 接口。CrossValidator 接收多个适配器的同一指标，差异 >5% 时标注 ⚠️。`financial.py` 和 `price.py` 内部切换到适配器，对外签名不变。

**Tech Stack:** Python 3.12, tushare, requests (SEC EDGAR REST API), 现有 yfinance/akshare

---

## 文件结构

```
新建:
  src/data/adapters/__init__.py
  src/data/adapters/base.py
  src/data/adapters/tushare_adapter.py
  src/data/adapters/sec_edgar_adapter.py
  src/data/cross_validator.py
  tests/test_adapters.py
  tests/test_cross_validator.py

修改:
  src/data/financial.py   — A股路径接入 Tushare，US路径接入 SEC EDGAR
  src/data/price.py       — A股历史行情接入 Tushare
  requirements.txt        — 添加 tushare
  .env.example            — 添加 TUSHARE_TOKEN
```

---

## Task 1: 依赖与配置

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: 添加 tushare 到 requirements.txt**

在 `requirements.txt` 末尾追加：

```
tushare>=1.2.89
```

- [ ] **Step 2: 添加环境变量模板**

在 `.env.example` 中添加（如果文件不存在则新建）：

```bash
# Tushare Pro token — 免费注册获取：https://tushare.pro/register
TUSHARE_TOKEN=your_tushare_token_here
```

- [ ] **Step 3: 安装依赖**

```bash
cd ~/stock-analyst
source .venv/bin/activate
pip install "tushare>=1.2.89"
```

预期输出包含：`Successfully installed tushare-1.2.x`

- [ ] **Step 4: 验证安装**

```bash
python -c "import tushare; print(tushare.__version__)"
```

预期：打印版本号，无报错。

- [ ] **Step 5: Commit**

```bash
cd ~/stock-analyst
git add requirements.txt .env.example
git commit -m "chore: add tushare dependency and env template"
```

---

## Task 2: 适配器基类

**Files:**
- Create: `src/data/adapters/__init__.py`
- Create: `src/data/adapters/base.py`
- Create: `tests/test_adapters.py`

- [ ] **Step 1: 写失败测试**

新建 `tests/test_adapters.py`：

```python
"""测试 BaseAdapter 接口约定"""
import pytest
from src.data.adapters.base import BaseAdapter


class ConcreteAdapter(BaseAdapter):
    """最小合规实现，用于测试接口约定"""

    def is_available(self) -> bool:
        return True

    def get_a_share_financials(self, symbol: str) -> dict | None:
        return {"roe": 0.15, "pe_trailing": 12.0, "_source": "test"}

    def get_us_financials(self, symbol: str) -> dict | None:
        return {"roe": 0.20, "pe_trailing": 25.0, "_source": "test"}

    def get_a_share_history(self, symbol: str, days: int = 250):
        import pandas as pd
        return pd.DataFrame({"date": [], "close": [], "volume": []})


def test_concrete_adapter_satisfies_interface():
    adapter = ConcreteAdapter()
    assert adapter.is_available() is True


def test_get_a_share_financials_returns_dict():
    adapter = ConcreteAdapter()
    result = adapter.get_a_share_financials("600519")
    assert isinstance(result, dict)
    assert "roe" in result
    assert "_source" in result


def test_get_us_financials_returns_dict():
    adapter = ConcreteAdapter()
    result = adapter.get_us_financials("AAPL")
    assert isinstance(result, dict)
    assert "roe" in result


def test_abstract_methods_enforced():
    """不实现抽象方法时应报 TypeError"""
    with pytest.raises(TypeError):
        BaseAdapter()  # type: ignore
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd ~/stock-analyst
source .venv/bin/activate
python -m pytest tests/test_adapters.py -v 2>&1 | head -30
```

预期：`ModuleNotFoundError: No module named 'src.data.adapters'`

- [ ] **Step 3: 创建 `src/data/adapters/__init__.py`**

```python
from .base import BaseAdapter
from .tushare_adapter import TushareAdapter
from .sec_edgar_adapter import SecEdgarAdapter

__all__ = ["BaseAdapter", "TushareAdapter", "SecEdgarAdapter"]
```

（此时 TushareAdapter / SecEdgarAdapter 尚未实现，先留空占位——在 Task 3/4 中填充）

暂时改为：

```python
from .base import BaseAdapter

__all__ = ["BaseAdapter"]
```

- [ ] **Step 4: 创建 `src/data/adapters/base.py`**

```python
"""适配器抽象基类 — 所有数据源适配器必须实现此接口"""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class BaseAdapter(ABC):
    """统一数据源接口。
    
    返回的财务字段格式约定（与 financial.py 的 Data format contract 保持一致）：
      - roe, profit_margin, operating_margin, gross_margin: 小数形式 (0.15 = 15%)
      - pe_trailing, pb: 原始倍数值
      - debt_to_equity: 百分比*100 格式 (yfinance 兼容, e.g., 102.63)
      - current_ratio, quick_ratio: 原始比率
      - free_cashflow, operating_cashflow: 原始数字（正数 = 好）
      - market_cap, total_revenue: 原始数字
      - roe_history: 百分比数字列表 (e.g., [15.2, 16.3])
      - _source: str，数据来源标识
      - _data_quality: "confirmed" | "uncertain" | "single_source"
    """

    @abstractmethod
    def is_available(self) -> bool:
        """检查此适配器当前是否可用（token 有效、网络可达）"""
        ...

    @abstractmethod
    def get_a_share_financials(self, symbol: str) -> Optional[dict]:
        """获取 A 股基本面数据。symbol 格式: '600519'（不含市场后缀）
        返回 None 表示不支持或获取失败。
        """
        ...

    @abstractmethod
    def get_us_financials(self, symbol: str) -> Optional[dict]:
        """获取美股基本面数据。symbol 格式: 'AAPL'
        返回 None 表示不支持或获取失败。
        """
        ...

    @abstractmethod
    def get_a_share_history(self, symbol: str, days: int = 250) -> Optional[pd.DataFrame]:
        """获取 A 股历史 K 线。
        返回 DataFrame，列：date(str), open, high, low, close, volume
        返回 None 表示不支持或获取失败。
        """
        ...
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
python -m pytest tests/test_adapters.py -v
```

预期：`4 passed`

- [ ] **Step 6: Commit**

```bash
git add src/data/adapters/__init__.py src/data/adapters/base.py tests/test_adapters.py
git commit -m "feat: add BaseAdapter abstract interface for data sources"
```

---

## Task 3: Tushare Pro 适配器

**Files:**
- Create: `src/data/adapters/tushare_adapter.py`
- Modify: `tests/test_adapters.py`

- [ ] **Step 1: 追加 Tushare 测试（mock 模式）**

在 `tests/test_adapters.py` 末尾追加：

```python
from unittest.mock import patch, MagicMock
from src.data.adapters.tushare_adapter import TushareAdapter


def test_tushare_is_available_false_when_no_token(monkeypatch):
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    adapter = TushareAdapter()
    assert adapter.is_available() is False


def test_tushare_get_a_share_financials_parses_correctly():
    """mock tushare pro API，验证字段转换逻辑"""
    mock_pro = MagicMock()

    # mock daily_basic
    import pandas as pd
    mock_daily = pd.DataFrame([{
        "ts_code": "600519.SH", "trade_date": "20260601",
        "pe": 30.5, "pb": 8.2, "total_mv": 2300000000.0,
        "dv_ratio": 1.2,
    }])
    mock_pro.daily_basic.return_value = mock_daily

    # mock fina_indicator
    mock_fina = pd.DataFrame([{
        "ts_code": "600519.SH", "end_date": "20251231",
        "roe": 28.5, "grossprofit_margin": 92.3,
        "netprofit_margin": 46.8, "debt_to_assets": 35.2,
        "current_ratio": 2.8, "quick_ratio": 2.1,
        "fcff": 45000000000.0, "n_cashflow_act": 52000000000.0,
        "operate_income": 148000000000.0,
    }])
    mock_pro.fina_indicator.return_value = mock_fina

    with patch("tushare.pro_api", return_value=mock_pro):
        with patch("tushare.set_token"):
            adapter = TushareAdapter(token="fake_token")
            result = adapter.get_a_share_financials("600519")

    assert result is not None
    assert abs(result["roe"] - 0.285) < 0.001      # 28.5 → 0.285
    assert abs(result["gross_margin"] - 0.923) < 0.001
    assert result["pe_trailing"] == 30.5
    assert result["_source"] == "tushare"


def test_tushare_get_us_financials_returns_none():
    """Tushare 不支持美股，应返回 None"""
    adapter = TushareAdapter(token="fake_token")
    result = adapter.get_us_financials("AAPL")
    assert result is None
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_adapters.py -v -k "tushare"
```

预期：`ImportError` 或 `ModuleNotFoundError`

- [ ] **Step 3: 创建 `src/data/adapters/tushare_adapter.py`**

```python
"""Tushare Pro 数据源适配器 — A 股基本面 + K 线历史"""
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from .base import BaseAdapter

logger = logging.getLogger(__name__)


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        s = str(val).strip()
        if s in ("", "-", "--", "N/A", "nan"):
            return default
        f = float(s)
        return None if f != f else f  # NaN check
    except (TypeError, ValueError):
        return default


class TushareAdapter(BaseAdapter):
    """Tushare Pro 适配器，仅支持 A 股。
    
    Token 优先从构造参数读取，其次读 TUSHARE_TOKEN 环境变量。
    """

    def __init__(self, token: str | None = None):
        self._token = token or os.getenv("TUSHARE_TOKEN", "")
        self._pro = None

    def _get_pro(self):
        if self._pro is None and self._token:
            import tushare as ts
            ts.set_token(self._token)
            self._pro = ts.pro_api()
        return self._pro

    def is_available(self) -> bool:
        if not self._token:
            return False
        try:
            pro = self._get_pro()
            # 轻量测试：查一条交易日历
            result = pro.trade_cal(exchange="SSE", start_date="20260101", end_date="20260102")
            return result is not None and not result.empty
        except Exception as e:
            logger.debug("Tushare availability check failed: %s", e)
            return False

    def _to_ts_code(self, symbol: str) -> str:
        """'600519' → '600519.SH', '000001' → '000001.SZ'"""
        symbol = symbol.upper().strip()
        if symbol.endswith(".SH") or symbol.endswith(".SZ"):
            return symbol
        if symbol.startswith("6") or symbol.startswith("9"):
            return f"{symbol}.SH"
        return f"{symbol}.SZ"

    def get_a_share_financials(self, symbol: str) -> Optional[dict]:
        pro = self._get_pro()
        if pro is None:
            return None

        ts_code = self._to_ts_code(symbol)
        today = datetime.now().strftime("%Y%m%d")

        try:
            # 估值数据（PE/PB/市值）
            daily_basic = pro.daily_basic(
                ts_code=ts_code, trade_date=today,
                fields="ts_code,trade_date,pe,pb,total_mv,dv_ratio"
            )
            if daily_basic is None or daily_basic.empty:
                # 如果今天没有（非交易日），取最近 5 个交易日
                start = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
                daily_basic = pro.daily_basic(
                    ts_code=ts_code, start_date=start, end_date=today,
                    fields="ts_code,trade_date,pe,pb,total_mv,dv_ratio"
                )
                if daily_basic is not None and not daily_basic.empty:
                    daily_basic = daily_basic.iloc[0:1]

            # 财务指标（ROE/利润率/资产负债/现金流）
            # period 取最近一个完整季度：Q1=0331, Q2=0630, Q3=0930, Q4=1231
            now = datetime.now()
            q_ends = []
            for y in [now.year, now.year - 1]:
                for m in ["1231", "0930", "0630", "0331"]:
                    q_ends.append(f"{y}{m}")

            fina = None
            for period in q_ends[:4]:
                try:
                    df = pro.fina_indicator(
                        ts_code=ts_code, period=period,
                        fields="ts_code,end_date,roe,grossprofit_margin,netprofit_margin,"
                               "debt_to_assets,current_ratio,quick_ratio,fcff,n_cashflow_act,operate_income"
                    )
                    if df is not None and not df.empty:
                        fina = df.iloc[0]
                        break
                except Exception:
                    continue

            result: dict = {
                "_source": "tushare",
                "symbol": symbol,
            }

            # 估值字段
            if daily_basic is not None and not daily_basic.empty:
                row = daily_basic.iloc[0]
                result["pe_trailing"] = _safe_float(row.get("pe"))
                result["pb"] = _safe_float(row.get("pb"))
                mv = _safe_float(row.get("total_mv"))
                result["market_cap"] = mv * 10000 if mv else None  # tushare 单位万元
                result["dividend_yield"] = _safe_float(row.get("dv_ratio"))

            # 财务指标字段（tushare 返回百分比，需转小数）
            if fina is not None:
                roe = _safe_float(fina.get("roe"))
                result["roe"] = roe / 100.0 if roe is not None else None

                gm = _safe_float(fina.get("grossprofit_margin"))
                result["gross_margin"] = gm / 100.0 if gm is not None else None

                nm = _safe_float(fina.get("netprofit_margin"))
                result["profit_margin"] = nm / 100.0 if nm is not None else None

                da = _safe_float(fina.get("debt_to_assets"))
                if da is not None and 0 < da < 100:
                    debt_ratio = da / 100.0
                    if debt_ratio < 1.0:
                        result["debt_to_equity"] = (debt_ratio / (1 - debt_ratio)) * 100

                result["current_ratio"] = _safe_float(fina.get("current_ratio"))
                result["quick_ratio"] = _safe_float(fina.get("quick_ratio"))
                result["free_cashflow"] = _safe_float(fina.get("fcff"))
                result["operating_cashflow"] = _safe_float(fina.get("n_cashflow_act"))
                result["total_revenue"] = _safe_float(fina.get("operate_income"))

            return result if len(result) > 2 else None

        except Exception as e:
            logger.warning("TushareAdapter.get_a_share_financials(%s) failed: %s", symbol, e)
            return None

    def get_us_financials(self, symbol: str) -> Optional[dict]:
        # Tushare 不支持美股
        return None

    def get_a_share_history(self, symbol: str, days: int = 250) -> Optional[pd.DataFrame]:
        pro = self._get_pro()
        if pro is None:
            return None

        ts_code = self._to_ts_code(symbol)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days + 30)).strftime("%Y%m%d")

        try:
            df = pro.daily(
                ts_code=ts_code, start_date=start_date, end_date=end_date,
                fields="trade_date,open,high,low,close,vol"
            )
            if df is None or df.empty:
                return None

            df = df.rename(columns={"trade_date": "date", "vol": "volume"})
            df = df.sort_values("date").reset_index(drop=True)
            return df.tail(days)

        except Exception as e:
            logger.warning("TushareAdapter.get_a_share_history(%s) failed: %s", symbol, e)
            return None
```

- [ ] **Step 4: 更新 `src/data/adapters/__init__.py`**

```python
from .base import BaseAdapter
from .tushare_adapter import TushareAdapter

__all__ = ["BaseAdapter", "TushareAdapter"]
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
python -m pytest tests/test_adapters.py -v -k "tushare"
```

预期：`3 passed`（3 个 tushare 测试）

- [ ] **Step 6: Commit**

```bash
git add src/data/adapters/tushare_adapter.py src/data/adapters/__init__.py tests/test_adapters.py
git commit -m "feat: add TushareAdapter for A-share fundamentals and history"
```

---

## Task 4: SEC EDGAR 适配器

**Files:**
- Create: `src/data/adapters/sec_edgar_adapter.py`
- Modify: `tests/test_adapters.py`
- Modify: `src/data/adapters/__init__.py`

- [ ] **Step 1: 追加 SEC EDGAR 测试**

在 `tests/test_adapters.py` 末尾追加：

```python
from unittest.mock import patch
import json
from src.data.adapters.sec_edgar_adapter import SecEdgarAdapter


MOCK_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
}

MOCK_COMPANY_FACTS = {
    "entityName": "Apple Inc.",
    "facts": {
        "us-gaap": {
            "NetIncomeLoss": {
                "units": {"USD": [
                    {"end": "2024-09-30", "val": 93736000000, "form": "10-K", "filed": "2024-11-01", "accn": "a"},
                ]}
            },
            "Revenues": {
                "units": {"USD": [
                    {"end": "2024-09-30", "val": 391035000000, "form": "10-K", "filed": "2024-11-01", "accn": "a"},
                ]}
            },
            "StockholdersEquity": {
                "units": {"USD": [
                    {"end": "2024-09-30", "val": 56950000000, "form": "10-K", "filed": "2024-11-01", "accn": "a"},
                ]}
            },
            "GrossProfit": {
                "units": {"USD": [
                    {"end": "2024-09-30", "val": 180683000000, "form": "10-K", "filed": "2024-11-01", "accn": "a"},
                ]}
            },
        }
    }
}


def test_sec_edgar_get_us_financials_roe():
    """验证从 SEC EDGAR 计算 ROE = NetIncome / StockholdersEquity"""
    with patch("requests.get") as mock_get:
        def side_effect(url, **kwargs):
            m = MagicMock()
            if "company_tickers" in url:
                m.json.return_value = MOCK_TICKERS
                m.raise_for_status = lambda: None
            elif "companyfacts" in url:
                m.json.return_value = MOCK_COMPANY_FACTS
                m.raise_for_status = lambda: None
            else:
                m.raise_for_status.side_effect = Exception("unexpected url")
            return m

        mock_get.side_effect = side_effect
        adapter = SecEdgarAdapter()
        result = adapter.get_us_financials("AAPL")

    assert result is not None
    # ROE = 93736B / 56950B ≈ 1.646 → 以小数形式存储
    assert result["roe"] is not None
    assert abs(result["roe"] - (93736000000 / 56950000000)) < 0.01
    assert result["_source"] == "sec_edgar"


def test_sec_edgar_get_a_share_financials_returns_none():
    adapter = SecEdgarAdapter()
    result = adapter.get_a_share_financials("600519")
    assert result is None


def test_sec_edgar_get_a_share_history_returns_none():
    adapter = SecEdgarAdapter()
    result = adapter.get_a_share_history("600519")
    assert result is None
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_adapters.py -v -k "sec_edgar"
```

预期：`ImportError` 或 `ModuleNotFoundError`

- [ ] **Step 3: 创建 `src/data/adapters/sec_edgar_adapter.py`**

```python
"""SEC EDGAR 数据源适配器 — 美股官方财务数据（免费，无需 API Key）

数据来源：data.sec.gov XBRL API
覆盖：10-K / 10-Q 年报季报中的标准 US-GAAP 指标
"""
import logging
import time
from functools import lru_cache
from typing import Optional

import pandas as pd
import requests

from .base import BaseAdapter

logger = logging.getLogger(__name__)

_EDGAR_BASE = "https://data.sec.gov"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_HEADERS = {
    "User-Agent": "StockAnalyst research@example.com",  # SEC 要求提供联系信息
    "Accept-Encoding": "gzip, deflate",
}
_TIMEOUT = 15
_REQUEST_DELAY = 0.15  # SEC 限速：10 req/s


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return None if f != f else f
    except (TypeError, ValueError):
        return default


def _get_latest_annual_value(units_list: list) -> Optional[float]:
    """从 XBRL units 列表中取最新 10-K 年报值"""
    annual = [u for u in units_list if u.get("form") in ("10-K", "10-K/A")]
    if not annual:
        return None
    latest = max(annual, key=lambda u: u.get("filed", ""))
    return _safe_float(latest.get("val"))


class SecEdgarAdapter(BaseAdapter):
    """SEC EDGAR XBRL 适配器，仅支持美股。无需 API Key，免费使用。"""

    def is_available(self) -> bool:
        try:
            r = requests.get(_TICKERS_URL, headers=_HEADERS, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    @lru_cache(maxsize=1024)
    def _get_cik(self, ticker: str) -> Optional[str]:
        """ticker → CIK（补零到10位）"""
        try:
            r = requests.get(_TICKERS_URL, headers=_HEADERS, timeout=_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            ticker_upper = ticker.upper()
            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker_upper:
                    cik = str(entry["cik_str"]).zfill(10)
                    return cik
        except Exception as e:
            logger.debug("SEC EDGAR CIK lookup failed for %s: %s", ticker, e)
        return None

    def _get_company_facts(self, ticker: str) -> Optional[dict]:
        cik = self._get_cik(ticker)
        if not cik:
            return None
        time.sleep(_REQUEST_DELAY)
        try:
            url = f"{_EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
            r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.debug("SEC EDGAR company facts failed for %s: %s", ticker, e)
            return None

    def get_us_financials(self, ticker: str) -> Optional[dict]:
        facts = self._get_company_facts(ticker)
        if not facts:
            return None

        gaap = facts.get("facts", {}).get("us-gaap", {})

        def _get(concept: str) -> Optional[float]:
            data = gaap.get(concept, {})
            usd = data.get("units", {}).get("USD", [])
            return _get_latest_annual_value(usd)

        net_income = _get("NetIncomeLoss")
        equity = _get("StockholdersEquity")
        revenues = _get("Revenues") or _get("RevenueFromContractWithCustomerExcludingAssessedTax")
        gross_profit = _get("GrossProfit")
        operating_income = _get("OperatingIncomeLoss")
        total_assets = _get("Assets")
        total_liabilities = _get("Liabilities")
        current_assets = _get("AssetsCurrent")
        current_liabilities = _get("LiabilitiesCurrent")
        operating_cf = _get("NetCashProvidedByUsedInOperatingActivities")
        capex_raw = _get("PaymentsToAcquirePropertyPlantAndEquipment")
        capex = -abs(capex_raw) if capex_raw is not None else None

        # 计算派生指标
        roe = (net_income / equity) if (net_income and equity and equity != 0) else None
        roa = (net_income / total_assets) if (net_income and total_assets and total_assets != 0) else None
        profit_margin = (net_income / revenues) if (net_income and revenues and revenues != 0) else None
        gross_margin = (gross_profit / revenues) if (gross_profit and revenues and revenues != 0) else None
        operating_margin = (operating_income / revenues) if (operating_income and revenues and revenues != 0) else None
        current_ratio = (current_assets / current_liabilities) if (current_assets and current_liabilities and current_liabilities != 0) else None
        debt_to_equity = None
        if total_liabilities and equity and equity != 0:
            debt_to_equity = (total_liabilities / equity) * 100  # yfinance 兼容格式
        fcf = (operating_cf + capex) if (operating_cf and capex) else operating_cf

        result = {
            "_source": "sec_edgar",
            "symbol": ticker,
            "roe": roe,
            "roa": roa,
            "profit_margin": profit_margin,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "total_revenue": revenues,
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "free_cashflow": fcf,
            "operating_cashflow": operating_cf,
        }

        return result

    def get_a_share_financials(self, symbol: str) -> Optional[dict]:
        return None  # 不支持 A 股

    def get_a_share_history(self, symbol: str, days: int = 250) -> Optional[pd.DataFrame]:
        return None  # 不支持 A 股历史
```

- [ ] **Step 4: 更新 `src/data/adapters/__init__.py`**

```python
from .base import BaseAdapter
from .tushare_adapter import TushareAdapter
from .sec_edgar_adapter import SecEdgarAdapter

__all__ = ["BaseAdapter", "TushareAdapter", "SecEdgarAdapter"]
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
python -m pytest tests/test_adapters.py -v -k "sec_edgar"
```

预期：`3 passed`

- [ ] **Step 6: 运行全部适配器测试**

```bash
python -m pytest tests/test_adapters.py -v
```

预期：`7 passed`（Task 2 的 4 个 + Task 3 的 3 个）

- [ ] **Step 7: Commit**

```bash
git add src/data/adapters/sec_edgar_adapter.py src/data/adapters/__init__.py tests/test_adapters.py
git commit -m "feat: add SecEdgarAdapter for US stock official financials"
```

---

## Task 5: CrossValidator

**Files:**
- Create: `src/data/cross_validator.py`
- Create: `tests/test_cross_validator.py`

- [ ] **Step 1: 写失败测试**

新建 `tests/test_cross_validator.py`：

```python
"""测试 CrossValidator 多源校验逻辑"""
import pytest
from src.data.cross_validator import CrossValidator, ValidationResult


def test_single_source_returns_single_source_quality():
    cv = CrossValidator()
    result = cv.validate_field({"yfinance": 0.15})
    assert result.value == 0.15
    assert result.quality == "single_source"
    assert result.warning == ""


def test_two_sources_within_threshold_returns_confirmed():
    cv = CrossValidator()
    result = cv.validate_field({"yfinance": 0.15, "tushare": 0.153})
    assert result.quality == "confirmed"
    assert abs(result.value - 0.1515) < 0.001  # 均值
    assert result.warning == ""


def test_two_sources_exceed_threshold_returns_uncertain():
    cv = CrossValidator()
    result = cv.validate_field({"yfinance": 0.15, "tushare": 0.22})
    assert result.quality == "uncertain"
    assert "⚠️" in result.warning


def test_none_values_filtered_out():
    cv = CrossValidator()
    result = cv.validate_field({"yfinance": 0.15, "tushare": None})
    assert result.value == 0.15
    assert result.quality == "single_source"


def test_all_none_returns_none():
    cv = CrossValidator()
    result = cv.validate_field({"yfinance": None, "tushare": None})
    assert result.value is None


def test_validate_fundamentals_merges_fields():
    cv = CrossValidator()
    source_a = {"roe": 0.15, "pe_trailing": 12.0, "gross_margin": 0.45, "_source": "a"}
    source_b = {"roe": 0.153, "pe_trailing": 12.5, "gross_margin": None, "_source": "b"}
    
    merged = cv.validate_fundamentals(source_a, source_b)
    assert merged["roe"] is not None
    assert merged["_data_quality"]["roe"] == "confirmed"
    assert merged["_data_quality"]["pe_trailing"] == "confirmed"
    assert merged["_data_quality"]["gross_margin"] == "single_source"


def test_threshold_customizable():
    cv = CrossValidator(threshold=0.10)
    # 差异 8%，在 10% 阈值内 → confirmed
    result = cv.validate_field({"a": 1.00, "b": 1.08}, threshold=0.10)
    assert result.quality == "confirmed"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_cross_validator.py -v
```

预期：`ImportError: No module named 'src.data.cross_validator'`

- [ ] **Step 3: 创建 `src/data/cross_validator.py`**

```python
"""多数据源交叉校验器 — 检测数据源间差异，标注数据质量"""
from dataclasses import dataclass, field
from typing import Optional


_NUMERIC_FIELDS = [
    "roe", "roa", "profit_margin", "gross_margin", "operating_margin",
    "pe_trailing", "pe_forward", "pb", "ps",
    "debt_to_equity", "current_ratio", "quick_ratio",
    "revenue_growth", "earnings_growth",
    "dividend_yield", "market_cap", "total_revenue",
]

_DEFAULT_THRESHOLD = 0.05  # 5% 差异阈值


@dataclass
class ValidationResult:
    value: Optional[float]
    quality: str  # "confirmed" | "uncertain" | "single_source"
    warning: str = ""
    sources: dict = field(default_factory=dict)


class CrossValidator:
    def __init__(self, threshold: float = _DEFAULT_THRESHOLD):
        self.default_threshold = threshold

    def validate_field(
        self,
        values: dict[str, Optional[float]],
        threshold: float | None = None,
    ) -> ValidationResult:
        """
        values: {"source_name": float_or_none, ...}
        返回 ValidationResult 包含共识值、质量标注、警告信息。
        """
        th = threshold if threshold is not None else self.default_threshold
        valid = {k: v for k, v in values.items() if v is not None}

        if not valid:
            return ValidationResult(value=None, quality="single_source", sources=values)

        if len(valid) == 1:
            val = next(iter(valid.values()))
            return ValidationResult(value=val, quality="single_source", sources=values)

        vals = list(valid.values())
        mean_val = sum(vals) / len(vals)
        max_val = max(abs(v) for v in vals)

        if max_val == 0:
            return ValidationResult(value=mean_val, quality="confirmed", sources=values)

        max_diff = (max(vals) - min(vals)) / max_val

        if max_diff > th:
            warning = f"⚠️ 数据源差异 {max_diff:.1%}（{', '.join(f'{k}={v:.4g}' for k, v in valid.items())}）"
            return ValidationResult(
                value=mean_val, quality="uncertain", warning=warning, sources=values
            )

        return ValidationResult(value=mean_val, quality="confirmed", sources=values)

    def validate_fundamentals(
        self,
        *sources: dict,
        threshold: float | None = None,
    ) -> dict:
        """
        合并多个数据源的基本面 dict，对每个数字字段做交叉校验。
        返回合并后的 dict，新增 _data_quality: {field: quality} 和 _warnings: [str]。
        """
        if not sources:
            return {}

        # 基础：用第一个有效源作为模板（包含非数字字段如 name, sector 等）
        merged = {}
        for src in sources:
            if src:
                merged.update({k: v for k, v in src.items() if not k.startswith("_")})
                break

        quality_map: dict[str, str] = {}
        warnings: list[str] = []

        for field_name in _NUMERIC_FIELDS:
            field_values = {}
            for src in sources:
                if src and field_name in src:
                    src_name = src.get("_source", f"source_{id(src)}")
                    field_values[src_name] = src[field_name]

            if not field_values:
                continue

            result = self.validate_field(field_values, threshold=threshold)
            merged[field_name] = result.value
            quality_map[field_name] = result.quality
            if result.warning:
                warnings.append(f"{field_name}: {result.warning}")

        merged["_data_quality"] = quality_map
        merged["_warnings"] = warnings

        # 合并数据来源标注
        src_names = [s.get("_source", "unknown") for s in sources if s]
        merged["data_source"] = "+".join(src_names)

        return merged
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest tests/test_cross_validator.py -v
```

预期：`7 passed`

- [ ] **Step 5: Commit**

```bash
git add src/data/cross_validator.py tests/test_cross_validator.py
git commit -m "feat: add CrossValidator for multi-source data quality checking"
```

---

## Task 6: 接入 financial.py — A 股路径

**Files:**
- Modify: `src/data/financial.py`

**策略**：在 A 股分支中，Tushare 数据与 Sina 数据并行获取，CrossValidator 校验关键字段。接口签名 `fetch_fundamentals(symbol, market)` 不变。

- [ ] **Step 1: 在 `financial.py` 顶部增加导入**

在 `financial.py` 现有 import 块末尾（`import requests` 之后）追加：

```python
# 新增：数据适配器 + 交叉校验
try:
    from src.data.adapters import TushareAdapter
    from src.data.cross_validator import CrossValidator
    _tushare = TushareAdapter()
    _cross_validator = CrossValidator()
except ImportError:
    _tushare = None
    _cross_validator = None
```

- [ ] **Step 2: 在 `fetch_fundamentals` 的 A 股分支末尾注入 Tushare 校验**

找到 `fetch_fundamentals` 函数中处理 A 股的位置（约 L640 附近），在 `_write_cache(cache_path, result)` 调用之前插入：

```python
        # ── Tushare 交叉校验（A 股）─────────────────────────────────
        if market == "a_share" and _tushare and _cross_validator:
            try:
                ts_data = _tushare.get_a_share_financials(symbol)
                if ts_data:
                    result = _cross_validator.validate_fundamentals(result, ts_data)
                    if result.get("_warnings"):
                        logger.info(
                            "CrossValidator warnings for %s: %s",
                            symbol, result["_warnings"]
                        )
            except Exception as e:
                logger.debug("Tushare cross-validation failed for %s: %s", symbol, e)
        # ── /Tushare 交叉校验 ─────────────────────────────────────────
```

- [ ] **Step 3: 验证 A 股接口不变**

```bash
cd ~/stock-analyst
source .venv/bin/activate
python -c "
from src.data.financial import fetch_fundamentals
result = fetch_fundamentals('600519', 'a_share')
print('Keys:', list(result.keys())[:10])
print('ROE:', result.get('roe'))
print('Source:', result.get('data_source'))
print('Quality:', result.get('_data_quality', {}).get('roe', 'N/A'))
"
```

预期：正常返回 dict，ROE 有值，无报错。如果 Tushare token 未配置，data_source 仍显示原来的 `tencent+sina`，不影响功能。

- [ ] **Step 4: Commit**

```bash
git add src/data/financial.py
git commit -m "feat: integrate TushareAdapter into A-share financials with cross-validation"
```

---

## Task 7: 接入 financial.py — 美股路径

**Files:**
- Modify: `src/data/financial.py`

**策略**：在 yfinance 成功获取数据后，用 SEC EDGAR 补充/校验。yfinance 失败时，SEC EDGAR 作为 fallback。

- [ ] **Step 1: 在 `financial.py` 顶部增加 SEC EDGAR 导入**

在 Task 6 的 import 块中追加：

```python
try:
    from src.data.adapters import TushareAdapter, SecEdgarAdapter
    from src.data.cross_validator import CrossValidator
    _tushare = TushareAdapter()
    _sec_edgar = SecEdgarAdapter()
    _cross_validator = CrossValidator()
except ImportError:
    _tushare = None
    _sec_edgar = None
    _cross_validator = None
```

（替换 Task 6 中写的 import 块）

- [ ] **Step 2: 在 US 分支的 yfinance 成功路径后注入 SEC EDGAR 校验**

找到 `if market == "us":` 分支中 `_write_cache(cache_path, result)` 调用前，插入：

```python
        # ── SEC EDGAR 交叉校验（美股）────────────────────────────────
        if market == "us" and _sec_edgar and _cross_validator:
            try:
                edgar_data = _sec_edgar.get_us_financials(symbol)
                if edgar_data:
                    result = _cross_validator.validate_fundamentals(result, edgar_data)
                    if result.get("_warnings"):
                        logger.info(
                            "CrossValidator warnings for %s: %s",
                            symbol, result["_warnings"]
                        )
            except Exception as e:
                logger.debug("SEC EDGAR cross-validation failed for %s: %s", symbol, e)
        # ── /SEC EDGAR 交叉校验 ───────────────────────────────────────
```

- [ ] **Step 3: 在 yfinance 失败的 fallback 路径增加 SEC EDGAR 降级**

找到 `logger.warning("yfinance failed for %s, falling back to eastmoney", symbol)` 之后，追加：

```python
            # yfinance 彻底失败时尝试 SEC EDGAR 作为独立 fallback
            if _sec_edgar:
                try:
                    edgar_data = _sec_edgar.get_us_financials(symbol)
                    if edgar_data:
                        logger.info("Using SEC EDGAR as fallback for %s", symbol)
                        _write_cache(cache_path, edgar_data)
                        return edgar_data
                except Exception as edgar_err:
                    logger.debug("SEC EDGAR fallback failed for %s: %s", symbol, edgar_err)
```

- [ ] **Step 4: 验证美股接口不变**

```bash
python -c "
from src.data.financial import fetch_fundamentals
result = fetch_fundamentals('AAPL', 'us')
print('Keys:', list(result.keys())[:10])
print('ROE:', result.get('roe'))
print('Source:', result.get('data_source'))
print('Warnings count:', len(result.get('_warnings', [])))
"
```

预期：正常返回，ROE 有值，无报错。

- [ ] **Step 5: Commit**

```bash
git add src/data/financial.py
git commit -m "feat: integrate SecEdgarAdapter into US stock financials with fallback"
```

---

## Task 8: 接入 price.py — A 股历史行情

**Files:**
- Modify: `src/data/price.py`

**策略**：A 股 `fetch_history` 优先使用 Tushare（更稳定），腾讯作为 fallback。

- [ ] **Step 1: 在 `price.py` 顶部追加导入**

在现有 import 块末尾追加：

```python
try:
    from src.data.adapters import TushareAdapter as _TushareAdapterCls
    _tushare_price = _TushareAdapterCls()
except ImportError:
    _tushare_price = None
```

- [ ] **Step 2: 修改 `fetch_history` 的 A 股分支**

找到 `fetch_history` 函数（约 L394）中处理 A 股的部分，在现有腾讯调用之前插入 Tushare 优先路径：

```python
    # ── Tushare 优先（A 股 K 线，更稳定）────────────────────────────
    if market == "a_share" and _tushare_price:
        try:
            ts_df = _tushare_price.get_a_share_history(symbol, days=days)
            if ts_df is not None and not ts_df.empty:
                # 统一列名到现有格式
                if "date" in ts_df.columns and "close" in ts_df.columns:
                    logger.debug("fetch_history: using Tushare for %s", symbol)
                    _write_kline_cache(cache_path, ts_df)
                    return ts_df
        except Exception as e:
            logger.debug("Tushare history failed for %s, falling back: %s", symbol, e)
    # ── /Tushare 优先 ─────────────────────────────────────────────────
```

（放在调用腾讯 API 的代码之前）

- [ ] **Step 3: 验证历史行情接口不变**

```bash
python -c "
from src.data.price import fetch_history
df = fetch_history('600519', 'a_share', days=30)
print('Shape:', df.shape)
print('Columns:', list(df.columns))
print('Last date:', df['date'].iloc[-1] if not df.empty else 'empty')
"
```

预期：返回 DataFrame，有日期和收盘价列，无报错。

- [ ] **Step 4: Commit**

```bash
git add src/data/price.py
git commit -m "feat: use TushareAdapter as primary source for A-share price history"
```

---

## Task 9: 全链路回归测试

**Files:**
- Modify: `tests/smoke_v2_pipeline.py`（复用现有 smoke test 框架）

- [ ] **Step 1: 运行现有 smoke test，确认分析页功能无回归**

```bash
cd ~/stock-analyst
source .venv/bin/activate
python tests/smoke_v2_pipeline.py 2>&1 | tail -30
```

预期：原有测试通过，无新增 ERROR。

- [ ] **Step 2: 运行全部新增测试**

```bash
python -m pytest tests/test_adapters.py tests/test_cross_validator.py -v
```

预期：`10 passed`（7 个适配器测试 + 7 个 CrossValidator 测试，共 ≥10）

- [ ] **Step 3: 快速功能验证（A 股 + 美股）**

```bash
python -c "
from src.data.financial import fetch_fundamentals
from src.data.price import fetch_history, fetch_quote

# A 股
f = fetch_fundamentals('600519', 'a_share')
assert f.get('roe') is not None or f.get('pe_trailing') is not None, 'A股基本面空数据'
print('✅ A股基本面 OK, ROE=', f.get('roe'), 'source=', f.get('data_source'))

q = fetch_quote('600519', 'a_share')
assert q.get('price') or q.get('close'), 'A股行情空数据'
print('✅ A股行情 OK')

h = fetch_history('600519', 'a_share', days=10)
assert not h.empty, 'A股历史K线空数据'
print('✅ A股历史K线 OK, shape=', h.shape)

# 美股
f2 = fetch_fundamentals('AAPL', 'us')
assert f2.get('roe') is not None or f2.get('pe_trailing') is not None, '美股基本面空数据'
print('✅ 美股基本面 OK, ROE=', f2.get('roe'), 'source=', f2.get('data_source'))

print()
print('🎉 全部通过，分析页数据链路正常')
"
```

- [ ] **Step 4: 最终 Commit**

```bash
git add -A
git commit -m "feat: complete data source upgrade — Tushare + SEC EDGAR + CrossValidator"
```

---

## 成功标准核查

- [ ] `fetch_fundamentals(symbol, market)` 签名不变，现有调用零修改
- [ ] `fetch_quote(symbol, market)` 不受影响
- [ ] `fetch_history(symbol, market, days)` 签名不变
- [ ] A 股有 Tushare 作为备用/校验源
- [ ] 美股有 SEC EDGAR 作为校验/fallback
- [ ] 数据质量警告通过 `_data_quality` 字段暴露给上层（不阻断流程）
- [ ] `tests/test_adapters.py` 和 `tests/test_cross_validator.py` 全部通过
- [ ] 原有 smoke test 无回归
