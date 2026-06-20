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
