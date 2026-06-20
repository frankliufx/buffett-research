"""测试 BaseAdapter 接口约定"""
from __future__ import annotations

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


from unittest.mock import patch, MagicMock
from src.data.adapters.tushare_adapter import TushareAdapter


def test_tushare_is_available_false_when_no_token(monkeypatch):
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    adapter = TushareAdapter()
    assert adapter.is_available() is False


def test_tushare_get_a_share_financials_parses_correctly():
    """mock tushare pro API，验证字段转换逻辑"""
    mock_pro = MagicMock()

    import pandas as pd
    mock_daily = pd.DataFrame([{
        "ts_code": "600519.SH", "trade_date": "20260601",
        "pe": 30.5, "pb": 8.2, "total_mv": 2300000000.0,
        "dv_ratio": 1.2,
    }])
    mock_pro.daily_basic.return_value = mock_daily

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
    assert abs(result["roe"] - 0.285) < 0.001
    assert abs(result["gross_margin"] - 0.923) < 0.001
    assert result["pe_trailing"] == 30.5
    assert result["_source"] == "tushare"


def test_tushare_get_us_financials_returns_none():
    """Tushare 不支持美股，应返回 None"""
    adapter = TushareAdapter(token="fake_token")
    result = adapter.get_us_financials("AAPL")
    assert result is None


from unittest.mock import patch, MagicMock
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
