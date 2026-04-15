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
from src.ai.hedge_fund_runner import run_hedge_fund
from src.ui_theme import get_global_css

logging.basicConfig(level=logging.WARNING)

st.set_page_config(
    page_title="AI 对冲基金 | Buffett Research",
    page_icon="🏦",
    layout="wide",
)

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
    market_map = {"美股": "US", "A股": "CN", "港股": "HK"}
    market_code = market_map[market]

    st.markdown("---")
    st.markdown("#### 🧑‍💼 选择分析师阵容")
    st.caption("选择参与本次分析的投资大师（至少1位）")

    selected_ids = []
    for group_name, ids in ANALYST_GROUPS.items():
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
                value=(aid in ["buffett", "munger", "graham", "lynch", "burry", "damodaran"]),
                key=f"analyst_{aid}",
                help=analyst["style"],
            )
            if checked:
                selected_ids.append(aid)

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

                # 计算 moat / dcf / tech
                buffett_res = analyze_buffett(fundamentals, normalized)
                moat = score_moat(fundamentals, normalized)
                dcf = calc_dcf(price, fundamentals, normalized) if price > 0 else {}
                tech = {}
                if df is not None and not df.empty:
                    df_ind = compute_indicators(df)
                    sig = generate_technical_signal(df_ind)
                    tech = {
                        "trend": sig.get("trend"),
                        "momentum": sig.get("momentum"),
                        "rsi": sig.get("rsi"),
                        "macd": sig.get("macd"),
                    }

                hf_result = run_hedge_fund(
                    symbol=ticker_input,
                    name=quote.get("shortName") or quote.get("longName") or ticker_input,
                    price=price,
                    fundamentals=fundamentals,
                    normalized=normalized,
                    moat=moat,
                    dcf=dcf,
                    tech=tech,
                    analyst_ids=selected_ids,
                    provider=provider,
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

        # ── Tab 切换：卡片 vs 表格 ────────────────────
        tab_cards, tab_table, tab_data = st.tabs(["📊 分析师详情", "📋 汇总表格", "🔧 原始数据"])

        with tab_cards:
            for analyst in r["analysts"]:
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

            styled = df_table.style.applymap(style_signal, subset=["信号"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

        with tab_data:
            st.markdown("**传给分析师的数据摘要：**")
            st.markdown(
                f'<div class="data-ctx-box">{r["data_context"]}</div>',
                unsafe_allow_html=True
            )

        st.caption(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 使用模型: {provider.model}")
