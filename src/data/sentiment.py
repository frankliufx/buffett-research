"""市场情绪分析 — 基于东方财富实时数据

指标体系:
1. 大盘指数涨跌幅 → 恐惧/贪婪判断
2. 两市成交额 → 市场活跃度
3. 北向资金净流入 → 外资情绪
4. 综合情绪分数 (0-100)
"""

import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.eastmoney.com",
}
_TIMEOUT = 8

# 缓存
_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
_CACHE_FILE = _CACHE_DIR / "sentiment.json"
_CACHE_TTL = 300  # 5 分钟


def _read_cache():
    try:
        if _CACHE_FILE.exists():
            data = json.loads(_CACHE_FILE.read_text())
            if time.time() - data.get("_ts", 0) < _CACHE_TTL:
                data.pop("_ts", None)
                return data
    except Exception:
        pass
    return None


def _write_cache(data):
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        to_save = dict(data)
        to_save["_ts"] = time.time()
        _CACHE_FILE.write_text(json.dumps(to_save, ensure_ascii=False))
    except Exception:
        pass


def _fetch_indices():
    """获取大盘指数数据（上证、深证、创业板）"""
    url = ("https://push2.eastmoney.com/api/qt/ulist.np/get"
           "?fltt=2&fields=f2,f3,f4,f6,f12,f14"
           "&secids=1.000001,0.399001,0.399006")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        items = resp.json().get("data", {}).get("diff", [])
        indices = []
        for item in items:
            indices.append({
                "name": item.get("f14", ""),
                "code": item.get("f12", ""),
                "price": item.get("f2", 0),
                "change_pct": item.get("f3", 0),
                "change_val": item.get("f4", 0),
                "amount": item.get("f6", 0),  # 成交额(元)
            })
        return indices
    except Exception as e:
        logger.warning("获取指数失败: %s", e)
        return []


def _fetch_northbound():
    """获取北向资金（沪港通+深港通）净流入"""
    url = ("https://push2.eastmoney.com/api/qt/kamt.rtmin/get"
           "?fields1=f1,f2,f3,f4"
           "&fields2=f51,f52,f53,f54,f55,f56")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        data = resp.json().get("data", {})
        # f1=沪股通今日净流入 f2=深股通今日净流入 f3=北向合计
        hgt = data.get("f1", 0)  # 沪股通
        sgt = data.get("f2", 0)  # 深股通
        total = data.get("f3", 0)  # 合计
        return {
            "hgt": hgt,  # 沪股通净流入(元)
            "sgt": sgt,  # 深股通净流入(元)
            "total": total,  # 北向合计(元)
        }
    except Exception as e:
        logger.warning("获取北向资金失败: %s", e)
        return {"hgt": 0, "sgt": 0, "total": 0}


def _calc_fear_greed(change_pct, amount_yi, northbound_yi):
    """计算恐惧贪婪指数 (0-100)

    0 = 极度恐惧, 50 = 中性, 100 = 极度贪婪

    权重:
    - 大盘涨跌幅: 50%
    - 成交量水位: 25%
    - 北向资金: 25%
    """
    # 1. 涨跌幅 → 0-100 (正态映射: -4%→10, 0%→50, +4%→90)
    pct_score = max(0, min(100, 50 + change_pct * 12.5))

    # 2. 成交量 → 0-100 (万亿为基准)
    # < 6000亿 = 低迷(20), 8000-12000 = 正常(50), > 15000 = 火热(80), > 20000 = 疯狂(95)
    if amount_yi <= 0:
        vol_score = 50  # 无数据时中性
    elif amount_yi < 6000:
        vol_score = 20
    elif amount_yi < 8000:
        vol_score = 20 + (amount_yi - 6000) / 2000 * 30
    elif amount_yi < 12000:
        vol_score = 50 + (amount_yi - 8000) / 4000 * 15
    elif amount_yi < 20000:
        vol_score = 65 + (amount_yi - 12000) / 8000 * 25
    else:
        vol_score = min(95, 90 + (amount_yi - 20000) / 10000 * 5)

    # 3. 北向资金 → 0-100 (净流入亿: -100→10, 0→50, +100→90)
    if northbound_yi == 0:
        north_score = 50
    else:
        north_score = max(0, min(100, 50 + northbound_yi * 0.4))

    # 加权
    score = pct_score * 0.50 + vol_score * 0.25 + north_score * 0.25
    return round(max(0, min(100, score)), 1)


def _mood_label(score):
    """恐惧贪婪分数 → 文字标签"""
    if score <= 15:
        return "极度恐惧", "#EF4444"
    elif score <= 30:
        return "恐惧", "#F5A623"
    elif score <= 45:
        return "偏恐惧", "#F5A623"
    elif score <= 55:
        return "中性", "#C9A962"
    elif score <= 70:
        return "偏贪婪", "#60A5FA"
    elif score <= 85:
        return "贪婪", "#3ECF8E"
    else:
        return "极度贪婪", "#3ECF8E"


def _fetch_sector_flow(limit=10):
    """获取板块资金流向 Top（主力净流入排名）"""
    url = ("https://push2.eastmoney.com/api/qt/clist/get"
           "?pn=1&pz=" + str(limit) + "&po=1&np=1&fltt=2&invt=2&fid=f62"
           "&fs=m:90+t:2&fields=f12,f14,f2,f3,f62,f184")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        items = resp.json().get("data", {}).get("diff") or []
        results = []
        for item in items:
            flow = item.get("f62", 0)
            results.append({
                "name": item.get("f14", ""),
                "code": item.get("f12", ""),
                "change_pct": item.get("f3", 0),
                "net_flow": round(flow / 1e8, 1) if flow else 0,  # 亿
            })
        return results
    except Exception as e:
        logger.warning("板块资金流向失败: %s", e)
        return []


def _fetch_stock_flow(limit=10):
    """获取个股主力资金净流入 Top"""
    url = ("https://push2.eastmoney.com/api/qt/clist/get"
           "?pn=1&pz=" + str(limit) + "&po=1&np=1&fltt=2&invt=2&fid=f62"
           "&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f62,f184")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        items = resp.json().get("data", {}).get("diff") or []
        results = []
        for item in items:
            flow = item.get("f62", 0)
            results.append({
                "name": item.get("f14", ""),
                "code": item.get("f12", ""),
                "price": item.get("f2", 0),
                "change_pct": item.get("f3", 0),
                "net_flow": round(flow / 1e8, 1) if flow else 0,  # 亿
            })
        return results
    except Exception as e:
        logger.warning("个股资金流向失败: %s", e)
        return []


def _fetch_stock_flow_bottom(limit=10):
    """获取个股主力资金净流出 Top（反向排序）"""
    url = ("https://push2.eastmoney.com/api/qt/clist/get"
           "?pn=1&pz=" + str(limit) + "&po=0&np=1&fltt=2&invt=2&fid=f62"
           "&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f62,f184")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        items = resp.json().get("data", {}).get("diff") or []
        results = []
        for item in items:
            flow = item.get("f62", 0)
            results.append({
                "name": item.get("f14", ""),
                "code": item.get("f12", ""),
                "price": item.get("f2", 0),
                "change_pct": item.get("f3", 0),
                "net_flow": round(flow / 1e8, 1) if flow else 0,
            })
        return results
    except Exception as e:
        logger.warning("个股资金流出失败: %s", e)
        return []


def _fetch_popularity(limit=10):
    """获取人气榜（东方财富散户关注度排名）"""
    url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
    payload = {
        "appId": "appId01",
        "globalId": "786e4c21-70dc-435a-93bb-38",
        "marketType": "",
        "pageNo": 1,
        "pageSize": limit,
    }
    try:
        resp = requests.post(url, json=payload, headers=_HEADERS, timeout=_TIMEOUT)
        items = resp.json().get("data") or []
        return [{"code": item.get("sc", ""), "rank": item.get("rk", 0)} for item in items]
    except Exception as e:
        logger.warning("人气榜失败: %s", e)
        return []


def _get_yfinance_fallback():
    """yfinance 全球数据兜底（东方财富 API 失败时使用）"""
    import math

    try:
        import yfinance as yf

        tickers = {"^VIX": "VIX", "^GSPC": "S&P 500", "^IXIC": "Nasdaq", "^DJI": "Dow Jones"}
        data = yf.download(list(tickers.keys()), period="220d", progress=False, threads=True)
        close = data.get("Close") if "Close" in data else None
        if close is None or close.empty:
            return None

        def _sf(val, d=0):
            if val is None:
                return d
            try:
                f = float(val)
                return d if math.isnan(f) or math.isinf(f) else f
            except (TypeError, ValueError):
                return d

        # Indices
        indices = []
        for sym, name in tickers.items():
            if sym == "^VIX":
                continue
            col = close.get(sym)
            if col is not None:
                vals = col.dropna()
                if len(vals) >= 2:
                    price = _sf(vals.iloc[-1])
                    prev = _sf(vals.iloc[-2])
                    chg = round((price - prev) / prev * 100, 2) if prev else 0
                    indices.append({"name": name, "price": round(price, 2),
                                    "change_pct": chg, "amount": 0})

        # VIX
        vix, vix_change = 0, 0
        vix_data = close.get("^VIX")
        if vix_data is not None:
            vix_clean = vix_data.dropna()
            if len(vix_clean) >= 2:
                vix = round(_sf(vix_clean.iloc[-1]), 2)
                vix_change = round(vix - _sf(vix_clean.iloc[-2]), 2)

        # S&P vs 200d MA
        sp500_vs_200d = 0
        sp_data = close.get("^GSPC")
        if sp_data is not None:
            sp_clean = sp_data.dropna()
            if len(sp_clean) >= 200:
                current = _sf(sp_clean.iloc[-1])
                ma200 = _sf(sp_clean.tail(200).mean())
                if ma200 > 0:
                    sp500_vs_200d = round((current - ma200) / ma200 * 100, 2)

        # Fear & Greed Score
        score = 50.0
        if vix > 0:
            vix_score = 90 if vix <= 12 else 70 if vix <= 18 else 50 if vix <= 22 else 30 if vix <= 30 else 15 if vix <= 40 else 5
            score = vix_score * 0.4

        ma_score = 85 if sp500_vs_200d > 10 else 70 if sp500_vs_200d > 5 else 55 if sp500_vs_200d > 0 else 35 if sp500_vs_200d > -5 else 15
        score += ma_score * 0.3

        if sp_data is not None:
            sp_clean = sp_data.dropna()
            if len(sp_clean) >= 6:
                ret5 = (_sf(sp_clean.iloc[-1]) - _sf(sp_clean.iloc[-6])) / _sf(sp_clean.iloc[-6]) * 100
                mom_score = 85 if ret5 > 3 else 65 if ret5 > 1 else 50 if ret5 > -1 else 30 if ret5 > -3 else 10
                score += mom_score * 0.3

        score = max(0, min(100, round(score)))

        if score >= 75:
            mood, mood_color = "Extreme Greed", "#00C853"
        elif score >= 55:
            mood, mood_color = "Greed", "#69F0AE"
        elif score >= 45:
            mood, mood_color = "Neutral", "#C9A962"
        elif score >= 25:
            mood, mood_color = "Fear", "#FF9800"
        else:
            mood, mood_color = "Extreme Fear", "#F44336"

        return {
            "indices": indices,
            "total_amount_yi": 0,
            "northbound": {"hgt": 0, "sgt": 0, "total": 0},
            "northbound_yi": 0,
            "fear_greed_score": score,
            "mood": mood,
            "mood_color": mood_color,
            "sh_change": 0,
            "vix": vix,
            "vix_change": vix_change,
            "sp500_vs_200d": sp500_vs_200d,
            "sector_flow": [],
            "stock_flow_in": [],
            "stock_flow_out": [],
            "popularity": [],
            "_source": "yfinance",
        }
    except Exception as e:
        logger.warning("yfinance sentiment fallback failed: %s", e)
        return None


def get_market_sentiment():
    """获取市场情绪综合数据

    优先东方财富 A 股数据，失败时降级到 yfinance 全球数据。
    """
    cached = _read_cache()
    if cached:
        return cached

    # 尝试东方财富 A 股数据
    try:
        indices = _fetch_indices()
        if not indices:
            raise ValueError("No index data")

        northbound = _fetch_northbound()
        total_amount = sum(idx.get("amount", 0) for idx in indices)
        total_amount_yi = round(total_amount / 1e8, 1)
        north_total = northbound.get("total", 0)
        northbound_yi = round(north_total / 1e8, 1) if north_total else 0
        sh_change = indices[0]["change_pct"] if indices else 0

        score = _calc_fear_greed(sh_change, total_amount_yi, northbound_yi)
        mood, mood_color = _mood_label(score)

        sector_flow = _fetch_sector_flow(10)
        stock_flow_in = _fetch_stock_flow(10)
        stock_flow_out = _fetch_stock_flow_bottom(10)
        popularity = _fetch_popularity(10)

        result = {
            "indices": indices,
            "total_amount_yi": total_amount_yi,
            "northbound": northbound,
            "northbound_yi": northbound_yi,
            "fear_greed_score": score,
            "mood": mood,
            "mood_color": mood_color,
            "sh_change": sh_change,
            "sector_flow": sector_flow,
            "stock_flow_in": stock_flow_in,
            "stock_flow_out": stock_flow_out,
            "popularity": popularity,
            "_source": "eastmoney",
        }
        _write_cache(result)
        return result

    except Exception as e:
        logger.warning("Eastmoney sentiment failed, trying yfinance: %s", e)

    # 降级到 yfinance
    fallback = _get_yfinance_fallback()
    if fallback:
        _write_cache(fallback)
        return fallback

    # 全部失败
    return {
        "fear_greed_score": 50, "mood": "Unknown", "mood_color": "#5A5A6A",
        "indices": [], "total_amount_yi": 0, "northbound_yi": 0,
        "northbound": {"hgt": 0, "sgt": 0, "total": 0},
        "sh_change": 0, "sector_flow": [], "stock_flow_in": [],
        "stock_flow_out": [], "popularity": [],
        "_error": "All data sources failed",
    }
