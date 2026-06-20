import sys
import types
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest


def _make_akshare_mock(**kwargs):
    """Create a fake akshare module with given function mocks."""
    mock_ak = types.ModuleType("akshare")
    for name, value in kwargs.items():
        setattr(mock_ak, name, value)
    return mock_ak


def test_get_csi300_tickers_returns_list():
    mock_df = pd.DataFrame({
        "成分券代码": ["600519", "000858", "601318"],
        "成分券名称": ["贵州茅台", "五粮液", "中国平安"],
    })
    mock_ak = _make_akshare_mock(index_stock_cons_csindex=MagicMock(return_value=mock_df))
    with patch.dict(sys.modules, {"akshare": mock_ak}):
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
    mock_ak = _make_akshare_mock(index_stock_cons_csindex=MagicMock(return_value=mock_df))
    with patch.dict(sys.modules, {"akshare": mock_ak}):
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


def test_get_csi300_tickers_returns_empty_on_error():
    mock_ak = _make_akshare_mock(
        index_stock_cons_csindex=MagicMock(side_effect=RuntimeError("network error"))
    )
    with patch.dict(sys.modules, {"akshare": mock_ak}):
        from src.screener.universe import get_csi300_tickers
        result = get_csi300_tickers()
    assert result == []


def test_fetch_basic_fundamentals_us():
    # patch "yfinance.Ticker" because the lazy import inside _fetch_us_fundamentals
    # resolves from sys.modules cache, so this is the correct patch target
    from src.screener.universe import fetch_basic_fundamentals
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
        result = fetch_basic_fundamentals("AAPL")
    assert result["pe"] == pytest.approx(28.5)
    assert result["roe"] == pytest.approx(0.18)


def test_fetch_basic_fundamentals_returns_empty_on_error():
    with patch("yfinance.Ticker", side_effect=Exception("network error")):
        from src.screener.universe import fetch_basic_fundamentals
        result = fetch_basic_fundamentals("INVALID")
    assert result == {}


def test_fetch_basic_fundamentals_ashare():
    mock_df = pd.DataFrame([{
        "代码": "600519",
        "市盈率-动态": "35.6",
        "市净率": "8.2",
        "总市值": 2000000000000,
    }])
    mock_ak = _make_akshare_mock(stock_zh_a_spot_em=MagicMock(return_value=mock_df))
    with patch.dict(sys.modules, {"akshare": mock_ak}):
        from src.screener.universe import fetch_basic_fundamentals
        result = fetch_basic_fundamentals("sh600519")
    assert result["pe"] == pytest.approx(35.6)
    assert result["pb"] == pytest.approx(8.2)
    assert result["roe"] is None


def test_fetch_basic_fundamentals_ashare_not_found():
    mock_df = pd.DataFrame(columns=["代码", "市盈率-动态", "市净率", "总市值"])
    mock_ak = _make_akshare_mock(stock_zh_a_spot_em=MagicMock(return_value=mock_df))
    with patch.dict(sys.modules, {"akshare": mock_ak}):
        from src.screener.universe import fetch_basic_fundamentals
        result = fetch_basic_fundamentals("sh999999")
    assert result == {}


def test_safe_float_with_none():
    from src.screener.universe import _safe_float
    assert _safe_float(None) is None


def test_safe_float_with_invalid_string():
    from src.screener.universe import _safe_float
    assert _safe_float("N/A") is None


def test_safe_float_with_valid_value():
    from src.screener.universe import _safe_float
    assert _safe_float("35.6") == pytest.approx(35.6)
    assert _safe_float(42) == pytest.approx(42.0)
