"""Personal Dashboard — Market Pulse · Watchlist · Journal"""

import datetime
import json
import logging
import streamlit as st
import streamlit.components.v1 as components
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.ui_theme import get_global_css, COLORS
from src.auth import get_current_user
from src.user_data import (
    load_watchlist, add_to_watchlist, remove_from_watchlist,
    load_journal, save_journal_entry, save_all_journal,
)
from src.tracker import load_user_analysis_history

logger = logging.getLogger(__name__)

# ── Session defaults ──────────────────────────────────────────────────────────
if "config" not in st.session_state:
    from src.config import load_config
    st.session_state.config = load_config()
config = st.session_state.config

user = get_current_user()
_uid = (user or {}).get("username", "anonymous")


def _detect_market(symbol: str) -> str:
    s = symbol.lower()
    if s.startswith("sh") or s.startswith("sz") or s.endswith(".ss") or s.endswith(".sz"):
        return "a_share"
    if s.endswith(".hk"):
        return "hk"
    return "us"


def _flat_watchlist(wl_dict: dict) -> list:
    result = []
    for market in ("us", "hk", "a_share"):
        for item in wl_dict.get(market, []):
            result.append({"symbol": item["symbol"], "name": item.get("name", item["symbol"]), "market": market})
    return result


# Load per-user data
if "user_watchlist_loaded" not in st.session_state or st.session_state.get("_last_uid") != _uid:
    raw_wl = load_watchlist(_uid)
    if not any(raw_wl.values()):
        config_wl = st.session_state.config.watchlist
        raw_wl = {
            "us": [{"symbol": s.symbol, "name": s.name} for s in config_wl.us],
            "hk": [{"symbol": s.symbol, "name": s.name} for s in config_wl.hk],
            "a_share": [{"symbol": s.symbol, "name": s.name} for s in config_wl.a_share],
        }
    st.session_state.user_watchlist = raw_wl
    st.session_state.dashboard_stocks = _flat_watchlist(raw_wl)
    st.session_state.user_watchlist_loaded = True
    st.session_state._last_uid = _uid

if "journal_loaded" not in st.session_state or st.session_state.get("_journal_uid") != _uid:
    st.session_state.journal_entries = load_journal(_uid)
    st.session_state.journal_loaded = True
    st.session_state._journal_uid = _uid
elif "journal_entries" not in st.session_state:
    st.session_state.journal_entries = []

# ── Load MOAT scores from analysis history (flywheel) ─────────────────────────
if "analysis_scores" not in st.session_state or st.session_state.get("_scores_uid") != _uid:
    _hist = load_user_analysis_history(_uid, limit=200)
    # Keep only most recent record per symbol:market
    _scores = {}
    for _r in reversed(_hist):  # oldest first so latest overwrites
        _k = "{}:{}".format(_r.get("market", ""), _r.get("symbol", ""))
        _scores[_k] = {
            "score": _r.get("score_total", 0),
            "grade": _r.get("grade", ""),
            "verdict": _r.get("verdict", ""),
        }
    st.session_state.analysis_scores = _scores
    st.session_state._scores_uid = _uid

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(get_global_css(), unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
display_name = (user or {}).get("name", "Investor")

components.html(f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:28px 0 8px}}
.greeting{{font-size:0.55rem;letter-spacing:4px;color:#C9A962;text-transform:uppercase;margin-bottom:6px}}
.title{{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.8rem;font-weight:300;color:#E8E8F0;letter-spacing:3px;text-transform:uppercase}}
.title b{{font-weight:700;color:#C9A962}}
.divider{{height:1px;background:linear-gradient(90deg,transparent,#C9A962 30%,transparent);margin-top:18px;opacity:0.3}}
</style></head><body>
<div class="greeting">Welcome back, {display_name}</div>
<div class="title">Command <b>Center</b></div>
<div class="divider"></div>
</body></html>
""", height=100, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — MARKET PULSE (real-time indices via yfinance)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_market_pulse():
    """获取全球市场关键指标"""
    try:
        import yfinance as yf
        tickers = {
            "S&P 500": "^GSPC",
            "VIX": "^VIX",
            "US 10Y": "^TNX",
            "Nasdaq": "^IXIC",
            "Shanghai": "000001.SS",
        }
        results = {}
        data = yf.download(list(tickers.values()), period="2d", progress=False, threads=True)
        close = data.get("Close") if "Close" in data else None
        if close is not None and not close.empty:
            for label, sym in tickers.items():
                try:
                    if sym in close.columns and len(close[sym].dropna()) >= 2:
                        vals = close[sym].dropna()
                        current = float(vals.iloc[-1])
                        prev = float(vals.iloc[-2])
                        chg = (current - prev) / prev * 100 if prev else 0
                        results[label] = {"value": current, "change": round(chg, 2)}
                except Exception:
                    pass
        return results
    except Exception as e:
        logger.warning("Market pulse failed: %s", e)
        return {}


pulse = _fetch_market_pulse()

if pulse:
    def _pulse_card(label, data):
        val = data["value"]
        chg = data["change"]
        chg_color = "#00C853" if chg >= 0 else "#F44336"
        arrow = "&#x25B2;" if chg >= 0 else "&#x25BC;"
        # Format value
        if label == "US 10Y":
            val_fmt = "{:.2f}%".format(val)
        elif val >= 10000:
            val_fmt = "{:,.0f}".format(val)
        else:
            val_fmt = "{:,.1f}".format(val)
        return '''<div class="pulse-card">
            <div class="pulse-label">{label}</div>
            <div class="pulse-value">{val}</div>
            <div class="pulse-change" style="color:{color}">{arrow} {chg:+.2f}%</div>
        </div>'''.format(label=label, val=val_fmt, color=chg_color, arrow=arrow, chg=chg)

    cards = "".join(_pulse_card(k, v) for k, v in pulse.items())

    components.html('''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:12px 0 0}}
.pulse-header{{font-size:0.5rem;letter-spacing:5px;color:#C9A962;text-transform:uppercase;margin-bottom:12px}}
.pulse-grid{{display:flex;gap:10px;flex-wrap:wrap}}
.pulse-card{{
    flex:1;min-width:120px;
    background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;
    padding:14px 16px;text-align:center;
}}
.pulse-label{{font-size:0.5rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:8px}}
.pulse-value{{font-size:1.2rem;font-weight:600;color:#E8E8F0;margin-bottom:4px}}
.pulse-change{{font-size:0.7rem;font-weight:600;letter-spacing:0.5px}}
</style></head><body>
<div class="pulse-header">Market Pulse</div>
<div class="pulse-grid">{cards}</div>
</body></html>'''.format(cards=cards), height=130, scrolling=False)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — WATCHLIST (live prices + grades)
# ══════════════════════════════════════════════════════════════════════════════

components.html('''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:8px 0 4px}
.sec-label{font-size:0.5rem;letter-spacing:5px;color:#C9A962;text-transform:uppercase}
.sec-title{font-size:1.1rem;font-weight:600;color:#E8E8F0;letter-spacing:1px;margin-top:2px}
</style></head><body>
<div class="sec-label">Portfolio Intelligence</div>
<div class="sec-title">My Watchlist</div>
</body></html>''', height=48, scrolling=False)

# Add/remove controls
wl_c1, wl_c2, wl_c3 = st.columns([3, 1, 1])
with wl_c1:
    new_ticker = st.text_input("Add", placeholder="e.g. MSFT, 0700.HK, sh600519",
                                key="wl_new", label_visibility="collapsed")
with wl_c2:
    if st.button("Add", key="wl_add", use_container_width=True):
        t = new_ticker.strip().upper()
        if t:
            mkt = _detect_market(t)
            add_to_watchlist(_uid, mkt, t, t)
            st.session_state.dashboard_stocks.append({"symbol": t, "name": t, "market": mkt})
            st.session_state.user_watchlist.setdefault(mkt, []).append({"symbol": t, "name": t})
            st.rerun()
with wl_c3:
    symbols_for_remove = [s["symbol"] for s in st.session_state.dashboard_stocks]
    rm = st.selectbox("Remove", ["--"] + symbols_for_remove, key="wl_rm", label_visibility="collapsed")
    if rm != "--":
        mkt = _detect_market(rm)
        remove_from_watchlist(_uid, mkt, rm)
        st.session_state.dashboard_stocks = [s for s in st.session_state.dashboard_stocks if s["symbol"] != rm]
        wl = st.session_state.user_watchlist
        if mkt in wl:
            wl[mkt] = [s for s in wl[mkt] if s["symbol"] != rm]
        st.rerun()


# Fetch live data for watchlist
@st.cache_data(ttl=300, show_spinner=False)
def _fetch_watchlist_data(stocks_json: str):
    """批量获取关注列表实时行情 + 评级"""
    from src.data.price import fetch_quote
    stocks = json.loads(stocks_json)
    results = []

    def _fetch_one(item):
        try:
            q = fetch_quote(item["symbol"], item["market"])
            return {
                "symbol": item["symbol"],
                "name": item["name"],
                "market": item["market"],
                "price": q.get("price", 0),
                "change_pct": q.get("change_pct", 0),
                "pe": q.get("pe", 0),
                "pb": q.get("pb", 0),
                "market_cap": q.get("market_cap", 0),
                "52w_high": q.get("52w_high", 0),
                "52w_low": q.get("52w_low", 0),
            }
        except Exception:
            return {"symbol": item["symbol"], "name": item["name"], "market": item["market"],
                    "price": 0, "change_pct": 0}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_fetch_one, s): s for s in stocks}
        for f in as_completed(futures):
            results.append(f.result())
    return results


stocks_list = st.session_state.dashboard_stocks
wl_data = []
if stocks_list:
    with st.spinner("Loading live data..."):
        wl_data = _fetch_watchlist_data(json.dumps(stocks_list))

    # Sort by change_pct descending
    wl_data.sort(key=lambda x: x.get("change_pct", 0), reverse=True)

    # Build market tab groups
    us_stocks = [s for s in wl_data if s["market"] == "us"]
    hk_stocks = [s for s in wl_data if s["market"] == "hk"]
    a_stocks = [s for s in wl_data if s["market"] == "a_share"]

    def _render_stock_table(stocks, currency="$"):
        if not stocks:
            st.caption("No stocks in this market.")
            return
        scores = st.session_state.get("analysis_scores", {})
        rows_html = ""
        for s in stocks:
            price = s.get("price", 0)
            chg = s.get("change_pct", 0)
            pe = s.get("pe", 0)
            cap = s.get("market_cap", 0)
            chg_color = "#00C853" if chg >= 0 else "#F44336"
            arrow = "&#x25B2;" if chg >= 0 else "&#x25BC;"

            # Price format
            if price >= 1000:
                price_fmt = "{}{:,.0f}".format(currency, price)
            elif price >= 1:
                price_fmt = "{}{:,.2f}".format(currency, price)
            else:
                price_fmt = "{}{:.4f}".format(currency, price)

            # Market cap format
            if cap >= 1e12:
                cap_fmt = "{:.1f}T".format(cap / 1e12)
            elif cap >= 1e9:
                cap_fmt = "{:.1f}B".format(cap / 1e9)
            elif cap >= 1e6:
                cap_fmt = "{:.0f}M".format(cap / 1e6)
            else:
                cap_fmt = "--"

            pe_fmt = "{:.1f}".format(pe) if pe and pe > 0 else "--"

            # MOAT score from flywheel
            _score_key = "{}:{}".format(s["market"], s["symbol"])
            _score_data = scores.get(_score_key)
            if _score_data:
                _sc = _score_data["score"]
                if _sc >= 80:
                    _sc_color = "#3ECF8E"
                elif _sc >= 60:
                    _sc_color = "#C9A962"
                else:
                    _sc_color = "#EF4444"
                _verdict = _score_data.get("verdict", "")
                _score_html = (
                    '<span style="font-weight:700;color:{c};">{sc:.0f}</span>'
                    '<span style="font-size:0.55rem;color:#5A5A6A;margin-left:3px;">{v}</span>'
                ).format(c=_sc_color, sc=_sc, v=_verdict[:4] if _verdict else "")
            else:
                _score_html = '<span style="color:#2A2A36;font-size:0.6rem;">—</span>'

            rows_html += '''<tr>
                <td class="sym">{sym}</td>
                <td class="name">{name}</td>
                <td class="price">{price}</td>
                <td class="chg" style="color:{chg_color}">{arrow} {chg:+.2f}%</td>
                <td class="score">{score}</td>
                <td class="pe">{pe}</td>
                <td class="cap">{cap}</td>
            </tr>'''.format(sym=s["symbol"], name=s["name"][:14],
                           price=price_fmt, chg_color=chg_color, arrow=arrow,
                           chg=chg, score=_score_html, pe=pe_fmt, cap=cap_fmt)

        components.html('''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:4px 0 0}}
table{{width:100%;border-collapse:collapse}}
th{{
    font-size:0.5rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;
    text-align:left;padding:8px 10px;border-bottom:1px solid #1A1A22;font-weight:500;
}}
th:nth-child(n+3){{text-align:right}}
td{{
    padding:10px 10px;border-bottom:1px solid #0F0F18;
    font-size:0.75rem;color:#AAAABC;
}}
td:nth-child(n+3){{text-align:right}}
tr:hover{{background:#0F0F18}}
.sym{{color:#C9A962;font-weight:600;letter-spacing:1px}}
.name{{color:#6A6A80;font-size:0.65rem}}
.price{{color:#E8E8F0;font-weight:500}}
.chg{{font-weight:600;letter-spacing:0.5px}}
.score{{white-space:nowrap}}
.pe{{color:#6A6A80}}
.cap{{color:#6A6A80;font-size:0.65rem}}
</style></head><body>
<table>
<tr><th>Symbol</th><th>Name</th><th>Price</th><th>Change</th><th>MOAT</th><th>PE</th><th>Mkt Cap</th></tr>
{rows}
</table>
</body></html>'''.format(rows=rows_html), height=max(60, len(stocks) * 42 + 40), scrolling=False)

    wl_tabs = []
    wl_tab_data = []
    if us_stocks:
        wl_tabs.append("US ({})".format(len(us_stocks)))
        wl_tab_data.append(("$", us_stocks))
    if hk_stocks:
        wl_tabs.append("HK ({})".format(len(hk_stocks)))
        wl_tab_data.append(("HK$", hk_stocks))
    if a_stocks:
        wl_tabs.append("A-Share ({})".format(len(a_stocks)))
        wl_tab_data.append(("¥", a_stocks))

    if wl_tabs:
        tabs = st.tabs(wl_tabs)
        for tab, (cur, data) in zip(tabs, wl_tab_data):
            with tab:
                _render_stock_table(data, cur)
else:
    st.caption("No stocks in watchlist. Add tickers above.")

st.markdown("<div style='height:16px;border-top:1px solid #1A1A22;margin-top:16px'></div>",
            unsafe_allow_html=True)

# ── 分析提醒：关注列表中超过30天未分析的股票 ──────────────────────────────
if stocks_list:
    _scores_map = st.session_state.get("analysis_scores", {})
    _now_ts = datetime.datetime.now(datetime.timezone.utc)
    _stale = []
    for _s in stocks_list:
        _k = "{}:{}".format(_s["market"], _s["symbol"])
        if _k not in _scores_map:
            _stale.append(_s["symbol"])
    if _stale:
        _stale_str = "、".join(_stale[:5])
        if len(_stale) > 5:
            _stale_str += " 等{}只".format(len(_stale))
        st.markdown(
            '<div style="background:#0C0C12;border:1px solid #2A1A00;border-left:3px solid #C9A962;'
            'padding:10px 16px;margin:12px 0;font-size:0.78rem;color:#8A7A5A;">'
            '💡 <b style="color:#C9A962;">{}只股票</b> 尚未运行分析（{}）— '
            '前往 <b>Analysis</b> 页面获取 AI 评分和投资结论。'
            '</div>'.format(len(_stale), _stale_str),
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — AI WEEKLY REPORT
# ══════════════════════════════════════════════════════════════════════════════

components.html('''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:8px 0 4px}
.sec-label{font-size:0.5rem;letter-spacing:5px;color:#C9A962;text-transform:uppercase}
.sec-title{font-size:1.1rem;font-weight:600;color:#E8E8F0;letter-spacing:1px;margin-top:2px}
</style></head><body>
<div class="sec-label">AI Intelligence</div>
<div class="sec-title">Weekly Market Report</div>
</body></html>''', height=48, scrolling=False)


def _build_report_context():
    """收集周报所需数据"""
    # Market data from yfinance
    market_lines = []
    if pulse:
        for name, d in pulse.items():
            market_lines.append("{}: {:.2f} ({:+.2f}%)".format(name, d["value"], d["change"]))
    market_data = "\n".join(market_lines) if market_lines else "Market data unavailable"

    # Watchlist summary
    wl_lines = []
    if stocks_list:
        try:
            for s in wl_data[:15]:
                chg = s.get("change_pct", 0)
                wl_lines.append("{} ({}): price {:.2f}, change {:+.2f}%, PE {}".format(
                    s["symbol"], s["name"][:12], s.get("price", 0), chg,
                    "{:.1f}".format(s["pe"]) if s.get("pe") else "N/A"))
        except Exception:
            pass
    watchlist_summary = "\n".join(wl_lines) if wl_lines else "No watchlist data"

    # Buffett indicator
    try:
        from src.data.macro import get_macro_overview
        macro = get_macro_overview()
        bi_us = macro.get("buffett_indicator_pct")
        bi_cn = macro.get("cn_buffett_pct")
        bi_parts = []
        if bi_us is not None:
            bi_parts.append("US Buffett Indicator: {:.1f}%".format(bi_us))
        if bi_cn is not None:
            bi_parts.append("CN Buffett Indicator: {:.1f}%".format(bi_cn))
        buffett_indicator = "\n".join(bi_parts) if bi_parts else "Not available"
    except Exception:
        buffett_indicator = "Not available"

    return market_data, watchlist_summary, buffett_indicator


report_key = "weekly_report_{}".format(_uid)

if st.button("Generate Weekly Report", key="gen_report", use_container_width=True):
    from src.config import get_premium_provider
    from src.ai.summarizer import generate_weekly_report
    provider = get_premium_provider(config)
    if not provider or not provider.api_key:
        st.warning("Please configure API key in Settings first.")
    else:
        with st.spinner("AI generating weekly report (15-30s)..."):
            market_data, watchlist_summary, buffett_indicator = _build_report_context()
            report = generate_weekly_report(market_data, watchlist_summary,
                                             buffett_indicator, provider)
            st.session_state[report_key] = report

if report_key in st.session_state:
    st.markdown(
        '<div style="background:#0D0D14;border:1px solid #1E1E2A;border-left:3px solid #C9A962;'
        'border-radius:4px;padding:20px 24px;margin:8px 0;line-height:1.8;color:#AAAABC;font-size:0.85rem">',
        unsafe_allow_html=True)
    st.markdown(st.session_state[report_key])
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.caption("Click the button above to generate this week's AI market report.")

st.markdown("<div style='height:16px;border-top:1px solid #1A1A22;margin-top:16px'></div>",
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — INVESTMENT JOURNAL (compact)
# ══════════════════════════════════════════════════════════════════════════════

with st.expander("Investment Journal ({} entries)".format(len(st.session_state.journal_entries)),
                  expanded=False):

    journal_tab1, journal_tab2, journal_tab3 = st.tabs([
        "Decision Log", "Trade Review", "Market Notes"])

    with journal_tab1:
        with st.expander("+ New Decision", expanded=False):
            d_c1, d_c2 = st.columns(2)
            with d_c1:
                d_ticker = st.text_input("Ticker", placeholder="e.g. BRK.B", key="d_ticker")
            with d_c2:
                d_action = st.selectbox("Action", ["Buy", "Sell", "Hold", "Watch"], key="d_action")
            d_thesis = st.text_area("Thesis", placeholder="Why?", height=80, key="d_thesis")
            d_conviction = st.slider("Conviction", 1, 10, 7, key="d_conviction")
            if st.button("Save", key="d_save"):
                if d_ticker.strip():
                    entry = {"type": "decision", "date": str(datetime.date.today()),
                             "ticker": d_ticker.strip().upper(), "action": d_action,
                             "thesis": d_thesis, "conviction": d_conviction}
                    save_journal_entry(_uid, entry)
                    st.session_state.journal_entries.insert(0, entry)
                    st.rerun()

        decisions = [e for e in st.session_state.journal_entries if e.get("type") == "decision"]
        for e in decisions[:10]:
            bar = "█" * e.get("conviction", 5) + "░" * (10 - e.get("conviction", 5))
            st.markdown(
                '<div style="background:#0D0D12;border:1px solid #1E1E26;border-radius:2px;padding:10px 14px;margin-bottom:6px">'
                '<div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:4px">'
                '<span style="color:#C9A962;font-weight:600">{ticker}</span>'
                '<span style="color:#3A3A4A;font-size:0.6rem;letter-spacing:2px">{date} · {action}</span>'
                '</div>'
                '<div style="font-size:0.75rem;color:#AAAABC;line-height:1.5;margin-bottom:4px">{thesis}</div>'
                '<div style="font-size:0.55rem;color:#5A5A6A">CONVICTION <span style="color:#C9A962;font-family:monospace">{bar}</span> {c}/10</div>'
                '</div>'.format(ticker=e.get("ticker", "?"), date=e.get("date", ""),
                                action=e.get("action", "").upper(), thesis=e.get("thesis", "—"),
                                bar=bar, c=e.get("conviction", 5)),
                unsafe_allow_html=True)
        if not decisions:
            st.caption("No decisions logged yet.")

    with journal_tab2:
        with st.expander("+ New Trade Review", expanded=False):
            r_c1, r_c2 = st.columns(2)
            with r_c1:
                r_ticker = st.text_input("Ticker", placeholder="e.g. KO", key="r_ticker")
            with r_c2:
                r_outcome = st.selectbox("Outcome", ["Profit", "Loss", "Break-even", "Ongoing"], key="r_outcome")
            r_lesson = st.text_area("Key Lesson", placeholder="What did you learn?", height=80, key="r_lesson")
            if st.button("Save", key="r_save"):
                if r_ticker.strip():
                    entry = {"type": "review", "date": str(datetime.date.today()),
                             "ticker": r_ticker.strip().upper(), "outcome": r_outcome,
                             "lesson": r_lesson}
                    save_journal_entry(_uid, entry)
                    st.session_state.journal_entries.insert(0, entry)
                    st.rerun()

        reviews = [e for e in st.session_state.journal_entries if e.get("type") == "review"]
        oc_color = {"Profit": "#00C853", "Loss": "#F44336", "Break-even": "#FF9800", "Ongoing": "#C9A962"}
        for e in reviews[:10]:
            oc = oc_color.get(e.get("outcome", ""), "#5A5A6A")
            st.markdown(
                '<div style="background:#0D0D12;border:1px solid #1E1E26;border-radius:2px;padding:10px 14px;margin-bottom:6px">'
                '<div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:4px">'
                '<span style="color:#C9A962;font-weight:600">{ticker}</span>'
                '<span style="color:{oc};font-size:0.65rem;font-weight:700">{outcome}</span>'
                '</div>'
                '<div style="font-size:0.75rem;color:#AAAABC;line-height:1.5">{lesson}</div>'
                '</div>'.format(ticker=e.get("ticker", "?"), oc=oc,
                                outcome=e.get("outcome", "").upper(),
                                lesson=e.get("lesson", "—")),
                unsafe_allow_html=True)
        if not reviews:
            st.caption("No reviews yet.")

    with journal_tab3:
        with st.expander("+ New Note", expanded=False):
            n_title = st.text_input("Title", placeholder="Brief description", key="n_title")
            n_body = st.text_area("Analysis", placeholder="What does this signal?", height=80, key="n_body")
            n_impact = st.selectbox("Impact", ["Positive", "Negative", "Neutral", "Monitoring"], key="n_impact")
            if st.button("Save", key="n_save"):
                if n_title.strip():
                    entry = {"type": "note", "date": str(datetime.date.today()),
                             "title": n_title.strip(), "body": n_body, "impact": n_impact}
                    save_journal_entry(_uid, entry)
                    st.session_state.journal_entries.insert(0, entry)
                    st.rerun()

        notes = [e for e in st.session_state.journal_entries if e.get("type") == "note"]
        ic_color = {"Positive": "#00C853", "Negative": "#F44336", "Neutral": "#5A5A6A", "Monitoring": "#FF9800"}
        for e in notes[:10]:
            ic = ic_color.get(e.get("impact", ""), "#5A5A6A")
            st.markdown(
                '<div style="background:#0D0D12;border:1px solid #1E1E26;border-radius:2px;padding:10px 14px;margin-bottom:6px">'
                '<div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:4px">'
                '<span style="color:#E8E8F0;font-weight:600">{title}</span>'
                '<span style="color:{ic};font-size:0.6rem;font-weight:700;letter-spacing:1px">{impact}</span>'
                '</div>'
                '<div style="font-size:0.6rem;color:#3A3A4A;letter-spacing:2px;margin-bottom:4px">{date}</div>'
                '<div style="font-size:0.75rem;color:#AAAABC;line-height:1.5">{body}</div>'
                '</div>'.format(title=e.get("title", "?"), ic=ic,
                                impact=e.get("impact", "").upper(),
                                date=e.get("date", ""), body=e.get("body", "—")),
                unsafe_allow_html=True)
        if not notes:
            st.caption("No notes yet.")

    # Export / Import / Clear
    st.markdown("---")
    ex_c, im_c, cl_c = st.columns(3)
    with ex_c:
        entries = st.session_state.journal_entries
        if entries:
            st.download_button("Export JSON", json.dumps(entries, ensure_ascii=False, indent=2),
                               "journal_{}.json".format(datetime.date.today()), "application/json",
                               use_container_width=True)
    with im_c:
        uploaded = st.file_uploader("Import", type=["json"], key="j_import", label_visibility="collapsed")
        if uploaded:
            try:
                imported = json.loads(uploaded.read().decode("utf-8"))
                if isinstance(imported, list):
                    save_all_journal(_uid, imported)
                    st.session_state.journal_entries = imported
                    st.rerun()
            except Exception as e:
                st.error(str(e))
    with cl_c:
        if st.button("Clear All", use_container_width=True, key="j_clear"):
            if st.session_state.get("_confirm_clear"):
                save_all_journal(_uid, [])
                st.session_state.journal_entries = []
                st.session_state._confirm_clear = False
                st.rerun()
            else:
                st.session_state._confirm_clear = True
                st.warning("Click again to confirm.")
