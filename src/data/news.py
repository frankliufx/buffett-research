"""新闻与财报信息采集 — 美股/港股/A股

数据源：
- A股个股新闻: 东方财富公告 API
- 市场整体新闻: 新浪财经滚动新闻 API
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.eastmoney.com",
}

_REQUEST_TIMEOUT = 15


def _safe_str(val, default=""):
    if val is None:
        return default
    return str(val).strip() or default


def _ts_to_str(ts) -> str:
    """Unix 时间戳转 MM-DD HH:MM"""
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%m-%d %H:%M")
    except Exception:
        return ""


def _extract_stock_code(symbol: str, market: str) -> str:
    """提取纯数字股票代码（A股用）"""
    s = symbol.lower()
    if s.startswith("sh") or s.startswith("sz"):
        return s[2:]
    return s


def _fetch_eastmoney_announcements(stock_code: str, limit: int = 8) -> List[Dict]:
    """从东方财富获取 A 股公告/新闻（已验证可用）"""
    try:
        url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        params = {
            "sr": "-1",
            "page_size": str(limit),
            "page_index": "1",
            "ann_type": "A,SHA",
            "client_source": "web",
            "stock_list": stock_code,
        }
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
        data = resp.json()

        items = data.get("data", {}).get("list", [])
        results = []
        for item in items[:limit]:
            title = _safe_str(item.get("title"))
            if not title:
                continue

            art_code = _safe_str(item.get("art_code"))
            news_url = f"https://data.eastmoney.com/notices/detail/{stock_code}/{art_code}.html" if art_code else ""

            display_time = _safe_str(item.get("display_time"))
            time_str = display_time[:10] if display_time else ""

            results.append({
                "title": title,
                "source": "东方财富",
                "time": time_str,
                "url": news_url,
                "summary": "",
            })
        return results
    except Exception as e:
        logger.warning("Eastmoney announcements failed for %s: %s", stock_code, e)
        return []


def _fetch_sina_roll_news(lid: str, limit: int = 8, keyword: str = "") -> List[Dict]:
    """从新浪财经滚动新闻获取新闻（已验证可用）

    常用 lid:
    - 2516: A股
    - 1686: 港股
    - 174: 美股
    """
    try:
        url = "https://feed.mix.sina.com.cn/api/roll/get"
        params = {
            "pageid": "153",
            "lid": lid,
            "num": str(min(limit * 3, 50)),  # 多取一些用于过滤
            "page": "1",
        }
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
        data = resp.json()
        items = data.get("result", {}).get("data", [])

        results = []
        for item in items:
            title = _safe_str(item.get("title"))
            if not title:
                continue
            # 如果有关键词过滤
            if keyword and keyword not in title and keyword not in _safe_str(item.get("intro", "")):
                continue

            ts = item.get("ctime", 0)
            time_str = _ts_to_str(ts) if ts else ""

            results.append({
                "title": title,
                "source": _safe_str(item.get("media_name"), "新浪财经"),
                "time": time_str,
                "url": _safe_str(item.get("url")),
                "summary": _safe_str(item.get("intro", ""))[:200],
            })

            if len(results) >= limit:
                break

        return results
    except Exception as e:
        logger.warning("Sina roll news failed for lid=%s: %s", lid, e)
        return []


def _fetch_tencent_stock_news(tencent_sym: str, limit: int = 8) -> List[Dict]:
    """从腾讯财经获取个股新闻（备用）"""
    try:
        url = "https://proxy.finance.qq.com/ifzqgtimg/appstock/news/info/search"
        params = {
            "stock": tencent_sym,
            "page": "0",
            "type": "0",
        }
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
        data = resp.json()

        results = []
        news_list = data.get("data", {}).get("data", {}).get("list", [])
        for item in news_list[:limit]:
            title = _safe_str(item.get("title"))
            if not title:
                continue

            pub_time = _safe_str(item.get("time"))
            if pub_time:
                try:
                    dt = datetime.strptime(pub_time, "%Y-%m-%d %H:%M:%S")
                    pub_time = dt.strftime("%m-%d %H:%M")
                except Exception:
                    pass

            results.append({
                "title": title,
                "source": _safe_str(item.get("source"), "腾讯财经"),
                "time": pub_time,
                "url": _safe_str(item.get("url")),
                "summary": _safe_str(item.get("abstract", ""))[:200],
            })

        return results
    except Exception as e:
        logger.debug("Tencent news failed for %s: %s", tencent_sym, e)
        return []


def _hk_sym_to_code(symbol: str) -> str:
    """0700.HK -> 00700"""
    code = symbol.replace(".HK", "").replace(".hk", "")
    return code.zfill(5)


def fetch_stock_news(symbol: str, market: str, limit: int = 8) -> List[Dict]:
    """获取个股新闻，返回统一格式列表

    Returns list of dicts with keys: title, source, time, url, summary
    """
    try:
        if market == "a_share":
            # A股: 东方财富公告（已验证可用）
            stock_code = _extract_stock_code(symbol, market)
            results = _fetch_eastmoney_announcements(stock_code, limit)
            if results:
                return results
            # 备用: 新浪A股综合新闻
            return _fetch_sina_roll_news("2516", limit)

        elif market == "hk":
            # 港股: 东方财富港股公告
            hk_code = _hk_sym_to_code(symbol)
            results = _fetch_eastmoney_announcements(hk_code, limit)
            if results:
                return results
            # 备用: 腾讯财经新闻
            from src.data.price import _to_tencent_symbol
            tencent_sym = _to_tencent_symbol(symbol, market)
            results = _fetch_tencent_stock_news(tencent_sym, limit)
            if results:
                return results
            # 最后备用: A股新闻频道（有港股内容）
            return _fetch_sina_roll_news("2516", limit)

        else:
            # 美股: 腾讯财经新闻
            from src.data.price import _to_tencent_symbol
            tencent_sym = _to_tencent_symbol(symbol, market)
            results = _fetch_tencent_stock_news(tencent_sym, limit)
            if results:
                return results
            # 备用: 新浪综合新闻
            return _fetch_sina_roll_news("2516", limit)

    except Exception as e:
        logger.warning("fetch_stock_news failed for %s: %s", symbol, e)
        return []


def fetch_earnings_calendar(symbol: str, market: str) -> Optional[Dict]:
    """获取财报日历（暂无可靠免费 API，返回 None）"""
    return None


def fetch_market_news(market: str = "general", limit: int = 6) -> List[Dict]:
    """获取市场整体新闻（新浪财经滚动新闻）"""
    try:
        lid_map = {
            "a_share": "2516",
            "hk": "1686",
            "us": "174",
        }
        lid = lid_map.get(market, "2516")
        return _fetch_sina_roll_news(lid, limit)
    except Exception as e:
        logger.warning("fetch_market_news failed for %s: %s", market, e)
        return []
