from unittest.mock import patch
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


def test_get_csi300_tickers_returns_empty_on_error():
    with patch("akshare.index_stock_cons_csindex", side_effect=RuntimeError("network error")):
        from src.screener.universe import get_csi300_tickers
        result = get_csi300_tickers()
    assert result == []
