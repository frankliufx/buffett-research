"""AI 对冲基金 — 多大师并行分析

侧边栏独立页面。用户输入股票代码，选择分析师阵容，一键运行。
复用现有数据管道（yfinance），无需第三方 financial datasets API。
"""

import logging
import streamlit as st
import streamlit.components.v1 as _cmp
from datetime import datetime

from src.config import load_config, get_active_provider
from src.auth import get_current_user
from src.data.price import fetch_history, fetch_quote
from src.data.financial import fetch_fundamentals
from src.analysis.fundamental import analyze_buffett, _normalize_fundamentals
from src.analysis.moat import score_moat
from src.analysis.valuation import calc_dcf
from src.analysis.technical import compute_indicators, generate_technical_signal
from src.ai.hedge_fund_agents import HEDGE_FUND_ANALYSTS, ANALYST_GROUPS, ANALYST_BY_ID
from src.ai.hedge_fund_runner import run_hedge_fund, run_full_workflow
from src.ui_theme import get_global_css

logging.basicConfig(level=logging.WARNING)

st.markdown(get_global_css(), unsafe_allow_html=True)

# ── 私有样式 ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 页面顶部大标题 */
.hf-hero {
    background: linear-gradient(135deg, #08080C 0%, #0D0D18 100%);
    border: 1px solid rgba(201,169,98,0.12);
    border-radius: 6px;
    padding: 28px 32px 22px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.hf-hero::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #C9A962, transparent);
}
.hf-hero-title {
    font-family: 'Cormorant Garamond', 'Georgia', serif;
    font-size: 1.9rem;
    font-weight: 300;
    letter-spacing: 4px;
    color: #E8E8F0;
    margin-bottom: 4px;
}
.hf-hero-sub {
    font-size: 0.62rem;
    letter-spacing: 5px;
    color: rgba(201,169,98,0.55);
    text-transform: uppercase;
}
.hf-hero-count {
    position: absolute;
    right: 32px;
    top: 50%;
    transform: translateY(-50%);
    font-family: 'Cormorant Garamond', serif;
    font-size: 3rem;
    font-weight: 200;
    color: rgba(201,169,98,0.15);
    letter-spacing: 2px;
}

/* 分析师选择卡片 */
.analyst-group-label {
    font-size: 0.48rem;
    letter-spacing: 4px;
    color: rgba(201,169,98,0.5);
    text-transform: uppercase;
    margin-bottom: 6px;
    margin-top: 12px;
}

/* 结果区域 */
.hf-result-header {
    background: #0D0D14;
    border: 1px solid #1E1E2A;
    border-top: 2px solid;
    border-radius: 4px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.hf-score-big {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3rem;
    font-weight: 300;
    line-height: 1;
}
.hf-verdict {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: 2px;
    margin-top: 4px;
}
.hf-meta {
    font-size: 0.58rem;
    letter-spacing: 2px;
    color: #6A6A78;
    margin-top: 6px;
}
.hf-vote-bar {
    display: flex;
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    margin-top: 16px;
}
.hf-gauge {
    position: relative;
    height: 16px;
    margin: 12px 0 4px;
}
.hf-gauge-track {
    position: absolute;
    top: 6px;
    left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #F44336, #FF9800, #C9A962, #69F0AE, #00C853);
    border-radius: 2px;
}
.hf-gauge-dot {
    position: absolute;
    top: 0;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: 2px solid #08080C;
    transform: translateX(-50%);
    box-shadow: 0 0 8px rgba(201,169,98,0.4);
}
.hf-gauge-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.44rem;
    color: #5A5A6A;
    letter-spacing: 1px;
}

/* 分析师结果卡片 */
.analyst-card {
    background: #0D0D14;
    border: 1px solid #1A1A24;
    border-left: 3px solid;
    border-radius: 3px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.ac-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
}
.ac-who {
    display: flex;
    align-items: center;
    gap: 10px;
}
.ac-icon { font-size: 1.4rem; }
.ac-name {
    font-size: 0.85rem;
    font-weight: 600;
    color: #E8E8F0;
}
.ac-style {
    font-size: 0.48rem;
    color: #6A6A78;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 1px;
}
.ac-signal {
    font-size: 0.5rem;
    font-weight: 700;
    letter-spacing: 3px;
    padding: 3px 10px;
    border: 1px solid;
    border-radius: 2px;
    white-space: nowrap;
}
.ac-reasoning {
    font-size: 0.7rem;
    color: #8A8A98;
    line-height: 1.65;
    border-left: 2px solid #1E1E2A;
    padding-left: 10px;
    margin-bottom: 10px;
}
.ac-conf-row {
    display: flex;
    align-items: center;
    gap: 8px;
}
.ac-conf-track {
    flex: 1;
    height: 3px;
    background: #1A1A24;
    border-radius: 2px;
    overflow: hidden;
}
.ac-conf-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.5s;
}
.ac-conf-label {
    font-size: 0.54rem;
    color: #8A8A98;
    width: 32px;
    text-align: right;
}

/* 综合摘要表格 */
.summary-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.7rem;
    margin-bottom: 20px;
}
.summary-table th {
    font-size: 0.44rem;
    letter-spacing: 3px;
    color: rgba(201,169,98,0.5);
    text-transform: uppercase;
    padding: 8px 12px;
    border-bottom: 1px solid #1A1A24;
    text-align: left;
}
.summary-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #0F0F18;
    color: #C8C8D8;
    vertical-align: middle;
}
.summary-table tr:hover td {
    background: rgba(201,169,98,0.03);
}

/* 数据上下文展示 */
.data-ctx-box {
    background: #0A0A10;
    border: 1px solid #1A1A24;
    border-radius: 3px;
    padding: 14px 16px;
    font-size: 0.62rem;
    color: #6A6A78;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    line-height: 1.7;
    white-space: pre-wrap;
    max-height: 300px;
    overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)

# ── 登录检测 ─────────────────────────────────────────────────────────────────
user = get_current_user()
if not user:
    st.warning("请先登录")
    st.stop()

config = load_config()
provider = get_active_provider(config)

# ── 顶部标题 ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hf-hero">
    <div class="hf-hero-title">AI Hedge Fund</div>
    <div class="hf-hero-sub">Multi-Agent · 13 Legendary Investors · Parallel Analysis</div>
    <div class="hf-hero-count">13</div>
</div>
""", unsafe_allow_html=True)

if not provider:
    st.error("⚠️ 未配置 API Key，请前往 **设置** 页面配置后再使用。")
    st.stop()

# ── 布局：左侧控制 + 右侧结果 ────────────────────────────────────────────────
ctrl_col, result_col = st.columns([1, 2], gap="large")

with ctrl_col:
    st.markdown("#### 🎯 分析配置")

    # 股票输入
    ticker_input = st.text_input(
        "股票代码",
        placeholder="如 AAPL / 600519 / 0700",
        help="美股直接输入代码，A股输入6位数字，港股输入4位数字"
    ).strip().upper()

    market = st.selectbox("市场", ["美股", "A股", "港股"])
    market_map = {"美股": "us", "A股": "a_share", "港股": "hk"}
    market_code = market_map[market]

    st.markdown("---")
    st.markdown("#### 🧑‍💼 选择分析师阵容")
    st.caption("选择参与本次分析的投资大师（至少1位）")

    selected_ids = []
    for group_name, ids in ANALYST_GROUPS.items():
        if group_name == "专项分析师":
            st.markdown("---")
            st.caption("专项分析师：系统性量化分析，独立投票")
        st.markdown(
            f'<div class="analyst-group-label">{group_name}</div>',
            unsafe_allow_html=True
        )
        for aid in ids:
            analyst = ANALYST_BY_ID.get(aid)
            if not analyst:
                continue
            checked = st.checkbox(
                f"{analyst['icon']} {analyst['name_cn']}",
                value=(aid in ["buffett", "munger", "graham", "lynch", "burry", "damodaran",
                               "technical_analyst", "fundamentals_analyst", "valuation_analyst"]),
                key=f"analyst_{aid}",
                help=analyst["style"],
            )
            if checked:
                selected_ids.append(aid)

    st.markdown("---")
    st.markdown("#### 🔑 数据增强（可选）")

    try:
        from src.data.financial_datasets import has_fd_key as _hfk
        _current_fd_key = config.api.financial_datasets_api_key if hasattr(config, 'api') else ""
    except Exception:
        _current_fd_key = ""
        _hfk = lambda k="": False

    fd_key_input = st.text_input(
        "Financial Datasets API Key",
        type="password",
        value=st.session_state.get("fd_api_key_override", _current_fd_key),
        placeholder="可选，填入后美股获得更丰富数据",
        key="fd_api_key_input",
    )
    if fd_key_input != st.session_state.get("fd_api_key_override", _current_fd_key):
        st.session_state["fd_api_key_override"] = fd_key_input

    _fd_active = bool(st.session_state.get("fd_api_key_override") or _current_fd_key)
    if _fd_active:
        st.caption("✦ Financial Datasets AI 已启用")

    st.markdown("---")

    run_btn = st.button(
        "🚀 运行分析",
        type="primary",
        use_container_width=True,
        disabled=(not ticker_input or len(selected_ids) == 0),
    )

    if not ticker_input:
        st.caption("请输入股票代码")
    elif len(selected_ids) == 0:
        st.warning("至少选择1位分析师")
    else:
        st.caption(f"已选 {len(selected_ids)} 位分析师，并行运行")

# ── 右侧结果区 ────────────────────────────────────────────────────────────────
with result_col:
    if not run_btn and "hf_result" not in st.session_state:
        # 空状态提示
        st.markdown("""
        <div style="text-align:center;padding:60px 20px">
            <div style="font-size:2.5rem;opacity:0.2;margin-bottom:16px">🏦</div>
            <div style="font-family:'Georgia',serif;font-size:1.2rem;color:#4A4A58;letter-spacing:2px">
                AI HEDGE FUND
            </div>
            <div style="font-size:0.62rem;color:#3A3A48;margin-top:8px;letter-spacing:1px">
                选择股票和分析师阵容，点击运行分析
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif run_btn:
        # 清除上次结果
        if "hf_result" in st.session_state:
            del st.session_state["hf_result"]

        with st.spinner(f"🔄 正在并行调用 {len(selected_ids)} 位分析师..."):
            try:
                # 拉取数据
                df = fetch_history(ticker_input, market_code, 365)
                quote = fetch_quote(ticker_input, market_code) or {}
                fundamentals = fetch_fundamentals(ticker_input, market_code) or {}
                normalized = _normalize_fundamentals(fundamentals)
                price = float(quote.get("price") or quote.get("regularMarketPrice") or 0)

                # 计算 buffett / dcf / tech (moat needs tech_signal first → see below)
                buffett_res = analyze_buffett(fundamentals, normalized)
                dcf = calc_dcf(price, fundamentals, normalized) if price > 0 else {}
                tech = {}
                tech_signal = {}
                df_ind = None
                if df is not None and not df.empty:
                    df_ind = compute_indicators(df)
                    sig = generate_technical_signal(df_ind)
                    tech_signal = sig
                    tech = {
                        "trend": sig.get("trend"),
                        "momentum": sig.get("momentum"),
                        "rsi": sig.get("rsi"),
                        "macd": sig.get("macd"),
                    }

                # moat depends on tech signal — must be computed after tech_signal
                moat = score_moat(fundamentals, normalized, tech_signal)

                hf_result = run_full_workflow(
                    symbol=ticker_input,
                    name=quote.get("shortName") or quote.get("longName") or ticker_input,
                    market=market_code,
                    price=price,
                    fundamentals=fundamentals,
                    normalized=normalized,
                    moat=moat,
                    dcf=dcf,
                    tech=tech,
                    df_history=df_ind if df is not None and not df.empty else None,
                    analyst_ids=selected_ids,
                    provider=provider,
                    max_workers=config.parallel.hedgefund_workers,
                )

                if hf_result:
                    st.session_state["hf_result"] = hf_result
                    st.session_state["hf_symbol"] = ticker_input
                    st.session_state["hf_price"] = price
                    st.session_state["hf_name"] = (
                        quote.get("shortName") or quote.get("longName") or ticker_input
                    )
                else:
                    st.error("分析失败，请检查 API Key 配置。")

            except Exception as e:
                st.error(f"数据获取失败: {e}")
                logging.exception("HedgeFund page error")

    # 展示结果
    if "hf_result" in st.session_state:
        r = st.session_state["hf_result"]
        sym = st.session_state.get("hf_symbol", "")
        price_val = st.session_state.get("hf_price", 0)
        name_val = st.session_state.get("hf_name", sym)
        cons = r["consensus"]
        ws = r["weighted_score"]

        sig_colors = {"bullish": "#00C853", "bearish": "#F44336", "neutral": "#C9A962"}
        sc = sig_colors.get(cons["signal"], "#C9A962")

        bull, bear, neut = r["bullish_count"], r["bearish_count"], r["neutral_count"]
        total = bull + bear + neut or 1
        gauge_pos = (ws + 100) / 200 * 100

        # ── 综合结论卡 ────────────────────────────────
        st.markdown(f"""
        <div class="hf-result-header" style="border-top-color:{sc}">
            <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div>
                    <div style="font-size:0.44rem;letter-spacing:5px;color:rgba(201,169,98,0.5);
                        text-transform:uppercase;border:1px solid rgba(201,169,98,0.15);
                        display:inline-block;padding:2px 10px;margin-bottom:8px">
                        {cons['unanimity']}
                    </div>
                    <div class="hf-verdict" style="color:{sc}">{cons['verdict']}</div>
                    <div class="hf-meta">
                        {sym} &nbsp;·&nbsp; {name_val}
                        &nbsp;·&nbsp; ¥/$ {price_val:.2f}
                        &nbsp;·&nbsp; {len(r['analysts'])} 位分析师
                        &nbsp;·&nbsp; <span style="color:{'#C9A962' if r.get('data_source') == 'financial_datasets' else '#5A5A6A'}">{'Financial Datasets AI ✦' if r.get('data_source') == 'financial_datasets' else 'yfinance'}</span>
                    </div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:0.44rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase">综合得分</div>
                    <div class="hf-score-big" style="color:{sc}">{ws:+.0f}</div>
                </div>
            </div>
            <div class="hf-gauge">
                <div class="hf-gauge-track"></div>
                <div class="hf-gauge-dot" style="left:{gauge_pos:.1f}%;background:{sc}"></div>
            </div>
            <div class="hf-gauge-labels">
                <span>极度看空</span><span>中性</span><span>极度看多</span>
            </div>
            <div class="hf-vote-bar">
                <div style="width:{bull/total*100:.0f}%;background:#00C853"></div>
                <div style="width:{neut/total*100:.0f}%;background:#C9A962"></div>
                <div style="width:{bear/total*100:.0f}%;background:#F44336"></div>
            </div>
            <div style="display:flex;gap:16px;margin-top:8px">
                <span style="font-size:0.58rem;color:#00C853">▲ 看多 {bull}</span>
                <span style="font-size:0.58rem;color:#C9A962">● 中性 {neut}</span>
                <span style="font-size:0.58rem;color:#F44336">▼ 看空 {bear}</span>
                <span style="font-size:0.58rem;color:#5A5A6A;margin-left:auto">
                    置信度 {cons['confidence']}%
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── 决策面板（Phase 1.4）────────────────────
        fd = r.get("final_decision")
        ns = r.get("news_sentiment") or {}
        rk = r.get("risk") or {}
        if fd:
            action_colors = {
                "买入": "#00C853", "加仓": "#26A69A", "持有": "#C9A962",
                "减仓": "#FF8A65", "卖出": "#F44336",
            }
            ac = action_colors.get(fd["action"], "#C9A962")
            ez = fd.get("entry_zone", {})
            sl = fd.get("stop_loss", {})
            tp = fd.get("take_profit", {})

            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#0a0d14 0%,#141822 100%);
                 border:1px solid rgba(201,169,98,0.18);border-radius:6px;padding:24px 28px;margin:14px 0">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;
                     border-bottom:1px solid rgba(201,169,98,0.12);padding-bottom:14px;margin-bottom:18px">
                    <div>
                        <div style="font-size:0.42rem;letter-spacing:5px;color:rgba(201,169,98,0.5);
                             text-transform:uppercase">portfolio manager · 综合决策</div>
                        <div style="font-size:1.85rem;font-weight:700;color:{ac};margin:6px 0 0;line-height:1.1">
                            {fd['action']}</div>
                        <div style="font-size:0.85rem;color:#a8a39a;margin-top:4px">
                            {fd['conviction']}信心 · {fd['horizon']} ·
                            综合分 {fd['combined_score']:+d}</div>
                    </div>
                    <div style="text-align:right">
                        <div style="font-size:0.42rem;letter-spacing:4px;color:rgba(201,169,98,0.5)">建议仓位</div>
                        <div style="font-size:2.0rem;font-weight:700;color:#C9A962">{fd['position_pct']}%</div>
                        <div style="font-size:0.78rem;color:#888;margin-top:2px">
                            上限 {rk.get('max_position_pct', '—')}% · {rk.get('risk_level', '—')}风险</div>
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;margin-bottom:14px">
                    <div>
                        <div style="font-size:0.40rem;letter-spacing:3px;color:rgba(201,169,98,0.5);
                             text-transform:uppercase;margin-bottom:6px">入场区间</div>
                        <div style="font-size:1.1rem;font-weight:600;color:#fff">
                            {ez.get('ideal','—')} ~ {ez.get('acceptable','—')}</div>
                        <div style="font-size:0.72rem;color:#888;margin-top:2px">{ez.get('anchor','—')}</div>
                    </div>
                    <div>
                        <div style="font-size:0.40rem;letter-spacing:3px;color:rgba(244,67,54,0.65);
                             text-transform:uppercase;margin-bottom:6px">止损</div>
                        <div style="font-size:1.1rem;font-weight:600;color:#F44336">
                            {sl.get('price','—')}</div>
                        <div style="font-size:0.72rem;color:#888;margin-top:2px">
                            {sl.get('rationale','—')}</div>
                    </div>
                    <div>
                        <div style="font-size:0.40rem;letter-spacing:3px;color:rgba(0,200,83,0.65);
                             text-transform:uppercase;margin-bottom:6px">止盈目标</div>
                        <div style="font-size:1.1rem;font-weight:600;color:#00C853">
                            {tp.get('price','—')}</div>
                        <div style="font-size:0.72rem;color:#888;margin-top:2px">
                            {tp.get('rationale','—')}</div>
                    </div>
                </div>

                <div style="display:flex;gap:14px;font-size:0.82rem;color:#a8a39a;
                     padding:10px 14px;background:rgba(201,169,98,0.04);border-radius:4px;margin-bottom:14px">
                    <div><b style="color:#C9A962">📰 新闻</b> {ns.get('label','—')}
                        ({ns.get('score',0):+d}, n={ns.get('article_count',0)})</div>
                    <div><b style="color:#C9A962">⚠️ 风险</b> {rk.get('regime','—')} · 年化{rk.get('annual_vol_pct','—')}%</div>
                    <div><b style="color:#C9A962">🗳️ 投票</b>
                        多 {fd['vote_aggregate']['bullish_weight']} ·
                        空 {fd['vote_aggregate']['bearish_weight']} · {fd['vote_aggregate']['unanimity']}</div>
                </div>

                <div style="font-size:0.40rem;letter-spacing:3px;color:rgba(201,169,98,0.5);
                     text-transform:uppercase;margin-bottom:8px">推理链</div>
                <div style="font-size:0.93rem;color:#d4ccbb;line-height:1.7;white-space:pre-wrap">
{fd.get('reasoning','')}</div>
            </div>
            """, unsafe_allow_html=True)

        # ── 历史决策（最近 10 次）────────────────────
        try:
            from src.db.decisions import get_recent_decisions
            from src.db.repository import get_or_create_stock as _gocs
            from src.db.session import db_available as _db_avail
            _MARKET_CANON_UI = {"US": "us", "CN": "a_share", "HK": "hk"}
            if _db_avail():
                _mk = _MARKET_CANON_UI.get(market_code, market_code.lower())
                _sid = _gocs(ticker_input, _mk, sym)
                _history = get_recent_decisions(_sid, limit=10)
                # 排除当次新写入（按 decided_at 是否 < 1 分钟前粗判）
                from datetime import datetime, timedelta, timezone
                _now = datetime.now(timezone.utc)
                _past = [h for h in _history if (_now - h["decided_at"]) > timedelta(seconds=30)]
                if _past:
                    with st.expander("📜 历史决策（最近 {} 次）".format(len(_past)), expanded=False):
                        action_colors_h = {
                            "买入": "#00C853", "加仓": "#26A69A", "持有": "#C9A962",
                            "减仓": "#FF8A65", "卖出": "#F44336",
                        }
                        rows_html = []
                        for h in _past:
                            ac = action_colors_h.get(h["action"], "#C9A962")
                            ts = h["decided_at"].astimezone().strftime("%Y-%m-%d %H:%M")
                            pos = "{:.1f}%".format(h["position_pct"]) if h["position_pct"] else "—"
                            rows_html.append(f"""
                            <tr style="border-bottom:1px solid rgba(201,169,98,0.08)">
                                <td style="padding:8px 10px;color:#888;font-size:0.78rem">{ts}</td>
                                <td style="padding:8px 10px;color:#fff;font-weight:600">{h['price']:.2f}</td>
                                <td style="padding:8px 10px;color:{ac};font-weight:700">{h['action']}</td>
                                <td style="padding:8px 10px;color:#a8a39a;font-size:0.8rem">{h['conviction']}</td>
                                <td style="padding:8px 10px;color:#fff;font-weight:600">{h['combined_score']:+d}</td>
                                <td style="padding:8px 10px;color:#C9A962">{pos}</td>
                                <td style="padding:8px 10px;color:#a8a39a;font-size:0.78rem">{h.get('consensus_verdict') or '—'}</td>
                                <td style="padding:8px 10px;color:#a8a39a;font-size:0.78rem">{h.get('news_label') or '—'}</td>
                                <td style="padding:8px 10px;color:#a8a39a;font-size:0.78rem">{h.get('risk_level') or '—'}</td>
                            </tr>""")
                        st.markdown(f"""
                        <div style="background:rgba(10,13,20,0.6);border:1px solid rgba(201,169,98,0.12);
                             border-radius:6px;overflow:hidden">
                            <table style="width:100%;border-collapse:collapse">
                                <thead>
                                    <tr style="background:rgba(201,169,98,0.06);
                                         border-bottom:1px solid rgba(201,169,98,0.18)">
                                        <th style="padding:10px;text-align:left;font-size:0.65rem;
                                             letter-spacing:2px;color:rgba(201,169,98,0.7)">时间</th>
                                        <th style="padding:10px;text-align:left;font-size:0.65rem;
                                             letter-spacing:2px;color:rgba(201,169,98,0.7)">价格</th>
                                        <th style="padding:10px;text-align:left;font-size:0.65rem;
                                             letter-spacing:2px;color:rgba(201,169,98,0.7)">决策</th>
                                        <th style="padding:10px;text-align:left;font-size:0.65rem;
                                             letter-spacing:2px;color:rgba(201,169,98,0.7)">信心</th>
                                        <th style="padding:10px;text-align:left;font-size:0.65rem;
                                             letter-spacing:2px;color:rgba(201,169,98,0.7)">综合分</th>
                                        <th style="padding:10px;text-align:left;font-size:0.65rem;
                                             letter-spacing:2px;color:rgba(201,169,98,0.7)">仓位</th>
                                        <th style="padding:10px;text-align:left;font-size:0.65rem;
                                             letter-spacing:2px;color:rgba(201,169,98,0.7)">大师共识</th>
                                        <th style="padding:10px;text-align:left;font-size:0.65rem;
                                             letter-spacing:2px;color:rgba(201,169,98,0.7)">新闻</th>
                                        <th style="padding:10px;text-align:left;font-size:0.65rem;
                                             letter-spacing:2px;color:rgba(201,169,98,0.7)">风险</th>
                                    </tr>
                                </thead>
                                <tbody>{''.join(rows_html)}</tbody>
                            </table>
                        </div>
                        """, unsafe_allow_html=True)
                        st.caption("数据源：本地 PostgreSQL（DB_FIRST_ENABLED 开启时自动落库）")
        except Exception as _e:
            # DB 不可用或未启用 → 静默跳过
            pass

        # ── Tab 切换：卡片 vs 表格 ────────────────────
        tab_cards, tab_table, tab_data = st.tabs(["📊 分析师详情", "📋 汇总表格", "🔧 原始数据"])

        with tab_cards:
            legendary = [a for a in r["analysts"] if a.get("group") != "专项分析师"]
            specialists = [a for a in r["analysts"] if a.get("group") == "专项分析师"]

            if legendary:
                st.markdown("**传奇投资人**", help="价值/成长/宏观等流派大师")
                for analyst in legendary:
                    asc = sig_colors.get(analyst["signal"], "#C9A962")
                    sig_labels = {"bullish": "BULLISH", "bearish": "BEARISH", "neutral": "NEUTRAL"}
                    sig_label = sig_labels.get(analyst["signal"], "—")
                    conf = analyst["confidence"]

                    st.markdown(f"""
                    <div class="analyst-card" style="border-left-color:{asc}">
                        <div class="ac-header">
                            <div class="ac-who">
                                <div class="ac-icon">{analyst['icon']}</div>
                                <div>
                                    <div class="ac-name">{analyst['name_cn']}</div>
                                    <div class="ac-style">{analyst['style']}</div>
                                </div>
                            </div>
                            <div class="ac-signal" style="color:{asc};border-color:{asc}">
                                {sig_label}
                            </div>
                        </div>
                        <div class="ac-reasoning">{analyst['reasoning']}</div>
                        <div class="ac-conf-row">
                            <span style="font-size:0.5rem;color:#5A5A6A;width:48px">置信度</span>
                            <div class="ac-conf-track">
                                <div class="ac-conf-fill" style="width:{conf}%;background:{asc}"></div>
                            </div>
                            <span class="ac-conf-label">{conf}%</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            if specialists:
                st.markdown("---")
                st.markdown("**专项分析师**", help="系统性量化分析：技术/基本面/估值/情绪")
                for analyst in specialists:
                    asc = sig_colors.get(analyst["signal"], "#C9A962")
                    sig_labels = {"bullish": "BULLISH", "bearish": "BEARISH", "neutral": "NEUTRAL"}
                    sig_label = sig_labels.get(analyst["signal"], "—")
                    conf = analyst["confidence"]

                    st.markdown(f"""
                    <div class="analyst-card" style="border-left-color:{asc}">
                        <div class="ac-header">
                            <div class="ac-who">
                                <div class="ac-icon">{analyst['icon']}</div>
                                <div>
                                    <div class="ac-name">{analyst['name_cn']}</div>
                                    <div class="ac-style">{analyst['style']}</div>
                                </div>
                            </div>
                            <div class="ac-signal" style="color:{asc};border-color:{asc}">
                                {sig_label}
                            </div>
                        </div>
                        <div class="ac-reasoning">{analyst['reasoning']}</div>
                        <div class="ac-conf-row">
                            <span style="font-size:0.5rem;color:#5A5A6A;width:48px">置信度</span>
                            <div class="ac-conf-track">
                                <div class="ac-conf-fill" style="width:{conf}%;background:{asc}"></div>
                            </div>
                            <span class="ac-conf-label">{conf}%</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        with tab_table:
            rows = []
            for analyst in r["analysts"]:
                rows.append({
                    "分析师": f"{analyst['icon']} {analyst['name_cn']}",
                    "风格": analyst["style"].split("·")[0].strip(),
                    "信号": analyst["signal"].upper(),
                    "置信度": f"{analyst['confidence']}%",
                    "理由摘要": analyst["reasoning"][:60] + "…" if len(analyst["reasoning"]) > 60 else analyst["reasoning"],
                })

            import pandas as pd
            df_table = pd.DataFrame(rows)

            def style_signal(val):
                colors = {"BULLISH": "color: #00C853", "BEARISH": "color: #F44336", "NEUTRAL": "color: #C9A962"}
                return colors.get(val, "")

            styled = df_table.style.map(style_signal, subset=["信号"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

        with tab_data:
            st.markdown("**传给分析师的数据摘要：**")
            st.markdown(
                f'<div class="data-ctx-box">{r["data_context"]}</div>',
                unsafe_allow_html=True
            )

        st.caption(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 使用模型: {provider.model}")
