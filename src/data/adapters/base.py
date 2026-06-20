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
