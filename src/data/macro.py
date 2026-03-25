"""宏观数据 — 巴菲特指标（证券化率）

巴菲特指标 = 股市总市值 / GDP × 100%
用于判断整体市场估值水位，是巴菲特推崇的市场泡沫衡量标尺。
"""

import json
import logging
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 5
_MAX_RETRIES = 2


def _urlopen_with_retry(req) -> bytes:
    """带重试的 urllib 请求，返回响应体字节"""
    last_err = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            if attempt < _MAX_RETRIES:
                time.sleep(0.5 * (2 ** attempt))
                logger.debug("Macro retry %d/%d: %s", attempt + 1, _MAX_RETRIES, e)
    raise last_err

# ── GDP 数据（最新年度，手动更新）───────────────────────────────
# 来源：国家统计局 / BEA / 香港统计处
GDP_DATA = {
    "cn": {
        "value": 134.91,        # 万亿 CNY
        "unit": "万亿",
        "year": 2024,
        "source": "国家统计局",
    },
    "us": {
        "value": 29.22,         # 万亿 USD
        "unit": "万亿美元",
        "year": 2024,
        "source": "BEA (美国经济分析局)",
    },
    "hk": {
        "value": 3.04,           # 万亿 HKD
        "unit": "万亿港元",
        "year": 2024,
        "source": "香港统计处",
    },
}

# ── 备用总市值（API 获取失败时使用）─────────────────────────────
FALLBACK_MARKET_CAP = {
    "cn": {"value": 88.0, "unit": "万亿", "date": "2025-03"},
    "us": {"value": 56.0, "unit": "万亿美元", "date": "2025-03"},
    "hk": {"value": 38.0, "unit": "万亿港元", "date": "2025-03"},  # 港交所全市场约35-40万亿港元
}

# ── 估值判断标准 ──────────────────────────────────────────────
VALUATION_BANDS = [
    # (上限, 标签, 描述, 投资建议, 颜色)
    (70,  "严重低估", "市场处于底部区域",     "适合分批布局、加仓",       "#3ECF8E"),
    (90,  "合理偏低", "估值温和，安全边际高",  "坚定持有，适度建仓",       "#60A5FA"),
    (120, "合理区间", "估值中性，市场平稳",    "均衡配置，观望为主",       "#C9A962"),
    (150, "偏高估值", "存在泡沫风险",         "减仓避险，控制仓位",       "#F5A623"),
    (999, "严重高估", "泡沫极大，风险极高",    "清仓离场，规避大跌风险",   "#EF4444"),
]


def get_valuation(ratio: float) -> dict:
    """根据比值返回估值判断"""
    for threshold, label, desc, advice, color in VALUATION_BANDS:
        if ratio < threshold:
            return {"label": label, "desc": desc, "advice": advice, "color": color}
    last = VALUATION_BANDS[-1]
    return {"label": last[1], "desc": last[2], "advice": last[3], "color": last[4]}


def _fetch_cn_market_cap():
    """尝试从东方财富获取 A 股总市值（沪 + 深，单位：万亿 CNY）

    使用东方财富 ulist 接口获取上证指数(1.000001)和深证成指(0.399106)的 f20 字段。
    f20 = 总市值（元），需转换为万亿。
    """
    try:
        url = (
            "https://push2.eastmoney.com/api/qt/ulist.np/get"
            "?fltt=2&fields=f14,f20"
            "&secids=1.000001,0.399106"
        )
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.eastmoney.com/",
        })
        data = json.loads(_urlopen_with_retry(req).decode())

        items = data.get("data", {}).get("diff", [])
        if not items:
            return None

        total = 0
        for item in items:
            cap = item.get("f20")
            if cap and isinstance(cap, (int, float)) and cap > 0:
                total += cap

        if total > 0:
            return round(total / 1e12, 2)   # 元 → 万亿
    except Exception as e:
        logger.warning("获取 A 股总市值失败: %s", e)
    return None


def _fetch_hk_market_cap():
    """尝试获取港股总市值（单位：万亿 HKD）

    从腾讯行情获取恒生指数(hkHSI)的总市值字段。
    恒生指数覆盖约80%港股市值，乘以系数估算全市场。
    """
    try:
        url = "https://qt.gtimg.cn/q=hkHSI"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
        })
        text = _urlopen_with_retry(req).decode("gbk", errors="replace")

        import re
        match = re.search(r'="([^"]*)"', text)
        if match:
            fields = match.group(1).split("~")
            # 尝试从不同字段位置获取总市值
            # 恒指行情的 f44 位通常是总市值（亿港元）
            if len(fields) > 44:
                cap_yi = float(fields[44]) if fields[44] and fields[44] != "0" else 0
                if cap_yi > 0:
                    # 恒指覆盖约 80% 市值，除以 0.8 估算全市场
                    total = cap_yi / 10000 / 0.8  # 亿 → 万亿，再校正
                    if total > 10:  # 合理性检查：港股至少 10 万亿
                        return round(total, 2)
    except Exception as e:
        logger.warning("获取港股总市值失败: %s", e)
    return None


def _fetch_us_market_cap():
    """尝试从 FRED API 获取美股总市值（Wilshire 5000 指数，单位：万亿 USD）

    FRED 的 WILL5000IND 是 Wilshire 5000 全市值指数，
    单位为十亿美元。无需 API key 的公开端点。
    """
    try:
        # FRED 公开 JSON 接口，获取最新的 Wilshire 5000 数据
        url = (
            "https://fred.stlouisfed.org/graph/fredgraph.csv"
            "?id=WILL5000IND&cosd=2025-01-01"
        )
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
        })
        text = _urlopen_with_retry(req).decode()

        # CSV 格式: DATE,WILL5000IND
        lines = text.strip().split("\n")
        for line in reversed(lines):
            if line.startswith("DATE") or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) >= 2 and parts[1] != ".":
                val = float(parts[1])
                # Wilshire 5000 Index Level ≈ 总市值（十亿美元）
                # 将十亿美元转为万亿美元
                cap_trillion = val / 1000
                if cap_trillion > 20:  # 合理性检查
                    return round(cap_trillion, 2)
    except Exception as e:
        logger.warning("获取美股总市值失败 (FRED): %s", e)
    return None


_CACHE_DIR = Path(__file__).parent.parent.parent / "data"
_BI_CACHE_FILE = _CACHE_DIR / "buffett_indicator_cache.json"
_BI_CACHE_TTL = 3600  # 1 小时缓存


def _load_bi_cache():
    """读取本地缓存的巴菲特指标数据"""
    try:
        if _BI_CACHE_FILE.exists():
            with open(_BI_CACHE_FILE) as f:
                cached = json.load(f)
            ts = cached.get("_timestamp", 0)
            if (datetime.now().timestamp() - ts) < _BI_CACHE_TTL:
                cached.pop("_timestamp", None)
                return cached
    except Exception as e:
        logger.debug("BI cache read failed: %s", e)
    return None


def _save_bi_cache(data: dict):
    """保存巴菲特指标到本地缓存"""
    try:
        _CACHE_DIR.mkdir(exist_ok=True)
        to_save = dict(data)
        to_save["_timestamp"] = datetime.now().timestamp()
        with open(_BI_CACHE_FILE, "w") as f:
            json.dump(to_save, f, ensure_ascii=False)
    except Exception as e:
        logger.debug("BI cache write failed: %s", e)


def get_buffett_indicator() -> dict:
    """获取巴菲特指标数据（带本地文件缓存，1小时TTL）

    Returns:
        dict with keys 'cn', 'us', 'hk', each containing:
        - market_cap, gdp, ratio, label, desc, advice, color,
        - name, unit, is_live, updated
    """
    # 优先使用本地缓存（秒级加载）
    cached = _load_bi_cache()
    if cached:
        return cached

    results = {}

    # ── A 股 ──
    live_cap = _fetch_cn_market_cap()
    cn_cap = live_cap if live_cap else FALLBACK_MARKET_CAP["cn"]["value"]
    cn_gdp = GDP_DATA["cn"]["value"]
    cn_ratio = cn_cap / cn_gdp * 100
    val = get_valuation(cn_ratio)
    results["cn"] = {
        "name": "A股",
        "market_cap": cn_cap,
        "gdp": cn_gdp,
        "ratio": round(cn_ratio, 1),
        "unit": "万亿",
        "is_live": live_cap is not None,
        "updated": datetime.now().strftime("%Y-%m-%d") if live_cap else FALLBACK_MARKET_CAP["cn"]["date"],
        "gdp_year": GDP_DATA["cn"]["year"],
        **val,
    }

    # ── 美股 ──
    live_us_cap = _fetch_us_market_cap()
    us_cap = live_us_cap if live_us_cap else FALLBACK_MARKET_CAP["us"]["value"]
    us_gdp = GDP_DATA["us"]["value"]
    us_ratio = us_cap / us_gdp * 100
    val = get_valuation(us_ratio)
    results["us"] = {
        "name": "美股",
        "market_cap": us_cap,
        "gdp": us_gdp,
        "ratio": round(us_ratio, 1),
        "unit": "万亿美元",
        "is_live": live_us_cap is not None,
        "updated": datetime.now().strftime("%Y-%m-%d") if live_us_cap else FALLBACK_MARKET_CAP["us"]["date"],
        "gdp_year": GDP_DATA["us"]["year"],
        **val,
    }

    # ── 港股 ──
    # 注：港股市场高度国际化，大量中国内地企业在港上市，
    # 传统巴菲特指标（市值/本地GDP）不适用。
    # 改用港股市值/中国GDP作为参考，更合理反映估值水位。
    live_hk_cap = _fetch_hk_market_cap()
    hk_cap = live_hk_cap if live_hk_cap else FALLBACK_MARKET_CAP["hk"]["value"]
    # 港股以港元计，中国GDP以人民币计，需汇率转换
    # 1 CNY ≈ 1.07 HKD (近似固定)
    cn_gdp_hkd = GDP_DATA["cn"]["value"] * 1.07  # 万亿CNY → 万亿HKD
    hk_ratio = hk_cap / cn_gdp_hkd * 100
    val = get_valuation(hk_ratio)
    results["hk"] = {
        "name": "港股",
        "market_cap": hk_cap,
        "gdp": round(cn_gdp_hkd, 1),
        "ratio": round(hk_ratio, 1),
        "unit": "万亿港元",
        "is_live": live_hk_cap is not None,
        "updated": datetime.now().strftime("%Y-%m-%d") if live_hk_cap else FALLBACK_MARKET_CAP["hk"]["date"],
        "gdp_year": GDP_DATA["cn"]["year"],
        **val,
    }

    # 缓存到本地文件
    _save_bi_cache(results)

    return results


def format_indicator_summary() -> str:
    """格式化巴菲特指标摘要（供 AI 分析使用）"""
    data = get_buffett_indicator()
    lines = ["## 巴菲特指标（市场整体估值水位）"]
    for key in ("cn", "us", "hk"):
        d = data[key]
        lines.append(
            "- {name}: 总市值 {cap}{unit} / GDP {gdp}{unit} = {ratio}% → {label}（{advice}）".format(
                name=d["name"], cap=d["market_cap"], unit=d["unit"],
                gdp=d["gdp"], ratio=d["ratio"],
                label=d["label"], advice=d["advice"],
            )
        )
    return "\n".join(lines)


def get_macro_overview() -> dict:
    """Flat dict of macro indicators for the Dashboard Market Compass.
    Returns buffett indicator ratios + placeholders for other indicators."""
    try:
        bi = get_buffett_indicator()
    except Exception:
        bi = {}
    return {
        "buffett_indicator_pct": (bi.get("us") or {}).get("ratio"),
        "cn_buffett_pct":        (bi.get("cn") or {}).get("ratio"),
        "hk_buffett_pct":        (bi.get("hk") or {}).get("ratio"),
        "us_buffett_label":      (bi.get("us") or {}).get("label"),
        "cn_buffett_label":      (bi.get("cn") or {}).get("label"),
        "hk_buffett_label":      (bi.get("hk") or {}).get("label"),
        # Additional macro fields (not available from current data sources)
        "sp500": None,
        "sp500_pe": None,
        "vix": None,
        "dxy": None,
        "us_10y_yield": None,
        "cn_10y_yield": None,
        "cn_gdp_growth": None,
    }
