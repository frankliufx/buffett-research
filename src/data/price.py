"""股价数据获取 — 支持美股（yfinance）、港股、A股（腾讯财经 API）"""

import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

# 新增：Tushare 行情适配器（可选依赖，失败时静默降级）
try:
    from src.data.adapters import TushareAdapter as _TushareAdapterCls
    _tushare_price = _TushareAdapterCls()
except ImportError:
    _tushare_price = None

# ── 本地 K 线缓存 ─────────────────────────────────────────────────
_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
_KLINE_CACHE_TTL = 4 * 3600  # K 线 4 小时缓存

logger = logging.getLogger(__name__)

# Cache for US stock exchange suffixes (needed for K-line API)
_exchange_suffix_cache: dict = {}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

_REQUEST_TIMEOUT = 20
_MAX_RETRIES = 2


def _safe_float(val, default=0.0):
    """安全转换为 float，处理 '-'、None、NaN、空字符串"""
    if val is None:
        return default
    try:
        s = str(val).strip()
        if s in ("", "-", "--", "N/A"):
            return default
        result = float(s)
        if result != result:  # NaN check
            return default
        return result
    except (TypeError, ValueError):
        return default


def _a_share_prefix(symbol: str) -> str:
    """为 A 股代码添加交易所前缀（如未携带）

    规则：6 开头 -> sh（上交所），0/3 开头 -> sz（深交所）
    已携带前缀（sh/sz/SH/SZ）时原样返回。
    """
    s = symbol.lower()
    if s.startswith(("sh", "sz")):
        return s
    if s.startswith("6"):
        return f"sh{s}"
    return f"sz{s}"


def _to_tencent_symbol(symbol: str, market: str) -> str:
    """将内部符号格式转换为腾讯行情 API 符号格式

    - A-share: 600519 -> sh600519, 000858 -> sz000858
    - US: AAPL -> usAAPL, BRK-B -> usBRK.B
    - HK: 0700.HK -> hk00700
    """
    if market == "a_share":
        return _a_share_prefix(symbol)
    elif market == "hk":
        # 0700.HK -> hk00700
        code = symbol.replace(".HK", "").replace(".hk", "")
        return f"hk{code.zfill(5)}"
    else:
        # US market: AAPL -> usAAPL, BRK-B -> usBRK.B
        us_sym = symbol.replace("-", ".")
        return f"us{us_sym}"


def _get_kline_symbol(symbol: str, market: str) -> str:
    """将内部符号格式转换为腾讯 K 线 API 符号格式

    - A-share: 600519 -> sh600519, 000858 -> sz000858
    - HK: 0700.HK -> hk00700
    - US: AAPL -> usAAPL.OQ (需要交易所后缀)
          BRK-B -> usBRK.B.N
    """
    if market == "a_share":
        return _a_share_prefix(symbol)
    elif market == "hk":
        code = symbol.replace(".HK", "").replace(".hk", "")
        return f"hk{code.zfill(5)}"
    else:
        # US: need exchange suffix from quote API
        us_sym = symbol.replace("-", ".")
        suffix = _get_us_exchange_suffix(symbol)
        if suffix:
            return f"us{us_sym}.{suffix}"
        # Fallback: try common suffixes
        return f"us{us_sym}.OQ"


def _get_us_exchange_suffix(symbol: str) -> str:
    """获取美股交易所后缀（从腾讯行情 API 的 code 字段提取）

    例如: AAPL -> quote field[2] = "AAPL.OQ" -> suffix = "OQ"
          BRK-B -> quote field[2] = "BRK.B.N" -> suffix = "N"
    """
    if symbol in _exchange_suffix_cache:
        return _exchange_suffix_cache[symbol]

    try:
        tencent_sym = _to_tencent_symbol(symbol, "us")
        url = f"https://qt.gtimg.cn/q={tencent_sym}"
        resp = _fetch_with_retry(url)
        text = resp.content.decode("gbk", errors="replace")

        # Parse response: v_usAAPL="...~...~AAPL.OQ~...";
        match = re.search(r'="([^"]*)"', text)
        if match:
            fields = match.group(1).split("~")
            if len(fields) > 2:
                code_field = fields[2]  # e.g., "AAPL.OQ" or "BRK.B.N"
                # Extract suffix: last part after the last dot that is 1-3 uppercase letters
                parts = code_field.split(".")
                if len(parts) >= 2:
                    suffix = parts[-1]
                    if suffix.isalpha() and len(suffix) <= 3:
                        _exchange_suffix_cache[symbol] = suffix
                        return suffix
    except Exception as e:
        logger.debug("Failed to get exchange suffix for %s: %s", symbol, e)

    return ""


def _parse_tencent_quote(text: str, market: str) -> dict:
    """解析腾讯行情 API 返回的数据"""
    match = re.search(r'="([^"]*)"', text)
    if not match:
        return {}

    data = match.group(1)
    if not data or data.strip() == "":
        return {}

    fields = data.split("~")
    if len(fields) < 40:
        return {}

    def _f(idx, default=0.0):
        return _safe_float(fields[idx], default) if len(fields) > idx else default

    if market == "us":
        # US field mapping (腾讯美股行情字段):
        # [3]=price [4]=prev_close [5]=open [6]=volume
        # [32]=change_pct [33]=high [34]=low [37]=amount [38]=turnover
        # [39]=PE [44]=market_cap(亿)
        # PB field varies by exchange:
        #   NASDAQ (.OQ): [47]=PB, [48]=52w_high, [49]=52w_low, [52]=div_yield
        #   NYSE (.N):    [51]=PB, [48]=52w_high, [49]=52w_low, [64]=div_yield
        code_field = fields[2] if len(fields) > 2 else ""
        exchange = code_field.split(".")[-1] if "." in code_field else ""
        # Determine PB field by exchange
        if exchange == "N":  # NYSE
            pb = _f(51)
            div_yield = _f(64)
        else:  # NASDAQ (.OQ) and others
            pb = _f(47)
            div_yield = _f(52)
        return {
            "name": fields[1] if len(fields) > 1 else "",
            "code": code_field,
            "exchange": exchange,
            "price": _f(3),
            "prev_close": _f(4),
            "open": _f(5),
            "volume": _f(6),
            "change_pct": _f(32),
            "high": _f(33),
            "low": _f(34),
            "amount": _f(37),
            "turnover": _f(38),
            "pe": _f(39),
            "market_cap": _f(44) * 1e8,  # 亿 -> 元
            "pb": pb,
            "52w_high": _f(48),
            "52w_low": _f(49),
            "dividend_yield": div_yield,
        }
    elif market == "hk":
        # HK field mapping:
        # [3]=price [4]=prev_close [5]=open [6]=volume
        # [31]=change [32]=change_pct [33]=high [34]=low
        # [39]=PE [44]=market_cap(亿) [47]=div_yield [48]=52w_high [49]=52w_low [50]=PB
        return {
            "name": fields[1] if len(fields) > 1 else "",
            "code": fields[2] if len(fields) > 2 else "",
            "price": _f(3),
            "prev_close": _f(4),
            "open": _f(5),
            "volume": _f(6),
            "change": _f(31),
            "change_pct": _f(32),
            "high": _f(33),
            "low": _f(34),
            "pe": _f(39),
            "market_cap": _f(44) * 1e8,  # 亿HKD -> HKD
            "dividend_yield": _f(47),
            "52w_high": _f(48),
            "52w_low": _f(49),
            "pb": _f(50),
        }
    else:
        # A-share field mapping:
        # [3]=price [4]=prev_close [5]=open [6]=volume
        # [31]=change [32]=change_pct [33]=today_high [34]=today_low
        # [37]=amount(万) [38]=turnover [39]=PE [44]=market_cap(亿) [45]=total_cap(亿)
        # [46]=PB [47]=52w_high [48]=52w_low
        return {
            "name": fields[1] if len(fields) > 1 else "",
            "code": fields[2] if len(fields) > 2 else "",
            "price": _f(3),
            "prev_close": _f(4),
            "open": _f(5),
            "volume": _f(6),
            "datetime": fields[30] if len(fields) > 30 else "",
            "change": _f(31),
            "change_pct": _f(32),
            "high": _f(33),
            "low": _f(34),
            "amount": _f(37),
            "turnover": _f(38),
            "pe": _f(39),
            "market_cap": _f(44) * 1e8,  # 亿 -> 元
            "total_cap": _f(45) * 1e8,
            "pb": _f(46),
            "52w_high": _f(47),
            "52w_low": _f(48),
        }


def _fetch_with_retry(url: str, **kwargs) -> requests.Response:
    """带重试的 HTTP 请求"""
    last_err = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT, **kwargs)
        except Exception as e:
            last_err = e
            if attempt < _MAX_RETRIES:
                import time
                time.sleep(1)
                logger.debug("Retry %d for %s", attempt + 1, url[:80])
    raise last_err


def _fetch_yfinance_quote(symbol: str) -> dict:
    """使用 yfinance 获取美股实时报价"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        prev_close = _safe_float(info.get("previousClose") or info.get("regularMarketPreviousClose"))
        open_ = _safe_float(info.get("open") or info.get("regularMarketOpen"))
        high = _safe_float(info.get("dayHigh") or info.get("regularMarketDayHigh"))
        low = _safe_float(info.get("dayLow") or info.get("regularMarketDayLow"))
        volume = _safe_float(info.get("volume") or info.get("regularMarketVolume"))
        market_cap = _safe_float(info.get("marketCap"))
        pe = _safe_float(info.get("trailingPE"))
        pb = _safe_float(info.get("priceToBook"))
        div_yield = _safe_float(info.get("dividendYield"))
        if div_yield:
            div_yield = round(div_yield * 100, 4)  # decimal -> percentage display
        w52_high = _safe_float(info.get("fiftyTwoWeekHigh"))
        w52_low = _safe_float(info.get("fiftyTwoWeekLow"))

        change_pct = 0.0
        if price and prev_close and prev_close > 0:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        return {
            "price": price,
            "prev_close": prev_close,
            "open": open_,
            "high": high,
            "low": low,
            "volume": volume,
            "market_cap": market_cap,
            "pe": pe,
            "pb": pb,
            "dividend_yield": div_yield,
            "52w_high": w52_high,
            "52w_low": w52_low,
            "change_pct": change_pct,
        }
    except Exception as e:
        logger.error("yfinance quote failed for %s: %s", symbol, e)
        return {}


def _fetch_yfinance_history(symbol: str, days: int = 250) -> pd.DataFrame:
    """使用 yfinance 获取美股历史 K 线数据"""
    try:
        import yfinance as yf
        # Use period or start date depending on days requested
        if days <= 365:
            period = "1y"
        elif days <= 730:
            period = "2y"
        else:
            period = "5y"

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()

        df.index = pd.to_datetime(df.index)
        df.index.name = "Date"
        # Ensure standard column names
        df = df.rename(columns={
            "Open": "Open", "High": "High", "Low": "Low",
            "Close": "Close", "Volume": "Volume",
        })
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]
        # Trim to requested days
        if len(df) > days:
            df = df.iloc[-days:]
        return df
    except Exception as e:
        logger.error("yfinance history failed for %s: %s", symbol, e)
        return pd.DataFrame()


def fetch_quote(symbol: str, market: str) -> dict:
    """统一入口：获取实时报价

    美股使用 yfinance，港股/A股使用腾讯财经 API。
    Returns dict with: price, prev_close, open, high, low, volume,
                       market_cap, pe, pb, dividend_yield, 52w_high, 52w_low, change_pct
    """
    if market == "us":
        return _fetch_yfinance_quote(symbol)

    try:
        tencent_sym = _to_tencent_symbol(symbol, market)
        url = f"https://qt.gtimg.cn/q={tencent_sym}"
        resp = _fetch_with_retry(url)
        text = resp.content.decode("gbk", errors="replace")

        raw = _parse_tencent_quote(text, market)
        if not raw:
            logger.warning("Empty quote data for %s", symbol)
            return {}

        price = raw.get("price", 0)
        prev_close = raw.get("prev_close", 0)

        # 计算涨跌幅 (use API value if available, fallback to calculation)
        change_pct = raw.get("change_pct", 0.0)
        if change_pct == 0.0 and price and prev_close and prev_close > 0:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        return {
            "price": price,
            "prev_close": prev_close,
            "open": raw.get("open", 0),
            "high": raw.get("high", 0),
            "low": raw.get("low", 0),
            "volume": raw.get("volume", 0),
            "market_cap": raw.get("market_cap", 0),
            "pe": raw.get("pe", 0),
            "pb": raw.get("pb", 0),
            "dividend_yield": raw.get("dividend_yield", 0),
            "52w_high": raw.get("52w_high", 0),
            "52w_low": raw.get("52w_low", 0),
            "change_pct": change_pct,
        }
    except Exception as e:
        logger.warning("Tencent quote failed for %s, trying yfinance fallback: %s", symbol, e)
        # 降级：港股/A股用 yfinance 兜底
        yf_sym = _to_yfinance_symbol(symbol, market)
        if yf_sym:
            return _fetch_yfinance_quote(yf_sym)
        return {}


def _to_yfinance_symbol(symbol: str, market: str) -> str:
    """将内部符号转换为 yfinance 格式（用于港股/A股降级）"""
    if market == "hk":
        # 0700.HK -> 0700.HK (yfinance 直接支持)
        return symbol if ".HK" in symbol.upper() else symbol + ".HK"
    elif market == "a_share":
        # sh600519 -> 600519.SS, sz000858 -> 000858.SZ
        s = symbol.lower()
        if s.startswith("sh"):
            return s[2:] + ".SS"
        elif s.startswith("sz"):
            return s[2:] + ".SZ"
    return ""


def fetch_history(symbol: str, market: str, days: int = 250) -> pd.DataFrame:
    """统一入口：获取历史 K 线数据（带本地文件缓存）

    美股使用 yfinance，港股/A股使用腾讯财经 API。
    Returns pd.DataFrame with columns: Open, High, Low, Close, Volume
    Index: DatetimeIndex named 'Date'
    """
    if market == "us":
        # 本地缓存
        safe_sym = symbol.replace("/", "_").replace(".", "_")
        cache_path = _CACHE_DIR / "kline_{}_{}.json".format(market, safe_sym)
        try:
            if cache_path.exists():
                cached = json.loads(cache_path.read_text())
                if time.time() - cached.get("_ts", 0) < _KLINE_CACHE_TTL:
                    records = cached.get("records", [])
                    if records:
                        df = pd.DataFrame(records)
                        df["Date"] = pd.to_datetime(df["Date"])
                        df = df.set_index("Date").sort_index()
                        return df
        except Exception:
            pass

        df = _fetch_yfinance_history(symbol, days)
        if not df.empty:
            try:
                _CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache_records = df.reset_index().to_dict("records")
                for r in cache_records:
                    r["Date"] = str(r["Date"])
                cache_path.write_text(json.dumps({"_ts": time.time(), "records": cache_records}))
            except Exception:
                pass
        return df

    # 本地缓存
    safe_sym = symbol.replace("/", "_").replace(".", "_")
    cache_path = _CACHE_DIR / "kline_{}_{}.json".format(market, safe_sym)
    try:
        if cache_path.exists():
            cached = json.loads(cache_path.read_text())
            if time.time() - cached.get("_ts", 0) < _KLINE_CACHE_TTL:
                records = cached.get("records", [])
                if records:
                    df = pd.DataFrame(records)
                    df["Date"] = pd.to_datetime(df["Date"])
                    df = df.set_index("Date").sort_index()
                    return df
    except Exception:
        pass

    # ── Tushare 优先（A 股 K 线，更稳定）────────────────────────────
    if market == "a_share" and _tushare_price:
        try:
            ts_df = _tushare_price.get_a_share_history(symbol, days=days)
            if ts_df is not None and not ts_df.empty and "date" in ts_df.columns and "close" in ts_df.columns:
                logger.debug("fetch_history: using Tushare for %s", symbol)
                try:
                    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    cache_records = ts_df.reset_index().to_dict("records")
                    for r in cache_records:
                        r["Date"] = str(r.get("Date", r.get("date", "")))
                    cache_path.write_text(json.dumps({"_ts": time.time(), "records": cache_records}))
                except Exception:
                    pass
                return ts_df
        except Exception as e:
            logger.debug("Tushare history failed for %s, falling back: %s", symbol, e)
    # ── /Tushare 优先 ─────────────────────────────────────────────────

    try:
        kline_sym = _get_kline_symbol(symbol, market)

        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days + 30)).strftime("%Y-%m-%d")

        # Tencent K-line API returns max 300 days per call
        # For more than 300 days, we need multiple calls
        all_rows = []
        remaining = days
        current_end = end_date

        while remaining > 0:
            batch = min(remaining, 300)
            url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            params = {
                "param": f"{kline_sym},day,{start_date},{current_end},{batch},qfq"
            }

            resp = _fetch_with_retry(url, params=params)
            data = resp.json()

            if "data" not in data:
                break

            # Find the kline data in response
            sym_data = data["data"]
            # The key might be the symbol itself
            kline_data = None
            for key in sym_data:
                if key in ("qfqday", "day"):
                    kline_data = sym_data[key]
                    break
                elif isinstance(sym_data[key], dict):
                    kline_data = sym_data[key].get("qfqday") or sym_data[key].get("day")
                    if kline_data:
                        break

            if not kline_data:
                break

            all_rows.extend(kline_data)

            if len(kline_data) < batch:
                break  # No more data available

            # Move end date back for next batch
            remaining -= len(kline_data)
            if kline_data:
                current_end = kline_data[0][0]  # Earliest date in this batch
                # Subtract one day
                try:
                    dt = datetime.strptime(current_end, "%Y-%m-%d")
                    current_end = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
                except Exception:
                    break

        if not all_rows:
            logger.warning("No K-line data for %s", symbol)
            return pd.DataFrame()

        # Parse rows: [date, open, close, high, low, volume]
        records = []
        for row in all_rows:
            if len(row) < 6:
                continue
            try:
                records.append({
                    "Date": pd.Timestamp(row[0]),
                    "Open": float(row[1]),
                    "Close": float(row[2]),
                    "High": float(row[3]),
                    "Low": float(row[4]),
                    "Volume": float(row[5]),
                })
            except (ValueError, TypeError):
                continue

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df = df.set_index("Date")
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]

        # 写入本地缓存
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_records = df.reset_index().to_dict("records")
            for r in cache_records:
                r["Date"] = str(r["Date"])
            cache_path.write_text(json.dumps({"_ts": time.time(), "records": cache_records}))
        except Exception:
            pass

        return df

    except Exception as e:
        logger.warning("Tencent history failed for %s, trying yfinance fallback: %s", symbol, e)
        # 降级：港股/A股用 yfinance 兜底
        yf_sym = _to_yfinance_symbol(symbol, market)
        if yf_sym:
            return _fetch_yfinance_history(yf_sym, days)
        return pd.DataFrame()
