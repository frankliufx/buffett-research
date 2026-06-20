"""智能选股 — AI-powered full-market screener."""

import random
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st

from src.config import load_config, get_active_provider
from src.screener.ai_screener import INVESTMENT_PRINCIPLES, batch_evaluate
from src.screener.universe import (
    get_csi300_tickers,
    get_sp500_tickers,
    fetch_basic_fundamentals,
)
from src.ui_theme import get_global_css, COLORS

if "config" not in st.session_state:
    st.session_state.config = load_config()
config = st.session_state.config

st.markdown(get_global_css(), unsafe_allow_html=True)

st.markdown(
    """
<div style="text-align:center; padding:1.5rem 0 1.2rem 0; border-bottom:1px solid {border}; margin-bottom:1rem;">
    <h2 style="color:{text}; font-weight:300; letter-spacing:4px; margin:0;">智能选股</h2>
    <p style="color:{muted}; font-size:0.8rem; letter-spacing:2px; margin-top:0.4rem;">
        AI STOCK SCREENER · 沪深300 + S&amp;P500
    </p>
</div>
""".format(
        text=COLORS.get("text", "#EAEAEA"),
        muted=COLORS.get("text_muted", "#888888"),
        border=COLORS.get("border", "#1E1E26"),
    ),
    unsafe_allow_html=True,
)

# ── 投资原则展示 ──────────────────────────────────────────────────
with st.expander("📋 投资原则（10条，已内置）", expanded=False):
    for i, p in enumerate(INVESTMENT_PRINCIPLES, 1):
        st.markdown("**{}**. {}".format(i, p))

st.markdown("---")

# ── 分析参数 ──────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])
with col_left:
    st.markdown(
        '<div style="color:{c}; font-size:0.75rem; letter-spacing:1px;">扫描范围</div>'.format(
            c=COLORS["text_muted"]
        ),
        unsafe_allow_html=True,
    )
    markets = st.multiselect(
        "选择市场",
        options=["沪深300 (A股)", "S&P500 Top-100 (美股)"],
        default=["沪深300 (A股)", "S&P500 Top-100 (美股)"],
        label_visibility="collapsed",
    )

with col_right:
    max_stocks = st.number_input(
        "最多评估股票数", min_value=10, max_value=200, value=50, step=10,
        help="限制AI评估数量以控制耗时和费用"
    )

# ── 启动按钮 ──────────────────────────────────────────────────────
provider = get_active_provider(config)
if not provider:
    st.warning("⚠️ 请先在 Settings → API 激活一个有效的 API Provider（需要 OpenRouter key）")
    st.stop()

if provider.provider != "openai_compatible":
    st.warning(
        "⚠️ 智能选股目前仅支持 OpenAI 兼容的 provider（如 OpenRouter / DeepSeek）。"
        "请在 Settings → API 切换到 OpenRouter provider，或使用顶部快速切换按钮。"
    )
    st.stop()

if "screener_results" not in st.session_state:
    st.session_state.screener_results = None

start_col, _ = st.columns([1, 3])
with start_col:
    start_btn = st.button(
        "🚀 开始分析",
        type="primary",
        use_container_width=True,
        disabled=not markets,
    )

if start_btn:
    st.session_state.screener_results = None

    with st.spinner("正在获取股票池…"):
        universe = []
        if "沪深300 (A股)" in markets:
            universe += get_csi300_tickers()
        if "S&P500 Top-100 (美股)" in markets:
            universe += get_sp500_tickers()

    if not universe:
        st.error("无法获取股票列表，请检查网络或 AKShare 配置。")
        st.stop()

    if len(universe) > max_stocks:
        universe = random.sample(universe, int(max_stocks))
    universe.sort(key=lambda x: x[0])

    st.info("共 {} 只股票进入AI分析队列…".format(len(universe)))

    # ── 获取基本面数据 ──────────────────────────────────────────
    progress_bar = st.progress(0, text="获取基本面数据…")

    fundamentals_map = {}
    total = len(universe)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_basic_fundamentals, sym): sym for sym, _ in universe}
        done = 0
        for f in as_completed(futures):
            sym = futures[f]
            fundamentals_map[sym] = f.result()
            done += 1
            progress_bar.progress(done / (total * 2), text="获取基本面: {}/{}".format(done, total))

    # ── AI评估 ────────────────────────────────────────────────
    def _on_progress(done: int, total: int) -> None:
        progress_bar.progress(0.5 + done / (total * 2), text="AI分析: {}/{}".format(done, total))

    all_results = batch_evaluate(
        universe,
        fundamentals_map,
        provider,
        max_workers=5,
        progress_callback=_on_progress,
    )

    progress_bar.progress(1.0, text="分析完成！")
    st.session_state.screener_results = all_results
    st.rerun()

# ── 结果展示 ──────────────────────────────────────────────────────
if st.session_state.screener_results:
    results = st.session_state.screener_results

    st.markdown("### 📊 分析结果 — {} 只股票".format(len(results)))

    _GOLD = COLORS.get("gold", "#C9A962")
    _MUTED = COLORS.get("text_muted", "#888888")
    _RED = "#E05252"

    categories = {
        "强烈关注": ("🟢", _GOLD),
        "持续观察": ("🟡", _MUTED),
        "回避": ("🔴", _RED),
    }

    for cat, (icon, color) in categories.items():
        cat_stocks = [r for r in results if r["category"] == cat]
        if not cat_stocks:
            continue
        st.markdown(
            '<div style="color:{c}; font-size:0.8rem; letter-spacing:2px; margin:1.2rem 0 0.5rem;">'
            "{icon} {cat} · {n}只"
            "</div>".format(c=color, icon=icon, cat=cat, n=len(cat_stocks)),
            unsafe_allow_html=True,
        )
        for r in cat_stocks:
            c1, c2, c3 = st.columns([1, 5, 1])
            with c1:
                st.metric("评分", r["score"])
            with c2:
                st.markdown("**{}** {}".format(r["symbol"], r["name"]))
                st.caption(r["rationale"])
            with c3:
                st.markdown(
                    '<div style="color:{c}; font-size:1.2rem; text-align:right;">{icon}</div>'.format(
                        c=color, icon=icon
                    ),
                    unsafe_allow_html=True,
                )
            st.divider()

    df_out = pd.DataFrame(results)[["symbol", "name", "score", "category", "rationale"]]
    df_out.columns = ["代码", "名称", "评分", "分类", "AI理由"]
    st.download_button(
        "⬇️ 下载完整结果 CSV",
        df_out.to_csv(index=False).encode("utf-8-sig"),
        file_name="screener_results.csv",
        mime="text/csv",
    )
