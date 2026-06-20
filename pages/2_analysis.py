"""股票分析页 — A股 / 港股 / 美股 | 高端金融风"""

import logging

import pandas as pd
import streamlit as st

from src.analysis.fundamental import _normalize_fundamentals
from src.analysis.page_orchestrator import (cached_fetch_calendar,
                                             cached_fetch_market_news,
                                             cached_fetch_news, run_analysis)
from src.auth import get_current_user
from src.config import StockItem, get_active_provider, load_config
from src.data.stock_search import search_stocks
from src.ui_analysis import (fmt_pct, format_revenue, inject_css,
                              render_stock_analysis, trend_label)
from src.ui_theme import (COLORS, get_global_css, render_buffett_quote,
                          render_calendar_card, render_empty_state,
                          render_hero_header, render_news_item,
                          render_sidebar_status)
from src.user_data import FREE_MONTHLY_LIMIT, can_analyze, increment_usage

logging.basicConfig(level=logging.WARNING)

# ===== 全局样式 =====
st.markdown(get_global_css(), unsafe_allow_html=True)
inject_css()

# ========================================
# MAIN
# ========================================
if "config" not in st.session_state:
    st.session_state.config = load_config()
config = st.session_state.config

st.markdown(render_hero_header(), unsafe_allow_html=True)
st.markdown(render_buffett_quote(), unsafe_allow_html=True)

# ===== 快速搜索框 =====
st.markdown("""
<style>
.search-bar-wrap {
    background: #08080E;
    border: 1px solid #1E1E26;
    border-radius: 2px;
    padding: 20px 24px 16px;
    margin-bottom: 20px;
}
.search-bar-wrap .stTextInput > div > div > input {
    background: #0C0C14 !important;
    border: 1px solid #2A2A36 !important;
    border-radius: 2px !important;
    color: #E8E8F0 !important;
    font-size: 1rem !important;
    padding: 10px 16px !important;
}
.search-label {
    font-size: 0.5rem; letter-spacing: 5px; color: #C9A962;
    text-transform: uppercase; font-weight: 500; margin-bottom: 8px;
}
</style>
<div class="search-label">Quick Analysis</div>
""", unsafe_allow_html=True)

_sq_col1, _sq_col2 = st.columns([3, 1])
with _sq_col1:
    _search_query = st.text_input(
        "search", label_visibility="collapsed",
        placeholder="搜索股票代码或名称  e.g. Apple / AAPL / 茅台 / 0700",
        key="stock_search_query",
    )
with _sq_col2:
    _search_mkt = st.selectbox(
        "market", ["全部市场", "US", "HK", "A股"],
        key="stock_search_market", label_visibility="collapsed",
    )
_mkt_map = {"全部市场": "all", "US": "us", "HK": "hk", "A股": "a_share"}
_search_mkt_key = _mkt_map[_search_mkt]

# 搜索结果
_search_result_stock = None
if _search_query and len(_search_query.strip()) >= 1:
    _matches = search_stocks(_search_query, _search_mkt_key, limit=8)
    if _matches:
        _fmt_map = {m["symbol"]: "{} — {}  [{}]".format(
            m["symbol"], m["name"], m["market"].upper().replace("_SHARE", "")
        ) for m in _matches}
        _selected_key = st.selectbox(
            "选择股票",
            options=list(_fmt_map.keys()),
            format_func=lambda k: _fmt_map[k],
            key="stock_search_select",
            label_visibility="collapsed",
        )
        _search_result_stock = next((m for m in _matches if m["symbol"] == _selected_key), None)
        if _search_result_stock and st.button(
            "🔍 分析 {}".format(_search_result_stock["symbol"]),
            key="search_analyze_btn", type="primary",
        ):
            st.session_state["_quick_search_symbol"] = _search_result_stock["symbol"]
            st.session_state["_quick_search_name"]   = _search_result_stock["name"]
            st.session_state["_quick_search_market"] = _search_result_stock["market"]
    else:
        st.caption("未找到匹配股票。你可以直接在下方市场标签中输入代码运行分析。")

# 快速搜索直接触发分析
if st.session_state.get("_quick_search_symbol"):
    _qs_sym = st.session_state.pop("_quick_search_symbol")
    _qs_name = st.session_state.pop("_quick_search_name", _qs_sym)
    _qs_mkt = st.session_state.pop("_quick_search_market", "us")
    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.55rem;letter-spacing:4px;color:#C9A962;'
        'text-transform:uppercase;margin-bottom:8px;">Quick Analysis</div>',
        unsafe_allow_html=True
    )
    _qs_user = get_current_user() or {}
    _qs_uid = _qs_user.get("username", "anonymous")
    _qs_role = _qs_user.get("role", "viewer")
    _qs_allowed, _qs_remaining, _qs_plan = can_analyze(_qs_uid, role=_qs_role)
    if not _qs_allowed:
        st.warning("You've used all **{} free analyses** this month.".format(FREE_MONTHLY_LIMIT))
    else:
        if _qs_plan == "free":
            st.caption("Free plan: {}/{} analyses remaining".format(_qs_remaining, FREE_MONTHLY_LIMIT))
        increment_usage(_qs_uid)
        render_stock_analysis(_qs_sym, _qs_name, _qs_mkt, config)

st.markdown("---")

# ===== Sidebar: 信息采集中心 =====
with st.sidebar:
    # AI Status
    provider = get_active_provider(config)
    if provider:
        st.markdown(render_sidebar_status(provider.name, provider.model, True), unsafe_allow_html=True)
    else:
        st.markdown(render_sidebar_status("Not Configured", "--", False), unsafe_allow_html=True)

    st.divider()

    # ===== PHILOSOPHY — 大师投资哲学 =====
    st.markdown("""
    <style>
    .phil-section { margin-bottom: 4px; }
    .phil-header {
        font-size: 0.68rem; letter-spacing: 3px; color: #C9A962;
        text-transform: uppercase; font-weight: 500; margin-bottom: 2px;
    }
    .phil-content {
        font-size: 0.75rem; color: #6A6A78; line-height: 1.5;
        padding: 8px 0 4px 8px; border-left: 1px solid #2A2A34;
    }
    .phil-principle {
        display: flex; align-items: flex-start; gap: 6px;
        padding: 4px 0; border-bottom: 1px solid #14141A;
    }
    .phil-dot {
        width: 4px; height: 4px; background: #C9A962; border-radius: 50%;
        margin-top: 6px; flex-shrink: 0;
    }
    .phil-text { font-size: 0.74rem; color: #7A7A88; line-height: 1.4; }
    .phil-text strong { color: #BDBDBD; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    with st.expander("BUFFETT · 巴菲特哲学", expanded=False):
        st.markdown("""
        <div class="phil-content">
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>市场先生</strong> — 市场短期是投票机，长期是称重机。利用市场，而非被市场左右。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>护城河</strong> — 寻找由宽广深厚的护城河保护的城堡。ROE 长期>15% 是护城河存在的证明。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>安全边际</strong> — 价格是你付出的，价值是你得到的。买入价须显著低于内在价值。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>能力圈</strong> — 只投资自己真正理解的生意。一句话说不清楚的公司，不买。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>长期主义</strong> — 不愿持有十年，就连十分钟也不要持有。复利是第八大奇迹。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>集中投资</strong> — 把鸡蛋放在少数几个篮子，然后看好它们。等待最肥的球。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>管理层</strong> — 好企业应该即使傻瓜经营也能赚钱。关注资本配置和股东回报。</div></div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("段永平 · 本分哲学", expanded=False):
        st.markdown("""
        <div class="phil-content">
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>Stop Doing List</strong> — 停止做不对的事比找到对的事更重要。不懂不做，不用杠杆，不做空。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>本分</strong> — 做正确的事情。商业道德和长期信誉比短期利润更重要。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>企业文化</strong> — 文化是最深的护城河。好文化让员工自动做正确的事。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>生意模式</strong> — 好生意：客户反复购买 + 不需太多资本 + 抵御通胀。问：10年后还在吗？</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>投资就是投人</strong> — 首问：愿意和这个管理层做生意吗？诚实 + 聪明 + 利益一致。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>等待与重仓</strong> — 大部分时间是等待。好机会很少，遇到了要有勇气下重注。</div></div>
        <div class="phil-principle"><div class="phil-dot"></div>
        <div class="phil-text"><strong>犯错纠错</strong> — 发现基本面变坏立即卖出，不管价格。死扛是价值投资最大的误区。</div></div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ===== INTELLIGENCE — 信息采集面板 =====
    st.markdown('<div class="news-section-title">INTELLIGENCE</div>', unsafe_allow_html=True)

    # 当前选中股票的新闻 (如果有)
    sidebar_symbol = st.session_state.get("_current_symbol")
    sidebar_market = st.session_state.get("_current_market")
    sidebar_name = st.session_state.get("_current_name")

    if sidebar_symbol and sidebar_market:
        # -- 个股新闻 --
        st.markdown('<div style="color:{}; font-size:0.72rem; letter-spacing:1px; margin:8px 0 4px;">NEWS · {}</div>'.format(
            COLORS["text_muted"], sidebar_symbol), unsafe_allow_html=True)

        news_list = cached_fetch_news(sidebar_symbol, sidebar_market, 6)
        if news_list:
            for n in news_list:
                st.markdown(render_news_item(
                    n["title"], n.get("source", ""), n.get("time", ""), n.get("url", "")
                ), unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:{}; font-size:0.78rem; padding:6px 0;">No recent news</div>'.format(
                COLORS["text_muted"]), unsafe_allow_html=True)

        # -- 财报日历 --
        calendar = cached_fetch_calendar(sidebar_symbol, sidebar_market)
        if calendar:
            st.markdown('<div style="color:{}; font-size:0.72rem; letter-spacing:1px; margin:12px 0 6px;">EARNINGS CALENDAR</div>'.format(
                COLORS["text_muted"]), unsafe_allow_html=True)

            if calendar.get("earnings_date"):
                sub = ""
                if calendar.get("eps_estimate"):
                    sub = "EPS Est. ${:.2f}".format(calendar["eps_estimate"])
                    if calendar.get("revenue_estimate"):
                        sub += " · Rev Est. {}".format(format_revenue(calendar["revenue_estimate"]))
                st.markdown(render_calendar_card(
                    "NEXT EARNINGS", calendar["earnings_date"], sub
                ), unsafe_allow_html=True)

            if calendar.get("ex_dividend_date"):
                st.markdown(render_calendar_card(
                    "EX-DIVIDEND", calendar["ex_dividend_date"]
                ), unsafe_allow_html=True)

        st.divider()

    # -- 市场新闻 --
    st.markdown('<div style="color:{}; font-size:0.72rem; letter-spacing:1px; margin:4px 0;">MARKET NEWS</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)

    # 获取当前 tab 对应市场的新闻
    market_for_news = sidebar_market or "us"
    market_news = cached_fetch_market_news(market_for_news, 5)
    if market_news:
        for n in market_news:
            st.markdown(render_news_item(
                n["title"], n.get("source", ""), n.get("time", "")
            ), unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:{}; font-size:0.78rem; padding:6px 0;">Loading market news...</div>'.format(
            COLORS["text_muted"]), unsafe_allow_html=True)

    st.divider()

    # Quick Add
    st.markdown('<div style="color:{}; font-size:0.72rem; letter-spacing:1px; margin-bottom:0.5rem;">QUICK ADD</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)
    with st.form("add_stock_quick"):
        new_market = st.selectbox("Market", ["us", "hk", "a_share"],
                                  format_func=lambda x: {"us": "US", "hk": "HK", "a_share": "A-Share"}[x])
        new_symbol = st.text_input("Symbol", placeholder="AAPL / 0700.HK / sh600519")
        new_name = st.text_input("Name")
        if st.form_submit_button("Add"):
            if new_symbol and new_name:
                stock_list = getattr(config.watchlist, new_market)
                if not any(s.symbol == new_symbol for s in stock_list):
                    stock_list.append(StockItem(symbol=new_symbol, name=new_name))
                    st.rerun()


# ===== Market tabs =====
tab_us, tab_hk, tab_a, tab_overview = st.tabs(
    ["US MARKET", "HK MARKET", "A-SHARE", "OVERVIEW"]
)

all_results = []

for tab, market_key, market_name in [
    (tab_us, "us", "US"), (tab_hk, "hk", "HK"), (tab_a, "a_share", "A-Share")
]:
    with tab:
        stocks = getattr(config.watchlist, market_key, [])
        if not stocks:
            st.markdown(render_empty_state("--",
                "No watchlist for {}".format(market_name),
                "Add stocks via the sidebar or Settings page"),
                unsafe_allow_html=True)
            continue

        selected = st.selectbox(
            "Select", stocks,
            format_func=lambda s: "{} {}".format(s.symbol, s.name),
            key="select_{}".format(market_key),
            label_visibility="collapsed",
        )

        if selected:
            # 记录当前选中股票，供侧边栏新闻面板使用
            st.session_state["_current_symbol"] = selected.symbol
            st.session_state["_current_market"] = market_key
            st.session_state["_current_name"] = selected.name

            # Freemium gate
            _a_user = get_current_user() or {}
            _a_uid = _a_user.get("username", "anonymous")
            _a_role = _a_user.get("role", "viewer")
            allowed, remaining, plan = can_analyze(_a_uid, role=_a_role)
            if not allowed:
                st.warning(
                    "You've used all **{} free analyses** this month. "
                    "Upgrade to **Premium** for unlimited access.".format(FREE_MONTHLY_LIMIT))
                st.info("Contact admin to upgrade your plan.")
                st.stop()

            # Show remaining quota for free users
            if plan == "free":
                st.caption("Free plan: {}/{} analyses remaining this month".format(
                    remaining, FREE_MONTHLY_LIMIT))

            # Track usage — only increment once per unique (uid, symbol) selection,
            # not on every Streamlit rerun, to avoid burning quota on re-renders.
            _usage_key = "_usage_counted_{}_{}".format(_a_uid, selected.symbol)
            if not st.session_state.get(_usage_key):
                increment_usage(_a_uid)
                st.session_state[_usage_key] = True

            out = render_stock_analysis(selected.symbol, selected.name, market_key, config)
            if out:
                all_results.append(out)

        st.divider()
        if st.button("Scan All {}".format(market_name), key="refresh_{}".format(market_key)):
            from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed
            overview_data = []
            progress_bar = st.progress(0)
            total = len(stocks)

            def _scan_one(stock):
                try:
                    r, _, _, _, moat, _ = run_analysis(stock.symbol, stock.name, market_key, config)
                    return {
                        "ok": True, "r": r, "moat": moat,
                        "Symbol": r.symbol, "Name": r.name,
                        "Price": "{:.2f}".format(r.price) if r.price else "-",
                        "Grade": moat["grade"],
                        "Score": moat["percentage"],
                        "ROE": fmt_pct(_normalize_fundamentals(r.fundamentals).get("roe")),
                        "Trend": trend_label(r.tech_signal.get("trend")),
                        "Verdict": moat["label"],
                    }
                except Exception as e:
                    return {"ok": False, "Symbol": stock.symbol, "Name": stock.name,
                            "Price": "-", "Grade": "-", "Score": 0,
                            "ROE": "-", "Trend": "-", "Verdict": str(e)[:30]}

            with ThreadPoolExecutor(max_workers=config.parallel.scan_workers) as exe:
                futures = {exe.submit(_scan_one, s): s for s in stocks}
                done = 0
                for future in _as_completed(futures):
                    row = future.result()
                    overview_data.append(row)
                    if row.get("ok") and "r" in row:
                        all_results.append((row["r"], row["moat"]))
                    done += 1
                    progress_bar.progress(done / total)

            overview_data.sort(key=lambda x: x.get("Score", 0), reverse=True)
            display_cols = ["Symbol", "Name", "Price", "Grade", "Score", "ROE", "Trend", "Verdict"]
            display_df = pd.DataFrame([{c: r[c] for c in display_cols} for r in overview_data])
            st.dataframe(display_df, use_container_width=True, hide_index=True)

with tab_overview:
    # 一键扫描全部三市场
    if st.button("⚡ Scan All Markets (Parallel)", type="primary"):
        from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed2
        all_stocks = []
        for mkey in ("us", "hk", "a_share"):
            for s in getattr(config.watchlist, mkey, []):
                all_stocks.append((s, mkey))
        if all_stocks:
            scan_progress = st.progress(0)
            scan_status = st.empty()
            scan_results = []
            total_scan = len(all_stocks)

            def _scan_stock(stock_market):
                s, mkey = stock_market
                try:
                    r, _, _, _, moat, _ = run_analysis(s.symbol, s.name, mkey, config)
                    return {"ok": True, "r": r, "moat": moat}
                except Exception as e:
                    return {"ok": False, "symbol": s.symbol, "name": s.name,
                            "market": mkey, "error": str(e)[:40]}

            with ThreadPoolExecutor(max_workers=config.parallel.scan_all_workers) as exe:
                futs = {exe.submit(_scan_stock, sm): sm for sm in all_stocks}
                done_c = 0
                for fut in _as_completed2(futs):
                    res = fut.result()
                    scan_results.append(res)
                    done_c += 1
                    scan_progress.progress(done_c / total_scan)
                    scan_status.caption("Scanned {}/{}...".format(done_c, total_scan))

            scan_status.empty()
            for res in scan_results:
                if res.get("ok"):
                    all_results.append((res["r"], res["moat"]))
            st.success("Scan complete — {} stocks".format(total_scan))

    # 排行榜显示
    if all_results:
        ml = {"us": "US", "hk": "HK", "a_share": "CN"}
        grade_colors = {"A+": "#3ECF8E", "A": "#3ECF8E", "B": "#60A5FA",
                        "C": "#C9A962", "D": "#F5A623", "F": "#EF4444"}
        rank = []
        for item in all_results:
            r, moat = item if isinstance(item, tuple) else (item, {})
            if not isinstance(moat, dict) or "grade" not in moat:
                continue
            norm = _normalize_fundamentals(r.fundamentals)
            rank.append({
                "Market": ml.get(r.market, ""),
                "Symbol": r.symbol, "Name": r.name,
                "Grade": moat["grade"],
                "Score": moat["percentage"],
                "Label": moat["label"],
                "ROE": fmt_pct(norm.get("roe")),
                "FCF": norm.get("free_cashflow"),
                "Verdict": moat.get("verdict", "")[:40],
            })

        if rank:
            rank.sort(key=lambda x: x["Score"], reverse=True)

            # ── Filters ──────────────────────────────────────────────────────
            st.markdown("### Watchlist Ranking")
            f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
            with f1:
                all_grades = ["A+", "A", "B", "C", "D", "F"]
                sel_grades = st.multiselect(
                    "Grade", all_grades, default=all_grades, key="ov_grades",
                    label_visibility="collapsed",
                    placeholder="Filter by grade…",
                )
            with f2:
                all_markets = sorted({r["Market"] for r in rank})
                sel_markets = st.multiselect(
                    "Market", all_markets, default=all_markets, key="ov_markets",
                    label_visibility="collapsed",
                    placeholder="Filter by market…",
                )
            with f3:
                min_score = st.slider("Min score", 0, 100, 0, key="ov_minscore",
                                      label_visibility="collapsed")
            with f4:
                fcf_only = st.toggle("FCF+", value=False, key="ov_fcf",
                                     help="Only show stocks with positive free cashflow")

            # Apply filters
            filtered = [
                r for r in rank
                if r["Grade"] in (sel_grades or all_grades)
                and r["Market"] in (sel_markets or all_markets)
                and r["Score"] >= min_score
                and (not fcf_only or (r["FCF"] is not None and r["FCF"] > 0))
            ]
            st.caption(f"Showing **{len(filtered)}** of {len(rank)} stocks")

            for i, row in enumerate(filtered):
                g = row["Grade"]
                gc = grade_colors.get(g, "#8A8A96")
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "&nbsp;{}".format(i + 1)
                col_rank, col_sym, col_score, col_meta = st.columns([1, 3, 5, 4])
                with col_rank:
                    st.markdown(medal, unsafe_allow_html=True)
                with col_sym:
                    st.markdown("**{}** <span style='color:#5A5A68; font-size:0.8rem;'>[{}] {}</span>".format(
                        row["Symbol"], row["Market"], row["Name"][:12]), unsafe_allow_html=True)
                with col_score:
                    filled = int(row["Score"] / 100 * 20)
                    bar = "█" * filled + "░" * (20 - filled)
                    fcf_tag = (
                        ' <span style="color:#3ECF8E; font-size:0.7rem;">FCF✓</span>'
                        if row["FCF"] and row["FCF"] > 0 else ""
                    )
                    st.markdown(
                        '<span style="color:{gc}; font-family:monospace;">{bar}</span>'
                        ' <span style="color:{gc}; font-weight:700;">{score:.0f}</span>'
                        '<span style="color:#5A5A68; font-size:0.8rem;">/{grade}</span>{fcf}'.format(
                            gc=gc, bar=bar, score=row["Score"], grade=g, fcf=fcf_tag),
                        unsafe_allow_html=True)
                with col_meta:
                    st.markdown(
                        '<span style="color:#8A8A96; font-size:0.82rem;">{label} · ROE {roe}</span>'.format(
                            label=row["Label"], roe=row["ROE"]),
                        unsafe_allow_html=True)
    else:
        st.info("Analyze individual stocks or click **Scan All Markets** to build the ranking.")

st.markdown('<div class="disclaimer">DISCLAIMER: FOR RESEARCH PURPOSES ONLY. NOT INVESTMENT ADVICE.</div>',
            unsafe_allow_html=True)
