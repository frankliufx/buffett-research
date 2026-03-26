"""财务数据获取 — 基本面数据（腾讯行情 + 新浪财务指标 + 东方财富美股港股）"""

import json
import logging
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# ── 本地文件缓存（加速启动，减少重复请求）──────────────────────────────
_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
_FUNDAMENTALS_CACHE_TTL = 6 * 3600  # 基本面 6 小时
_QUOTE_CACHE_TTL = 300              # 行情 5 分钟


def _cache_key(prefix: str, symbol: str, market: str) -> Path:
    safe_sym = symbol.replace("/", "_").replace(".", "_")
    return _CACHE_DIR / "{}_{}_{}.json".format(prefix, market, safe_sym)


def _read_cache(path: Path, ttl: int):
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if time.time() - data.get("_ts", 0) < ttl:
                data.pop("_ts", None)
                return data
    except Exception:
        pass
    return None


def _write_cache(path: Path, data: dict):
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        to_save = dict(data)
        to_save["_ts"] = time.time()
        path.write_text(json.dumps(to_save, ensure_ascii=False, default=str))
    except Exception:
        pass

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

_SINA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn",
}

_REQUEST_TIMEOUT = 10
_MAX_RETRIES = 2


def _fetch_with_retry(url: str, headers: dict = None, params: dict = None,
                      encoding: str = None) -> requests.Response:
    """带指数退避重试的 HTTP GET（最多重试 _MAX_RETRIES 次）"""
    last_err = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url,
                headers=headers or _HEADERS,
                params=params,
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            if attempt < _MAX_RETRIES:
                time.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s
                logger.debug("Retry %d/%d for %s: %s", attempt + 1, _MAX_RETRIES, url[:80], e)
    raise last_err


def _safe_float(val, default=None):
    """安全转换为 float，处理 '-'、None、NaN、空字符串"""
    if val is None:
        return default
    try:
        s = str(val).strip()
        if s in ("", "-", "--", "N/A", "—"):
            return default
        result = float(s)
        if math.isnan(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _extract_sina_stock_id(symbol: str) -> str:
    """从 A 股符号中提取纯数字 stock ID: sh600519 -> 600519"""
    s = symbol.lower()
    if s.startswith("sh") or s.startswith("sz"):
        return s[2:]
    return s


def _parse_sina_financial_table(html: str) -> dict:
    """解析新浪财务指标页面 HTML，提取关键财务数据

    Returns dict with raw percentage values as strings (e.g., "36.99" means 36.99%)
    """
    result = {}

    try:
        # Use regex to find table data instead of requiring lxml/beautifulsoup
        # The financial guideline page has tables with specific field names

        # Helper: find value next to a label in the HTML table
        def find_value(label):
            """Find the numeric value associated with a label in HTML tables"""
            # Pattern: <td>label</td><td>value</td> or similar variations
            patterns = [
                rf'{re.escape(label)}</(?:td|a)>\s*</td>\s*<td[^>]*>\s*([^<]+?)\s*</td>',
                rf'{re.escape(label)}\s*</(?:td|a|span)>\s*</td>\s*<td[^>]*>\s*<[^>]*>\s*([^<]+?)\s*</',
                rf'{re.escape(label)}[^<]*</[^>]+>\s*</td>\s*<td[^>]*>\s*([^<]+?)\s*</td>',
            ]
            for pattern in patterns:
                m = re.search(pattern, html, re.DOTALL)
                if m:
                    val = m.group(1).strip()
                    if val and val not in ("--", "-", ""):
                        return val
            return None

        # Extract key financial indicators
        # These are returned as percentage strings from Sina, e.g. "36.99" = 36.99%
        result["roe"] = find_value("加权净资产收益率(%)")
        if result["roe"] is None:
            result["roe"] = find_value("净资产收益率(%)")

        result["profit_margin"] = find_value("销售净利率(%)")
        result["operating_margin"] = find_value("营业利润率(%)")
        result["gross_margin"] = find_value("销售毛利率(%)")
        result["debt_ratio"] = find_value("资产负债率(%)")  # 资产负债率, not D/E directly
        result["current_ratio"] = find_value("流动比率")
        result["quick_ratio"] = find_value("速动比率")
        result["cashflow_per_share"] = find_value("每股经营性现金流(元)")

    except Exception as e:
        logger.debug("Sina financial table parsing error: %s", e)

    return result


def _fetch_sina_fundamentals(stock_id: str, year: int = None) -> dict:
    if year is None:
        from datetime import datetime
        year = datetime.now().year
    """从新浪财经获取 A 股财务指标数据"""
    url = (f"https://money.finance.sina.com.cn/corp/go.php/vFD_FinancialGuideLine/"
           f"stockid/{stock_id}/ctrl/{year}/displaytype/4.phtml")
    try:
        resp = _fetch_with_retry(url, headers=_SINA_HEADERS)
        html = resp.content.decode("gbk", errors="replace")
        return _parse_sina_financial_table(html)
    except Exception as e:
        logger.warning("Sina fundamentals fetch failed for %s year %d: %s", stock_id, year, e)
        return {}


def _fetch_roe_history(stock_id: str, years: list = None) -> list:
    """并发获取多年 ROE 数据用于一致性检查（ThreadPoolExecutor 加速）

    Returns list of ROE values in percentage form (e.g., [15.2, 16.3, 14.8])
    matching the format that _normalize_fundamentals expects (already %).
    """
    if years is None:
        years = [2024, 2023, 2022, 2021, 2020]

    def _fetch_one(year: int):
        try:
            data = _fetch_sina_fundamentals(stock_id, year)
            roe_str = data.get("roe")
            if roe_str is not None:
                roe_val = _safe_float(roe_str)
                if roe_val is not None:
                    return year, round(roe_val, 2)
        except Exception as e:
            logger.debug("ROE history fetch failed for year %d: %s", year, e)
        return year, None

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_one, y): y for y in years}
        for future in as_completed(futures):
            year, val = future.result()
            if val is not None:
                results[year] = val

    # 保持年份降序排列
    return [results[y] for y in sorted(results.keys(), reverse=True)]


# ── yfinance 美股基本面数据 ─────────────────────────────────────────────

def _fetch_yfinance_fundamentals(symbol: str) -> dict:
    """使用 yfinance 获取美股基本面数据

    数据格式与 fetch_fundamentals 的 contract 保持一致:
    - roe, profit_margin, gross_margin: decimal (0.15 = 15%)
    - debt_to_equity: yfinance 原始格式 (D/E * 100, e.g. 102.63)
    - roe_history: percentage 列表 (e.g. [15.2, 16.3])
    - free_cashflow: 绝对值（正数 = 好）
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        result = {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "data_source": "yfinance",
            # Valuation
            "pe_trailing": _safe_float(info.get("trailingPE")),
            "pe_forward": _safe_float(info.get("forwardPE")),
            "pb": _safe_float(info.get("priceToBook")),
            "ps": _safe_float(info.get("priceToSalesTrailing12Months")),
            "ev_ebitda": _safe_float(info.get("enterpriseToEbitda")),
            # Profitability (decimals: 0.15 = 15%)
            "roe": _safe_float(info.get("returnOnEquity")),
            "roa": _safe_float(info.get("returnOnAssets")),
            "profit_margin": _safe_float(info.get("profitMargins")),
            "operating_margin": _safe_float(info.get("operatingMargins")),
            "gross_margin": _safe_float(info.get("grossMargins")),
            # Growth (decimals)
            "revenue_growth": _safe_float(info.get("revenueGrowth")),
            "earnings_growth": _safe_float(info.get("earningsGrowth")),
            # Financial health
            "debt_to_equity": _safe_float(info.get("debtToEquity")),  # already D/E*100
            "current_ratio": _safe_float(info.get("currentRatio")),
            "quick_ratio": _safe_float(info.get("quickRatio")),
            # Dividend
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "payout_ratio": _safe_float(info.get("payoutRatio")),
            "dividend_rate": _safe_float(info.get("dividendRate")),
            # Cash flow
            "free_cashflow": _safe_float(info.get("freeCashflow")),
            "operating_cashflow": _safe_float(info.get("operatingCashflow")),
            # Scale
            "market_cap": _safe_float(info.get("marketCap")),
            "enterprise_value": _safe_float(info.get("enterpriseValue")),
            "total_revenue": _safe_float(info.get("totalRevenue")),
            # Price range
            "52w_high": _safe_float(info.get("fiftyTwoWeekHigh")),
            "52w_low": _safe_float(info.get("fiftyTwoWeekLow")),
            # Analyst targets
            "target_mean_price": _safe_float(info.get("targetMeanPrice")),
            # History
            "roe_history": [],
            "revenue_history": [],
        }

        # Build ROE history from financials (annual)
        try:
            financials = ticker.financials  # income statement, columns = dates
            balance = ticker.balance_sheet
            if financials is not None and not financials.empty and \
               balance is not None and not balance.empty:
                roe_list = []
                for col in financials.columns[:5]:  # up to 5 years
                    try:
                        net_income = financials.loc["Net Income", col] if "Net Income" in financials.index else None
                        equity_row = None
                        for eq_key in ("Stockholders Equity", "Total Stockholders Equity",
                                       "Common Stock Equity"):
                            if eq_key in balance.index:
                                equity_row = balance.loc[eq_key, col]
                                break
                        if net_income and equity_row and equity_row > 0:
                            roe_val = round(float(net_income) / float(equity_row) * 100, 2)
                            roe_list.append(roe_val)
                    except Exception:
                        continue
                if roe_list:
                    result["roe_history"] = roe_list
        except Exception as e:
            logger.debug("yfinance ROE history failed for %s: %s", symbol, e)

        return result

    except Exception as e:
        logger.warning("yfinance fundamentals failed for %s: %s", symbol, e)
        return {}


# ── 东方财富美股/港股基本面数据 ────────────────────────────────────────

_EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://emweb.securities.eastmoney.com",
}

# 美股交易所映射表（symbol -> 东方财富 SECUCODE 后缀: .O=纳斯达克, .N=纽交所, .A=美交所）
# 内置已知映射（启动快），运行时自动学习并持久化到缓存文件
_US_EXCHANGE_MAP_BUILTIN = {
    # 纳斯达克
    "AAPL": "O", "MSFT": "O", "GOOGL": "O", "AMZN": "O", "META": "O",
    "NVDA": "O", "TSLA": "O", "WMT": "O",
    # 纽交所
    "BRK-B": "N", "KO": "N", "V": "N", "JPM": "N", "JNJ": "N",
}

_EXCHANGE_CACHE_FILE = _CACHE_DIR / "us_exchange_map.json"
_us_exchange_runtime: dict = {}  # 运行时内存缓存（避免重复读文件）


def _load_exchange_map() -> dict:
    """从持久化文件加载已学习的交易所映射"""
    global _us_exchange_runtime
    if _us_exchange_runtime:
        return _us_exchange_runtime
    result = dict(_US_EXCHANGE_MAP_BUILTIN)
    try:
        if _EXCHANGE_CACHE_FILE.exists():
            learned = json.loads(_EXCHANGE_CACHE_FILE.read_text())
            result.update(learned)
    except Exception:
        pass
    _us_exchange_runtime = result
    return result


def _save_exchange_suffix(symbol: str, suffix: str):
    """将成功确认的交易所后缀持久化，供后续请求直接使用"""
    global _us_exchange_runtime
    _us_exchange_runtime[symbol] = suffix
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        existing = {}
        if _EXCHANGE_CACHE_FILE.exists():
            existing = json.loads(_EXCHANGE_CACHE_FILE.read_text())
        existing[symbol] = suffix
        _EXCHANGE_CACHE_FILE.write_text(json.dumps(existing, ensure_ascii=False))
    except Exception:
        pass


def _to_eastmoney_secucode(symbol: str, market: str) -> str:
    """将内部 symbol 转换为东方财富 SECUCODE 格式

    美股: AAPL -> AAPL.O, BRK-B -> BRK.B.N (dash→dot for secucode)
    港股: 0700.HK -> 00700.HK
    """
    if market == "us":
        base = symbol.replace("-", ".")
        exchange_map = _load_exchange_map()
        suffix = exchange_map.get(symbol, "O")  # 默认猜测纳斯达克
        return "{}.{}".format(base, suffix)
    elif market == "hk":
        code = symbol.replace(".HK", "").replace(".hk", "")
        return "{}.HK".format(code.zfill(5))
    return symbol


def _fetch_eastmoney_fundamentals(symbol: str, market: str) -> dict:
    """从东方财富获取美股/港股基本面数据

    Returns dict with percentage values as-is from API:
    - ROE_AVG: e.g., 51.99 means 51.99%
    - GROSS_PROFIT_RATIO: e.g., 48.16 means 48.16%
    - All percentage fields are already in "XX.XX" format = XX.XX%
    """
    secucode = _to_eastmoney_secucode(symbol, market)

    if market == "us":
        report_name = "RPT_USF10_FN_GMAININDICATOR"
        columns = ("SECUCODE,SECURITY_NAME_ABBR,REPORT_DATE,"
                   "ROE_AVG,GROSS_PROFIT_RATIO,NET_PROFIT_RATIO,"
                   "DEBT_ASSET_RATIO,CURRENT_RATIO,SPEED_RATIO,"
                   "OPERATE_INCOME_YOY,PARENT_HOLDER_NETPROFIT_YOY,"
                   "OPERATE_INCOME,NETCASH_OPERATE,FREE_CASH_FLOW")
    elif market == "hk":
        report_name = "RPT_HKF10_FN_MAININDICATOR"
        columns = ("SECUCODE,SECURITY_NAME_ABBR,REPORT_DATE,"
                   "ROE_AVG,GROSS_PROFIT_RATIO,NET_PROFIT_RATIO,"
                   "DEBT_ASSET_RATIO,CURRENT_RATIO,"
                   "OPERATE_INCOME_YOY,HOLDER_PROFIT_YOY,"
                   "OPERATE_INCOME,NETCASH_OPERATE")
    else:
        return {}

    url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    params = {
        "reportName": report_name,
        "columns": columns,
        "filter": '(SECUCODE="{}")'.format(secucode),
        "pageSize": 5,
        "sortColumns": "REPORT_DATE",
        "sortTypes": -1,
        "source": "SECURITIES",
        "client": "PC",
    }

    try:
        resp = _fetch_with_retry(url, headers=_EASTMONEY_HEADERS, params=params)
        data = resp.json()
        rows = (data.get("result") or {}).get("data") or []
        if not rows:
            # 美股：交易所猜错了，换一个试
            if market == "us":
                alt_suffix = "N" if secucode.endswith(".O") else "O"
                alt_code = secucode.rsplit(".", 1)[0] + "." + alt_suffix
                params["filter"] = '(SECUCODE="{}")'.format(alt_code)
                resp = _fetch_with_retry(url, headers=_EASTMONEY_HEADERS, params=params)
                data = resp.json()
                rows = (data.get("result") or {}).get("data") or []
                if rows:
                    # 学习到正确的交易所后缀，持久化避免下次二次请求
                    _save_exchange_suffix(symbol, alt_suffix)
            if not rows:
                return {}

        return rows[0]  # 最新一期

    except Exception as e:
        logger.warning("Eastmoney fundamentals failed for %s (%s): %s", symbol, market, e)
        return {}


def _fetch_eastmoney_roe_history(symbol: str, market: str) -> list:
    """获取多年 ROE 历史（东方财富美股/港股）

    Returns list of ROE percentage values, e.g. [51.99, 48.2, ...]
    """
    secucode = _to_eastmoney_secucode(symbol, market)

    if market == "us":
        report_name = "RPT_USF10_FN_GMAININDICATOR"
    elif market == "hk":
        report_name = "RPT_HKF10_FN_MAININDICATOR"
    else:
        return []

    url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    params = {
        "reportName": report_name,
        "columns": "SECUCODE,REPORT_DATE,ROE_AVG",
        "filter": '(SECUCODE="{}")'.format(secucode),
        "pageSize": 20,
        "sortColumns": "REPORT_DATE",
        "sortTypes": -1,
        "source": "SECURITIES",
        "client": "PC",
    }

    try:
        resp = _fetch_with_retry(url, headers=_EASTMONEY_HEADERS, params=params)
        data = resp.json()
        rows = (data.get("result") or {}).get("data") or []

        if not rows and market == "us":
            alt_suffix = "N" if secucode.endswith(".O") else "O"
            alt_code = secucode.rsplit(".", 1)[0] + "." + alt_suffix
            params["filter"] = '(SECUCODE="{}")'.format(alt_code)
            resp = _fetch_with_retry(url, headers=_EASTMONEY_HEADERS, params=params)
            data = resp.json()
            rows = (data.get("result") or {}).get("data") or []
            if rows:
                _save_exchange_suffix(symbol, alt_suffix)

        # 取年报数据（每年一条），最多5年
        seen_years = set()
        roe_history = []
        for row in rows:
            roe = _safe_float(row.get("ROE_AVG"))
            report_date = str(row.get("REPORT_DATE", ""))
            year = report_date[:4] if report_date else ""
            if roe is not None and year and year not in seen_years:
                seen_years.add(year)
                roe_history.append(round(roe, 2))
                if len(roe_history) >= 5:
                    break

        return roe_history

    except Exception as e:
        logger.debug("Eastmoney ROE history failed for %s: %s", symbol, e)
        return []


def _fetch_tencent_quote_data(symbol: str, market: str) -> dict:
    """从腾讯行情获取基础估值数据 (PE, PB, market_cap)"""
    from src.data.price import _to_tencent_symbol, _parse_tencent_quote

    try:
        from src.data.price import _fetch_with_retry
        tencent_sym = _to_tencent_symbol(symbol, market)
        url = f"https://qt.gtimg.cn/q={tencent_sym}"
        resp = _fetch_with_retry(url)
        text = resp.content.decode("gbk", errors="replace")
        return _parse_tencent_quote(text, market)
    except Exception as e:
        logger.warning("Tencent quote fetch failed for %s: %s", symbol, e)
        return {}


def fetch_fundamentals(symbol: str, market: str) -> dict:
    """统一入口：获取基本面数据（带本地文件缓存，6小时TTL）

    Data format contract (must match what _normalize_fundamentals expects):
    - roe, profit_margin, operating_margin, gross_margin: DECIMAL form (0.15 = 15%)
      because _normalize_fundamentals multiplies by 100
    - debt_to_equity: yfinance-compatible format (percentage * 100, e.g., 102.63)
      because _normalize_fundamentals divides by 100 to get ratio
    - current_ratio, quick_ratio: raw ratio values (no conversion needed)
    - roe_history: list of percentage numbers (e.g., [15.2, 16.3])
      because _normalize_fundamentals only cleans NaN, doesn't multiply
    - pe_trailing, pb: raw values
    - free_cashflow: raw number (positive = good)
    """
    # 本地缓存优先
    cache_path = _cache_key("fund", symbol, market)
    cached = _read_cache(cache_path, _FUNDAMENTALS_CACHE_TTL)
    if cached:
        return cached

    try:
        # ── 美股: 直接使用 yfinance（数据更全、更准确）──────────────────
        if market == "us":
            result = _fetch_yfinance_fundamentals(symbol)
            if result:
                _write_cache(cache_path, result)
                return result
            # yfinance 失败时降级到 Tencent+EastMoney
            logger.warning("yfinance failed for %s, falling back to eastmoney", symbol)

        # Get basic quote data from Tencent (works for HK/A-share)
        quote_data = _fetch_tencent_quote_data(symbol, market)

        result = {
            "symbol": symbol,
            "name": quote_data.get("name", symbol),
            "sector": "",
            "industry": "",
            "data_source": "tencent+sina" if market == "a_share" else "tencent",
            # Valuation from Tencent quote
            "pe_trailing": _safe_float(quote_data.get("pe")),
            "pe_forward": None,
            "pb": _safe_float(quote_data.get("pb")),
            "ps": None,
            "ev_ebitda": None,
            # Defaults for profitability (will be overridden below)
            "roe": None,
            "roa": None,
            "profit_margin": None,
            "operating_margin": None,
            "gross_margin": None,
            # Growth
            "revenue_growth": None,
            "earnings_growth": None,
            # Financial health defaults
            "debt_to_equity": None,
            "current_ratio": None,
            "quick_ratio": None,
            # Dividend
            "dividend_yield": None,
            "payout_ratio": None,
            "dividend_rate": None,
            # Cash flow
            "free_cashflow": None,
            "operating_cashflow": None,
            # Scale
            "market_cap": _safe_float(quote_data.get("market_cap")),
            "enterprise_value": None,
            "total_revenue": None,
            # History
            "roe_history": [],
            "revenue_history": [],
        }

        # For US (fallback) / HK: enrich with Eastmoney financial data
        if market in ("us", "hk"):
            em_data = _fetch_eastmoney_fundamentals(symbol, market)
            if em_data:
                result["data_source"] = "tencent+eastmoney"

                roe = _safe_float(em_data.get("ROE_AVG"))
                if roe is not None:
                    result["roe"] = roe / 100.0

                gm = _safe_float(em_data.get("GROSS_PROFIT_RATIO"))
                if gm is not None:
                    result["gross_margin"] = gm / 100.0

                nm = _safe_float(em_data.get("NET_PROFIT_RATIO"))
                if nm is not None:
                    result["profit_margin"] = nm / 100.0

                dar = _safe_float(em_data.get("DEBT_ASSET_RATIO"))
                if dar is not None and 0 < dar < 100:
                    debt_ratio = dar / 100.0
                    de_ratio = debt_ratio / (1.0 - debt_ratio)
                    result["debt_to_equity"] = de_ratio * 100

                cr = _safe_float(em_data.get("CURRENT_RATIO"))
                if cr is not None:
                    result["current_ratio"] = cr

                qr = _safe_float(em_data.get("SPEED_RATIO"))
                if qr is not None:
                    result["quick_ratio"] = qr

                rg = _safe_float(em_data.get("OPERATE_INCOME_YOY"))
                if rg is not None:
                    result["revenue_growth"] = rg / 100.0

                eg_key = "PARENT_HOLDER_NETPROFIT_YOY" if market == "us" else "HOLDER_PROFIT_YOY"
                eg = _safe_float(em_data.get(eg_key))
                if eg is not None:
                    result["earnings_growth"] = eg / 100.0

                ocf = _safe_float(em_data.get("NETCASH_OPERATE"))
                if ocf is not None and ocf != 0:
                    result["operating_cashflow"] = ocf
                    result["free_cashflow"] = ocf

                if market == "us":
                    fcf = _safe_float(em_data.get("FREE_CASH_FLOW"))
                    if fcf is not None and fcf != 0:
                        result["free_cashflow"] = fcf

                rev = _safe_float(em_data.get("OPERATE_INCOME"))
                if rev is not None:
                    result["total_revenue"] = rev

            roe_history = _fetch_eastmoney_roe_history(symbol, market)
            if roe_history:
                result["roe_history"] = roe_history

        # For A-share: enrich with Sina financial data
        if market == "a_share":
            stock_id = _extract_sina_stock_id(symbol)

            # Get current year financial data
            sina_data = _fetch_sina_fundamentals(stock_id)

            if sina_data:
                # Convert Sina percentages to decimals for _normalize_fundamentals
                # Sina: "36.99" means 36.99%, we store as 0.3699
                roe_raw = _safe_float(sina_data.get("roe"))
                if roe_raw is not None:
                    result["roe"] = roe_raw / 100.0  # 36.99 -> 0.3699

                pm_raw = _safe_float(sina_data.get("profit_margin"))
                if pm_raw is not None:
                    result["profit_margin"] = pm_raw / 100.0

                om_raw = _safe_float(sina_data.get("operating_margin"))
                if om_raw is not None:
                    result["operating_margin"] = om_raw / 100.0

                gm_raw = _safe_float(sina_data.get("gross_margin"))
                if gm_raw is not None:
                    result["gross_margin"] = gm_raw / 100.0

                # Current ratio and quick ratio: raw values (no conversion)
                cr = _safe_float(sina_data.get("current_ratio"))
                if cr is not None:
                    result["current_ratio"] = cr

                qr = _safe_float(sina_data.get("quick_ratio"))
                if qr is not None:
                    result["quick_ratio"] = qr

                # Debt to equity: compute from 资产负债率
                # 资产负债率 = Total Debt / Total Assets * 100
                # D/E = Debt / Equity = debt_ratio / (1 - debt_ratio)
                # yfinance returns debtToEquity as D/E * 100 (e.g., 102.63)
                # _normalize_fundamentals divides by 100 to get ratio
                debt_ratio_pct = _safe_float(sina_data.get("debt_ratio"))
                if debt_ratio_pct is not None and debt_ratio_pct < 100:
                    debt_ratio = debt_ratio_pct / 100.0  # e.g., 45.5% -> 0.455
                    if debt_ratio < 1.0:
                        de_ratio = debt_ratio / (1.0 - debt_ratio)  # D/E ratio
                        result["debt_to_equity"] = de_ratio * 100  # yfinance format

                # Free cashflow: approximate from per-share cashflow
                # We don't have total shares easily, but store per-share value
                # The analysis only checks if fcf > 0
                cashflow_ps = _safe_float(sina_data.get("cashflow_per_share"))
                if cashflow_ps is not None:
                    # Use per-share value; sign is what matters for scoring
                    # Multiply by a large number to make it look like total FCF
                    # (the analysis only checks positive/negative)
                    result["free_cashflow"] = cashflow_ps * 1e8  # rough proxy

            # Get multi-year ROE history (percentage numbers)
            roe_history = _fetch_roe_history(stock_id)
            result["roe_history"] = roe_history

        # 写入本地缓存
        _write_cache(cache_path, result)
        return result

    except Exception as e:
        logger.error("fetch_fundamentals failed for %s: %s", symbol, e)
        return {
            "symbol": symbol,
            "name": symbol,
            "data_source": "error",
            "roe_history": [],
            "revenue_history": [],
        }
