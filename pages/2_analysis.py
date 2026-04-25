"""股票分析页 — A股 / 港股 / 美股 | 高端金融风"""

import logging
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from src.config import get_active_provider, get_premium_provider, StockItem
from src.auth import get_current_user
from src.user_data import can_analyze, increment_usage, FREE_MONTHLY_LIMIT
from src.data.stock_search import search_stocks, get_popular_stocks
from src.data.peers import get_peers
from src.tracker import (
    save_analysis_record, get_latest_analysis, load_stock_thesis,
    save_stock_thesis, build_history_context,
)
from src.data.price import fetch_history, fetch_quote
from src.data.financial import fetch_fundamentals
from src.data.news import fetch_stock_news, fetch_earnings_calendar, fetch_market_news
from src.analysis.technical import compute_indicators, generate_technical_signal
from src.analysis.fundamental import analyze_buffett, _normalize_fundamentals
from src.analysis.moat import score_moat
from src.analysis.signals import AnalysisResult
from src.ai.summarizer import (analyze_stock, generate_market_overview, get_ai_brief,
                                get_ai_insights, get_ashare_brief, analyze_ashare_stock)
from src.ai.knowledge_base import BUFFETT_PHILOSOPHY, DUAN_YONGPING_PHILOSOPHY
from src.analysis.valuation import calc_dcf, calc_multi_model_valuation
from src.analysis.risk import calculate_volatility, calculate_position_limit, generate_risk_report
from src.analysis.technical import generate_ensemble_signal
from src.ai.committee import convene_committee
from src.ui_committee import render_committee_page
from src.ui_valuation import (render_valuation_verdict, render_price_spectrum,
                               render_scenario_cards, render_assumptions_panel,
                               render_insight_cards, render_share_card)
from src.data.policy import get_stock_policy_tags, get_fifteen_five_alignment, get_policy_news
from src.ui_ashare import render_policy_hero, render_ashare_score_banner
from src.ui_theme import (get_global_css, render_hero_header, render_buffett_quote,
                          render_grade_badge, render_moat_bar, render_detail_item,
                          render_stock_header, render_moat_dimension,
                          render_kpi_card, render_sidebar_status,
                          render_empty_state, render_news_item,
                          render_calendar_card, COLORS)

logging.basicConfig(level=logging.WARNING)

# ===== 全局样式 =====
st.markdown(get_global_css(), unsafe_allow_html=True)

# ===== AI 分析动画样式 =====
_AI_LOADING_CSS = """
<style>
@keyframes ai-pulse {
    0%, 100% { opacity: 0.4; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.05); }
}
@keyframes ai-scan {
    0% { left: 10%; }
    50% { left: 70%; }
    100% { left: 10%; }
}
@keyframes ai-dot {
    0%, 20% { opacity: 0; }
    40% { opacity: 1; }
    100% { opacity: 0; }
}
.ai-loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 32px 0;
    gap: 16px;
}
.ai-loading-icon {
    position: relative;
    width: 64px;
    height: 64px;
}
.ai-loading-icon svg {
    animation: ai-pulse 2s ease-in-out infinite;
}
.ai-loading-bar {
    width: 200px;
    height: 3px;
    background: #1E1E26;
    border-radius: 2px;
    position: relative;
    overflow: hidden;
}
.ai-loading-bar::after {
    content: '';
    position: absolute;
    width: 40%;
    height: 100%;
    background: linear-gradient(90deg, transparent, #C9A962, transparent);
    border-radius: 2px;
    animation: ai-scan 2s ease-in-out infinite;
}
.ai-loading-text {
    font-size: 0.82rem;
    color: #6A6A78;
    letter-spacing: 1px;
}
.ai-loading-text .dot1 { animation: ai-dot 1.4s 0s infinite; }
.ai-loading-text .dot2 { animation: ai-dot 1.4s 0.2s infinite; }
.ai-loading-text .dot3 { animation: ai-dot 1.4s 0.4s infinite; }
</style>
"""
st.markdown(_AI_LOADING_CSS, unsafe_allow_html=True)

# 放大镜 SVG 动画
_AI_LOADING_SVG = """
<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="28" cy="28" r="16" stroke="#C9A962" stroke-width="2.5" fill="none" opacity="0.6"/>
  <circle cx="28" cy="28" r="8" stroke="#C9A962" stroke-width="1.5" fill="none" stroke-dasharray="4 3" opacity="0.4">
    <animateTransform attributeName="transform" type="rotate" from="0 28 28" to="360 28 28" dur="3s" repeatCount="indefinite"/>
  </circle>
  <line x1="40" y1="40" x2="54" y2="54" stroke="#C9A962" stroke-width="3" stroke-linecap="round" opacity="0.7"/>
  <circle cx="28" cy="28" r="3" fill="#C9A962" opacity="0.3">
    <animate attributeName="r" values="2;5;2" dur="2s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.3;0.6;0.3" dur="2s" repeatCount="indefinite"/>
  </circle>
</svg>
"""

def _show_ai_loading(text="AI 正在深入分析这支股票"):
    """显示高品质 AI 分析动画"""
    return st.markdown(
        '<div class="ai-loading-container">'
        '<div class="ai-loading-icon">' + _AI_LOADING_SVG + '</div>'
        '<div class="ai-loading-bar"></div>'
        '<div class="ai-loading-text">' + text
        + '<span class="dot1">.</span><span class="dot2">.</span><span class="dot3">.</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ===== 缓存（含错误边界：单项失败不影响整页）=====
@st.cache_data(ttl=86400, show_spinner=False)
def cached_get_policy_data(symbol):
    """A股专用：获取政策概念数据（24h缓存）"""
    try:
        alignment = get_fifteen_five_alignment(symbol)
        news = get_policy_news(limit=5)
        return alignment, news
    except Exception as e:
        logging.warning("policy data failed %s: %s", symbol, e)
        return {"level": "暂无明显政策主题", "score": 0, "color": "#5A5A6A",
                "tier1": [], "tier2": [], "all_tags": []}, []

@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch_history(symbol, market, days):
    try:
        return fetch_history(symbol, market, days)
    except Exception as e:
        logging.warning("fetch_history failed %s: %s", symbol, e)
        return pd.DataFrame()

@st.cache_data(ttl=1800, show_spinner=False)
def cached_fetch_quote(symbol, market):
    try:
        return fetch_quote(symbol, market)
    except Exception as e:
        logging.warning("fetch_quote failed %s: %s", symbol, e)
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch_fundamentals(symbol, market):
    try:
        return fetch_fundamentals(symbol, market)
    except Exception as e:
        logging.warning("fetch_fundamentals failed %s: %s", symbol, e)
        return {}

@st.cache_data(ttl=900, show_spinner=False)
def cached_fetch_news(symbol, market, limit=8):
    try:
        return fetch_stock_news(symbol, market, limit)
    except Exception as e:
        logging.warning("fetch_news failed %s: %s", symbol, e)
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch_calendar(symbol, market):
    try:
        return fetch_earnings_calendar(symbol, market)
    except Exception as e:
        logging.warning("fetch_calendar failed %s: %s", symbol, e)
        return []

@st.cache_data(ttl=1800, show_spinner=False)
def cached_fetch_market_news(market, limit=6):
    try:
        return fetch_market_news(market, limit)
    except Exception as e:
        logging.warning("fetch_market_news failed %s: %s", market, e)
        return []


def run_analysis(symbol, name, market, config):
    df = cached_fetch_history(symbol, market, config.technical.lookback_days)
    quote = cached_fetch_quote(symbol, market)
    fundamentals = cached_fetch_fundamentals(symbol, market)
    normalized = _normalize_fundamentals(fundamentals)

    if not df.empty:
        df = compute_indicators(df.copy(), config.technical)
        tech_signal = generate_technical_signal(df)
    else:
        tech_signal = {"trend": "unknown", "momentum": "unknown", "signals": [], "trend_score": 0}

    buffett_result = analyze_buffett(fundamentals, config.buffett_strategy)
    moat_result = score_moat(fundamentals, normalized, tech_signal)

    result = AnalysisResult(
        symbol=symbol, name=name, market=market,
        price=quote.get("price", 0) or tech_signal.get("price", 0),
        change_pct=quote.get("change_pct", 0),
        tech_signal=tech_signal, buffett_result=buffett_result,
        fundamentals=fundamentals,
    )
    result.compute_overall()
    return result, df, fundamentals, normalized, moat_result, quote


# ===== K线图 (暗色主题) =====
PLOT_LAYOUT = dict(
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=COLORS["text_secondary"], size=11),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10, color=COLORS["text_muted"])),
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
    yaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
)


def plot_candlestick(df, symbol, name):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_heights=[0.75, 0.25])

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="K",
        increasing_line_color=COLORS["success"],
        decreasing_line_color=COLORS["danger"],
        increasing_fillcolor=COLORS["success"],
        decreasing_fillcolor=COLORS["danger"],
    ), row=1, col=1)

    sma_colors = {"SMA_20": COLORS["primary"], "SMA_50": COLORS["info"], "SMA_200": "#A78BFA"}
    for col_name, color in sma_colors.items():
        if col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_name], name=col_name.replace("_", " "),
                line=dict(color=color, width=1),
            ), row=1, col=1)

    if "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"], name="BB",
                                 line=dict(color="rgba(201,169,98,0.3)", dash="dash"),
                                 showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_lower"], name="BB",
                                 line=dict(color="rgba(201,169,98,0.3)", dash="dash"),
                                 fill="tonexty", fillcolor="rgba(201,169,98,0.04)",
                                 showlegend=False), row=1, col=1)

    if "Volume" in df.columns:
        colors_vol = [COLORS["success"] if c >= o else COLORS["danger"]
                      for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="VOL",
                             marker_color=colors_vol, opacity=0.35), row=2, col=1)

    fig.update_layout(
        title=dict(text="{} {}".format(symbol, name), font=dict(color=COLORS["text"], size=14)),
        height=520, xaxis_rangeslider_visible=False,
        **PLOT_LAYOUT,
    )
    fig.update_xaxes(gridcolor=COLORS["border"], row=2, col=1)
    fig.update_yaxes(gridcolor=COLORS["border"], row=1, col=1)
    fig.update_yaxes(gridcolor=COLORS["border"], row=2, col=1)
    return fig


# ===== 护城河评分卡 V2 =====
_VERDICT_CSS = {
    "买入": "verdict-buy",
    "增持": "verdict-accumulate",
    "持有": "verdict-hold",
    "减持": "verdict-reduce",
    "回避": "verdict-avoid",
}
_CONFIDENCE_LABEL = {"高": "HIGH", "中": "MED", "低": "LOW"}


def render_moat_scorecard(moat, brief=None, normalized=None):
    """重设计的护城河评分卡 — 含 AI 简报"""
    grade = moat["grade"]
    pct = moat["percentage"]
    label = moat["label"]
    color = moat["color"]

    # ── 1. AI 投资结论横幅 ──────────────────────────────────────────
    if brief:
        verdict = brief.get("verdict", "持有")
        confidence = brief.get("confidence", "中")
        reason = brief.get("reason", "")
        css_cls = _VERDICT_CSS.get(verdict, "verdict-hold")
        conf_label = _CONFIDENCE_LABEL.get(confidence, confidence)
        st.markdown("""
        <div class="verdict-banner {css}">
            <div class="verdict-action">{verdict}</div>
            <div class="verdict-confidence">置信度 · {conf}</div>
            <div class="verdict-reason">{reason}</div>
        </div>
        """.format(css=css_cls, verdict=verdict, conf=conf_label, reason=reason),
        unsafe_allow_html=True)
    else:
        # 无 AI 时用本地结论
        local_action = moat.get("verdict", "")
        st.markdown("""
        <div style="background:#141419; border:1px solid #2A2A33; padding:12px 18px; margin-bottom:16px;
                    display:flex; align-items:center; gap:12px;">
            <span style="color:{color}; font-size:0.9rem; font-weight:600; letter-spacing:1px;">{label}</span>
            <span style="color:#5A5A68; font-size:0.82rem;">{verdict}</span>
        </div>
        """.format(color=color, label=label, verdict=local_action), unsafe_allow_html=True)

    # ── 2. 双列布局：左=评级面板，右=维度卡片 ─────────────────────────
    col_left, col_right = st.columns([1, 2])

    with col_left:
        # 关键指标
        pe_v = "{:.1f}".format(normalized["pe_trailing"]) if normalized and normalized.get("pe_trailing") else "--"
        pb_v = "{:.2f}".format(normalized["pb"]) if normalized and normalized.get("pb") else "--"
        roe_v = _fmt_pct(normalized.get("roe")) if normalized else "--"
        mcap = normalized.get("market_cap") if normalized else None

        st.markdown("""
        <div class="grade-panel">
            {badge}
            <div class="score-big">{pct:.0f}</div>
            <div class="score-label">/ 100 · 综合评分</div>
            <div style="margin:14px 0 8px;">
                <span class="moat-label" style="background:{color}18; color:{color}; font-size:0.72rem;">
                    {label}
                </span>
            </div>
            <div style="height:1px; background:#1E1E26; margin:12px 0;"></div>
            <div class="grade-stat-row"><span class="stat-k">PE</span><span class="stat-v">{pe}</span></div>
            <div class="grade-stat-row"><span class="stat-k">PB</span><span class="stat-v">{pb}</span></div>
            <div class="grade-stat-row"><span class="stat-k">ROE</span><span class="stat-v">{roe}</span></div>
            <div class="grade-stat-row"><span class="stat-k">市值</span><span class="stat-v">{mcap}</span></div>
        </div>
        """.format(
            badge=render_grade_badge(grade),
            pct=pct, color=color, label=label,
            pe=pe_v, pb=pb_v, roe=roe_v,
            mcap=_format_number(mcap) if mcap else "--",
        ), unsafe_allow_html=True)

    with col_right:
        dim_insights = brief.get("dimensions", {}) if brief else {}
        for cat_name, info in moat["scores"].items():
            icon = info.get("icon", "")
            score = info["score"]
            max_s = info["max"]
            pct_s = score / max_s * 100 if max_s > 0 else 0
            if pct_s >= 65:
                bar_color = COLORS["success"]
            elif pct_s >= 40:
                bar_color = COLORS["warning"]
            else:
                bar_color = COLORS["danger"]
            ai_text = dim_insights.get(cat_name, "")
            has_cls = "has-insight" if ai_text else ""
            display_text = ai_text if ai_text else moat.get("verdict", "")[:30] if cat_name == list(moat["scores"].keys())[0] else ""

            st.markdown("""
            <div class="dim-card-v2">
                <div class="dim-header-v2">
                    <span class="dim-icon-v2">{icon}</span>
                    <span class="dim-name-v2">{name}</span>
                    <span class="dim-score-v2">{score}/{max}</span>
                </div>
                <div class="dim-bar-bg-v2">
                    <div class="dim-bar-fill-v2" style="width:{pct:.0f}%; background:{color};"></div>
                </div>
                {insight_html}
            </div>
            """.format(
                icon=icon, name=cat_name, score=score, max=max_s, pct=pct_s, color=bar_color,
                insight_html='<div class="dim-ai-v2 {}">{}</div>'.format(has_cls, display_text) if display_text else "",
            ), unsafe_allow_html=True)

    # ── 3. 多空理由 ──────────────────────────────────────────────────
    if brief:
        bull = brief.get("bull_points", [])
        bear = brief.get("bear_points", [])
        if bull or bear:
            bull_items = "".join('<div class="bb-item">· {}</div>'.format(b) for b in bull)
            bear_items = "".join('<div class="bb-item">· {}</div>'.format(b) for b in bear)
            st.markdown("""
            <div class="bb-grid">
                <div class="bb-col bb-bull">
                    <div class="bb-title">✓ 核心优势</div>
                    {bull}
                </div>
                <div class="bb-col bb-bear">
                    <div class="bb-title">✗ 主要风险</div>
                    {bear}
                </div>
            </div>
            """.format(bull=bull_items, bear=bear_items), unsafe_allow_html=True)

    # ── 4. 详细分析折叠 ──────────────────────────────────────────────
    st.write("")
    with st.expander("查看详细维度分析"):
        for icon, text, level in moat["details"]:
            st.markdown(render_detail_item(icon, text, level), unsafe_allow_html=True)


# ===== 格式化 =====
def _fmt_pct(val):
    return "{:.1f}%".format(val) if val is not None else "--"

def _trend_label(t):
    return {"bullish": "BULLISH", "bearish": "BEARISH", "neutral": "NEUTRAL"}.get(t, "--")

def _momentum_label(m):
    return {"strong": "STRONG", "weak": "WEAK", "overbought": "OVERBOUGHT", "oversold": "OVERSOLD"}.get(m, "--")

def _format_number(n):
    if n is None: return "--"
    a = abs(float(n)); s = "-" if float(n) < 0 else ""
    if a >= 1e12: return "{}{}T".format(s, round(a/1e12, 1))
    if a >= 1e9: return "{}{}B".format(s, round(a/1e9, 1))
    if a >= 1e6: return "{}{}M".format(s, round(a/1e6, 1))
    if a >= 1e3: return "{}{}K".format(s, round(a/1e3, 1))
    return "{}{}".format(s, round(a))


def _format_revenue(n):
    """格式化营收预估 (美元)"""
    if n is None: return "--"
    a = abs(float(n))
    if a >= 1e9: return "${:.1f}B".format(a / 1e9)
    if a >= 1e6: return "${:.0f}M".format(a / 1e6)
    return "${:.0f}".format(a)


# ===== 投资委员会 + 风控 + 多模型估值 =====
def _render_committee_tab(symbol, name, market, result, fundamentals, normalized, moat, provider, df):
    """投资委员会标签页 — 单一HTML页面，Blackstone品质"""
    import streamlit.components.v1 as _cmp

    price = result.price or 0

    # 1. 五策略集成
    ensemble = generate_ensemble_signal(df) if df is not None and not df.empty else None

    # 2. 多模型估值
    multi_val = calc_multi_model_valuation(price, fundamentals, normalized) if price > 0 else None

    # 3. 风险管理
    vol = calculate_volatility(df) if df is not None and not df.empty else None
    pos = calculate_position_limit(vol)
    dcf_for_risk = calc_dcf(price, fundamentals, normalized) if price > 0 else None
    risk_report = generate_risk_report(vol, pos, dcf=dcf_for_risk)

    # 4. 委员会按钮
    committee_key = "committee_{}".format(symbol)
    if st.button("召集投资委员会", key="committee_btn_{}".format(symbol), type="primary"):
        if not provider:
            st.warning("请先在「设置」页面配置 API Key")
        else:
            loading = _show_ai_loading("5 位投资大师正在独立分析")
            dcf_for_comm = calc_dcf(price, fundamentals, normalized) if price > 0 else None
            comm = convene_committee(result, fundamentals, normalized, moat, dcf_for_comm, provider)
            st.session_state[committee_key] = comm
            loading.empty()

    committee_result = st.session_state.get(committee_key)

    # 单一 HTML 渲染
    page_html = render_committee_page(
        ensemble=ensemble,
        multi_val=multi_val,
        price=price,
        volatility=vol,
        position=pos,
        risk_report=risk_report,
        committee=committee_result,
    )

    # 动态高度计算
    h = 200  # base
    if ensemble and ensemble.get("strategies"):
        h += 220
    if multi_val:
        h += 280
    if risk_report:
        h += 180 + len(risk_report.get("recommendations", [])) * 30
    if committee_result:
        h += 320 + len(committee_result.get("members", [])) * 130

    _cmp.html(page_html, height=h, scrolling=True)


# ===== 渲染单只股票 =====
def _render_thesis_panel(uid: str, symbol: str, market: str, name: str,
                         moat: dict, prev_analysis):
    """投资论点面板 — 用户记忆层的核心界面。"""
    thesis = load_stock_thesis(uid, symbol, market)

    st.markdown(
        '<div style="font-size:0.6rem;letter-spacing:4px;color:#C9A962;'
        'text-transform:uppercase;font-weight:500;margin-bottom:4px;">My Investment Thesis</div>'
        '<div style="font-size:0.82rem;color:#5A5A6A;margin-bottom:20px;">'
        '记录你的买入理由和目标价——这些笔记会随着每次分析积累，成为你的私人投资档案。'
        '</div>',
        unsafe_allow_html=True,
    )

    col_l, col_r = st.columns([2, 1])

    with col_l:
        buy_thesis = st.text_area(
            "买入逻辑 / Buy Thesis",
            value=thesis.get("buy_thesis", "") if thesis else "",
            placeholder="你为什么看好这家公司？护城河在哪里？十年后它还在吗？",
            height=120,
            key="thesis_buy_{}_{}_{}".format(uid, market, symbol),
        )
        risk_watch = st.text_area(
            "风险关注点 / Risk Watch",
            value=thesis.get("risk_watch", "") if thesis else "",
            placeholder="什么情况会让你改变看法？竞争威胁？管理层变化？",
            height=90,
            key="thesis_risk_{}_{}_{}".format(uid, market, symbol),
        )
        notes = st.text_area(
            "备忘录 / Notes",
            value=thesis.get("notes", "") if thesis else "",
            placeholder="任何值得记录的想法、新闻、或操作记录…",
            height=80,
            key="thesis_notes_{}_{}_{}".format(uid, market, symbol),
        )

    with col_r:
        target_price = st.number_input(
            "目标价 / Target Price",
            value=float(thesis.get("target_price") or 0) if thesis else 0.0,
            min_value=0.0, step=0.1, format="%.2f",
            key="thesis_tp_{}_{}_{}".format(uid, market, symbol),
        )
        st.markdown("<br>", unsafe_allow_html=True)

        # 历史分析摘要
        if prev_analysis:
            _days = 0
            try:
                from datetime import datetime, timezone
                _dt = datetime.fromisoformat(
                    prev_analysis["analyzed_at"].replace("Z", "+00:00"))
                _days = (datetime.now(timezone.utc) - _dt).days
            except Exception:
                pass
            _ps = prev_analysis.get("score_total", 0)
            _cs = moat.get("percentage", 0)
            _delta = int(_cs - _ps)
            _dc = "#3ECF8E" if _delta > 0 else ("#EF4444" if _delta < 0 else "#5A5A6A")
            st.markdown(
                '<div style="background:#09090F;border:1px solid #1E1E26;padding:16px;'
                'border-radius:2px;">'
                '<div style="font-size:0.5rem;letter-spacing:3px;color:#C9A962;'
                'text-transform:uppercase;margin-bottom:12px;">分析历史</div>'
                '<div style="font-size:0.78rem;color:#5A5A6A;line-height:2;">'
                '上次分析：<span style="color:#9A9AA8;">{} 天前</span><br>'
                '上次评分：<span style="color:#C9A962;">{:.0f}</span> 分<br>'
                '本次评分：<span style="color:#E8E8F0;font-weight:600;">{:.0f}</span> 分'
                '&nbsp;<span style="color:{};">({:+d})</span>'
                '</div></div>'.format(_days, _ps, _cs, _dc, _delta),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:#09090F;border:1px solid #1E1E26;padding:16px;">'
                '<div style="font-size:0.5rem;letter-spacing:3px;color:#3A3A4A;'
                'text-transform:uppercase;margin-bottom:8px;">分析历史</div>'
                '<div style="font-size:0.75rem;color:#3A3A4A;">首次分析，记录已保存。</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    if st.button("保存论点", key="thesis_save_{}_{}_{}".format(uid, market, symbol), type="primary"):
        ok = save_stock_thesis(
            uid=uid, symbol=symbol, market=market,
            buy_thesis=buy_thesis,
            target_price=target_price if target_price > 0 else None,
            risk_watch=risk_watch,
            notes=notes,
        )
        if ok:
            st.success("论点已保存 ✓")
        else:
            st.error("保存失败，请重试。")


def _render_ashare_policy_tab(symbol, name, alignment, news, fundamentals, normalized, moat):
    """A股专属政策分析Tab"""
    import streamlit.components.v1 as components
    from src.ui_ashare import render_policy_hero

    # Section 1: 完整政策雷达（比顶部的更高更详细，height=600）
    hero_html = render_policy_hero(symbol, name, alignment,
                                   alignment.get("all_tags", []),
                                   news, fundamentals, normalized)
    components.html(hero_html, height=600, scrolling=True)

    # Section 2: 政策新闻完整列表（用 st.markdown 显示，最多10条）
    st.markdown(
        '<div style="font-size:0.6rem;letter-spacing:4px;color:#C9A962;'
        'text-transform:uppercase;font-weight:500;margin:24px 0 12px;">最新政策动态</div>',
        unsafe_allow_html=True,
    )
    if news:
        for item in news[:10]:
            title = item.get("title", "")
            date = item.get("date", "")
            source = item.get("source", "人民网")
            st.markdown(
                '<div style="background:#0C0C12;border:1px solid #1E1E26;'
                'border-left:2px solid #C9A962;padding:10px 14px;margin-bottom:8px;'
                'border-radius:2px;">'
                '<span style="font-size:0.58rem;color:#5A5A6A;letter-spacing:1px;">'
                '{date} · {source}</span><br>'
                '<span style="font-size:0.75rem;color:#C8C8D8;line-height:1.5;">'
                '{title}</span></div>'.format(date=date[:10] if date else "", source=source, title=title[:80]),
                unsafe_allow_html=True,
            )
    else:
        st.info("暂无政策新闻（人民网数据加载中...）")

    # Section 3: 申万行业 + 政策评分说明
    st.markdown(
        '<div style="font-size:0.6rem;letter-spacing:4px;color:#C9A962;'
        'text-transform:uppercase;font-weight:500;margin:24px 0 12px;">评分说明</div>',
        unsafe_allow_html=True,
    )
    level = alignment.get("level", "暂无明显政策主题")
    tier1 = alignment.get("tier1", [])
    tier2 = alignment.get("tier2", [])
    score = alignment.get("score", 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("十五五对齐级别", level)
    with col2:
        st.metric("政策得分", "{}/15".format(score))
    with col3:
        st.metric("概念板块数量", len(alignment.get("all_tags", [])))

    if tier1:
        st.markdown("**核心主线：** " + " · ".join(tier1[:6]))
    if tier2:
        st.markdown("**受益方向：** " + " · ".join(tier2[:6]))


def render_stock_analysis(symbol, name, market, config):
    provider = get_active_provider(config)

    # 数据分析
    loading_placeholder = st.empty()
    loading_placeholder.markdown(
        '<div class="ai-loading-container">'
        '<div class="ai-loading-icon">' + _AI_LOADING_SVG + '</div>'
        '<div class="ai-loading-bar"></div>'
        '<div class="ai-loading-text">正在分析 ' + name
        + '<span class="dot1">.</span><span class="dot2">.</span><span class="dot3">.</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    try:
        result, df, fundamentals, normalized, moat, quote = run_analysis(symbol, name, market, config)
    except Exception as e:
        loading_placeholder.empty()
        st.error("Error: {} — {}".format(symbol, e))
        return None

    # ── 飞轮：读取历史记录，构建 AI 上下文 ──────────────
    _cur_user = get_current_user() or {}
    _uid = _cur_user.get("username", "anonymous")
    prev_analysis = get_latest_analysis(_uid, symbol, market)
    hist_ctx = build_history_context(prev_analysis, result.price or 0)

    # ── 竞品对比上下文（后台静默获取，不影响主流程）─────
    peer_ctx = ""
    _peer_key = "_peers_{}_{}".format(market, symbol)
    if _peer_key not in st.session_state:
        peers = get_peers(symbol, market)
        if peers:
            peer_lines = ["## 同行竞品对比（供参考，数据可能有延迟）"]
            for p in peers:
                try:
                    p_fund = fetch_fundamentals(p["symbol"], p["market"])
                    p_roe = p_fund.get("roe")
                    p_pe  = p_fund.get("pe_trailing")
                    p_gm  = p_fund.get("gross_margin")
                    p_roe_str = "{:.1f}%".format(p_roe * 100) if p_roe else "N/A"
                    p_pe_str  = "{:.1f}".format(p_pe) if p_pe else "N/A"
                    p_gm_str  = "{:.1f}%".format(p_gm * 100) if p_gm else "N/A"
                    peer_lines.append(
                        "- {name}（{sym}）: ROE {roe} | PE {pe} | 毛利率 {gm}".format(
                            name=p["name"], sym=p["symbol"],
                            roe=p_roe_str, pe=p_pe_str, gm=p_gm_str,
                        )
                    )
                except Exception:
                    peer_lines.append("- {}（{}）: 数据获取失败".format(p["name"], p["symbol"]))
            peer_lines.append("请在分析中对比 {name} 与竞品的相对优劣势。".format(name=name))
            peer_ctx = "\n".join(peer_lines)
        st.session_state[_peer_key] = peer_ctx
    else:
        peer_ctx = st.session_state[_peer_key]

    # ── A股：加载政策数据 ────────────────────────────────
    _policy_alignment, _policy_news = (None, [])
    if market == "a_share":
        _policy_alignment, _policy_news = cached_get_policy_data(symbol)

    # ── 自动加载 AI 简报（含历史上下文 + 竞品对比）──────
    brief_key = "ai_brief_{}".format(symbol)
    if brief_key not in st.session_state:
        if provider:
            loading_placeholder.markdown(
                '<div class="ai-loading-container">'
                '<div class="ai-loading-icon">' + _AI_LOADING_SVG + '</div>'
                '<div class="ai-loading-bar"></div>'
                '<div class="ai-loading-text">AI 正在深入分析 ' + name
                + '<span class="dot1">.</span><span class="dot2">.</span><span class="dot3">.</span></div>'
                '</div>',
                unsafe_allow_html=True,
            )
            if market == "a_share" and _policy_alignment:
                st.session_state[brief_key] = get_ashare_brief(
                    result, moat, _policy_alignment, provider,
                    history_context=hist_ctx, peer_context=peer_ctx,
                    policy_news=_policy_news,
                )
            else:
                st.session_state[brief_key] = get_ai_brief(
                    result, moat, provider, history_context=hist_ctx, peer_context=peer_ctx
                )
        else:
            st.session_state[brief_key] = None
    brief = st.session_state.get(brief_key)
    loading_placeholder.empty()

    # ── 飞轮：自动存档本次分析快照 ───────────────────
    _save_key = "_saved_{}_{}".format(market, symbol)
    if _save_key not in st.session_state:
        save_analysis_record(
            uid=_uid, symbol=symbol, market=market, name=name,
            price=result.price or 0,
            moat_result=moat, brief=brief,
            fundamentals=fundamentals,
        )
        st.session_state[_save_key] = True

    # ── 历史对比 banner（如有上次记录）──────────────────
    if prev_analysis:
        _prev_score = prev_analysis.get("score_total", 0)
        _cur_score  = moat.get("percentage", 0)
        _delta      = _cur_score - _prev_score
        _prev_price = prev_analysis.get("price") or 0
        _days_ago   = 0
        try:
            from datetime import datetime, timezone
            _dt = datetime.fromisoformat(
                prev_analysis["analyzed_at"].replace("Z", "+00:00"))
            _days_ago = (datetime.now(timezone.utc) - _dt).days
        except Exception:
            pass
        _price_chg = ""
        if _prev_price and result.price:
            _pct = (result.price - _prev_price) / _prev_price * 100
            _price_chg = " | 价格 {:+.1f}%".format(_pct)
        _score_str = "{:+d}分".format(int(_delta)) if _delta else "持平"
        _delta_color = "#3ECF8E" if _delta > 0 else ("#EF4444" if _delta < 0 else "#5A5A6A")
        st.markdown(
            '<div style="background:#0C0C12;border:1px solid #1E1E26;border-left:3px solid #C9A962;'
            'padding:10px 16px;margin-bottom:16px;font-size:0.78rem;color:#6A6A78;'
            'display:flex;align-items:center;gap:8px;">'
            '📋 <span style="color:#9A9AA8;">上次分析：{}天前</span>'
            '&nbsp;|&nbsp;评分 <span style="color:#C9A962;">{}</span> → '
            '<span style="color:#E8E8F0;font-weight:600;">{}</span>'
            '&nbsp;<span style="color:{};">（{}）</span>{}'
            '</div>'.format(
                _days_ago, int(_prev_score), int(_cur_score),
                _delta_color, _score_str, _price_chg
            ),
            unsafe_allow_html=True,
        )

    # ===== 头部 =====
    price, change = result.price, result.change_pct
    st.markdown(render_stock_header(
        symbol, name, price, change,
        moat["grade"], moat["label"], moat["color"], moat["percentage"]
    ), unsafe_allow_html=True)

    # ===== 估值/政策中枢（A股走政策逻辑，美股/港股走DCF）=====
    premium_provider = get_premium_provider(config)
    if market == "a_share" and _policy_alignment is not None:
        import streamlit.components.v1 as _cmp_ashare
        # 政策评分横幅
        tech_score = result.tech_signal.get("trend_score", 50) if result.tech_signal else 50
        banner_html = render_ashare_score_banner(
            _policy_alignment,
            moat_score=moat.get("percentage", 0),
            tech_score=tech_score,
        )
        _cmp_ashare.html(banner_html, height=90, scrolling=False)
        # 政策雷达主面板
        hero_html = render_policy_hero(
            symbol, name, _policy_alignment, _policy_alignment.get("all_tags", []),
            _policy_news, fundamentals, normalized,
        )
        _cmp_ashare.html(hero_html, height=520, scrolling=False)
    else:
        _render_valuation_hero(symbol, name, market, price, fundamentals, normalized, quote,
                               tech_signal=result.tech_signal, provider=premium_provider)

    # ===== Share Card =====
    currency_map = {"us": "$", "hk": "HK$", "a_share": "¥"}
    _share_currency = currency_map.get(market, "$")
    _dcf_for_share = calc_dcf(price, fundamentals, normalized)

    with st.expander("Share This Analysis", expanded=False):
        share_html = render_share_card(symbol, name, price, _dcf_for_share,
                                       moat, normalized, _share_currency)
        import streamlit.components.v1 as _components
        _components.html(share_html, height=480, scrolling=False)
        st.caption("Screenshot this card and share with friends. Watermarked with AI Buffett branding.")

    # ===== Tabs =====
    if market == "a_share":
        tab_policy, tab_moat, tab_trend, tab_chart, tab_finance, tab_tech, tab_ai, tab_committee, tab_thesis = st.tabs(
            ["🏛️ 政策", "MOAT", "TREND", "CHART", "FINANCIALS", "TECHNICAL", "AI REPORT", "🏛 COMMITTEE", "📋 MY THESIS"]
        )
    else:
        tab_policy = None
        tab_moat, tab_trend, tab_chart, tab_finance, tab_tech, tab_ai, tab_committee, tab_thesis = st.tabs(
            ["MOAT", "TREND", "CHART", "FINANCIALS", "TECHNICAL", "AI REPORT", "🏛 COMMITTEE", "📋 MY THESIS"]
        )

    if market == "a_share" and tab_policy is not None:
        with tab_policy:
            _render_ashare_policy_tab(symbol, name, _policy_alignment, _policy_news, fundamentals, normalized, moat)

    with tab_moat:
        render_moat_scorecard(moat, brief=brief, normalized=normalized)

        # ── 同行竞品对比卡片 ──────────────────────────────────────
        _peer_ctx_stored = st.session_state.get("_peers_{}_{}".format(market, symbol), "")
        if _peer_ctx_stored:
            st.markdown(
                '<div style="font-size:0.5rem;letter-spacing:4px;color:#C9A962;'
                'text-transform:uppercase;margin:24px 0 8px;">Peer Comparison</div>',
                unsafe_allow_html=True,
            )
            peers = get_peers(symbol, market)
            if peers:
                _peer_cols = st.columns(len(peers))
                for _pi, (_pc, _pp) in enumerate(zip(_peer_cols, peers)):
                    with _pc:
                        try:
                            _pf = fetch_fundamentals(_pp["symbol"], _pp["market"])
                            _p_roe = _pf.get("roe")
                            _p_pe  = _pf.get("pe_trailing")
                            _p_gm  = _pf.get("gross_margin")
                            _p_roe_s = "{:.1f}%".format(_p_roe * 100) if _p_roe else "--"
                            _p_pe_s  = "{:.1f}x".format(_p_pe)        if _p_pe  else "--"
                            _p_gm_s  = "{:.1f}%".format(_p_gm * 100)  if _p_gm  else "--"
                        except Exception:
                            _p_roe_s = _p_pe_s = _p_gm_s = "--"
                        st.markdown(
                            '<div style="background:#09090F;border:1px solid #1E1E26;'
                            'padding:14px 16px;border-radius:2px;">'
                            '<div style="font-size:0.6rem;color:#C9A962;font-weight:600;'
                            'letter-spacing:1px;margin-bottom:8px;">{sym}</div>'
                            '<div style="font-size:0.65rem;color:#5A5A6A;margin-bottom:10px;">{name}</div>'
                            '<div style="font-size:0.72rem;color:#7A7A88;line-height:2;">'
                            'ROE: <span style="color:#C8C8D8;">{roe}</span><br>'
                            'PE: <span style="color:#C8C8D8;">{pe}</span><br>'
                            '毛利率: <span style="color:#C8C8D8;">{gm}</span>'
                            '</div></div>'.format(
                                sym=_pp["symbol"], name=_pp["name"][:12],
                                roe=_p_roe_s, pe=_p_pe_s, gm=_p_gm_s,
                            ),
                            unsafe_allow_html=True,
                        )

        # ── 巴菲特估值参考面板 ──
        _render_valuation_reference(symbol, normalized, moat)

    with tab_trend:
        _render_trend_analysis(symbol, name, market, price, change, df, normalized, moat, result, provider)

    with tab_chart:
        if not df.empty:
            st.plotly_chart(plot_candlestick(df, symbol, name), use_container_width=True)
        else:
            st.markdown(render_empty_state("--", "No historical data"), unsafe_allow_html=True)

    with tab_finance:
        # KPI row 1
        metrics = [
            ("PE", "{:.1f}".format(normalized['pe_trailing']) if normalized.get('pe_trailing') else "--"),
            ("PB", "{:.2f}".format(normalized['pb']) if normalized.get('pb') else "--"),
            ("ROE", _fmt_pct(normalized.get("roe"))),
            ("NET MARGIN", _fmt_pct(normalized.get("profit_margin"))),
            ("GROSS MARGIN", _fmt_pct(normalized.get("gross_margin"))),
        ]
        cols = st.columns(5)
        for i, (k, v) in enumerate(metrics):
            with cols[i]:
                st.markdown(render_kpi_card(k, v), unsafe_allow_html=True)

        st.write("")

        # KPI row 2
        metrics2 = [
            ("D/E RATIO", "{:.2f}".format(normalized['debt_to_equity']) if normalized.get('debt_to_equity') is not None else "--"),
            ("CURRENT RATIO", "{:.2f}".format(normalized['current_ratio']) if normalized.get('current_ratio') else "--"),
            ("REV GROWTH", _fmt_pct(normalized.get("revenue_growth"))),
            ("EPS GROWTH", _fmt_pct(normalized.get("earnings_growth"))),
            ("FCF", _format_number(normalized.get("free_cashflow"))),
        ]
        cols2 = st.columns(5)
        for i, (k, v) in enumerate(metrics2):
            with cols2[i]:
                st.markdown(render_kpi_card(k, v), unsafe_allow_html=True)

        # ROE history
        roe_hist = normalized.get("roe_history", [])
        if len(roe_hist) >= 3:
            st.write("")
            st.markdown('<div style="color:{}; font-size:0.8rem; letter-spacing:1px; margin-bottom:0.5rem;">ROE TREND</div>'.format(
                COLORS["text_muted"]), unsafe_allow_html=True)
            roe_df = pd.DataFrame({"ROE": list(reversed(roe_hist)),
                                   "Year": ["Y{}".format(i+1) for i in range(len(roe_hist))]})
            fig_roe = go.Figure()
            fig_roe.add_trace(go.Bar(
                x=roe_df["Year"], y=roe_df["ROE"], name="ROE",
                marker_color=[COLORS["primary"] if r >= 15 else COLORS["danger"]
                              for r in reversed(roe_hist)],
                marker_line_width=0,
            ))
            fig_roe.add_hline(y=15, line_dash="dash", line_color=COLORS["primary"],
                              line_width=1, annotation_text="15%",
                              annotation_font_color=COLORS["primary"])
            fig_roe.update_layout(height=220, **PLOT_LAYOUT)
            st.plotly_chart(fig_roe, use_container_width=True)

    with tab_tech:
        c1, c2, c3 = st.columns(3)
        tech = result.tech_signal

        trend = tech.get("trend", "")
        trend_color = "positive" if trend == "bullish" else ("negative" if trend == "bearish" else "")
        momentum = tech.get("momentum", "")
        mom_color = "positive" if momentum == "strong" else ("negative" if momentum in ("weak", "overbought") else "")
        rsi_val = tech.get("rsi")
        rsi_color = "negative" if rsi_val and rsi_val > 70 else ("positive" if rsi_val and rsi_val < 30 else "")

        with c1:
            st.markdown(render_kpi_card("TREND", _trend_label(trend), trend_color), unsafe_allow_html=True)
        with c2:
            st.markdown(render_kpi_card("MOMENTUM", _momentum_label(momentum), mom_color), unsafe_allow_html=True)
        with c3:
            st.markdown(render_kpi_card("RSI", "{:.1f}".format(rsi_val) if rsi_val is not None else "--", rsi_color), unsafe_allow_html=True)

        if tech.get("signals"):
            st.write("")
            for s in tech["signals"]:
                st.markdown('<div style="color:{}; font-size:0.85rem; padding:3px 0;">· {}</div>'.format(
                    COLORS["text_secondary"], s), unsafe_allow_html=True)

        if not df.empty and "RSI" in df.columns:
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                                         line=dict(color=COLORS["primary"], width=1.5),
                                         fill="tozeroy", fillcolor="rgba(201,169,98,0.05)"))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color=COLORS["danger"],
                              line_width=0.8, annotation_text="70",
                              annotation_font_color=COLORS["danger"])
            fig_rsi.add_hline(y=30, line_dash="dash", line_color=COLORS["success"],
                              line_width=0.8, annotation_text="30",
                              annotation_font_color=COLORS["success"])
            fig_rsi.update_layout(height=200, **PLOT_LAYOUT)
            st.plotly_chart(fig_rsi, use_container_width=True)

    with tab_ai:
        ai_key = "ai_analysis_{}".format(symbol)
        _btn_label = "生成A股政策研报" if market == "a_share" else "生成深度研报"
        if st.button(_btn_label, key="ai_btn_{}".format(symbol), type="primary"):
            if not provider:
                st.warning("请先在「设置」页面配置 API Key")
            else:
                ai_loading = st.empty()
                ai_loading.markdown(
                    '<div class="ai-loading-container">'
                    '<div class="ai-loading-icon">' + _AI_LOADING_SVG + '</div>'
                    '<div class="ai-loading-bar"></div>'
                    '<div class="ai-loading-text">AI 正在撰写深度研报'
                    '<span class="dot1">.</span><span class="dot2">.</span><span class="dot3">.</span></div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if market == "a_share":
                    ai_text = analyze_ashare_stock(
                        result, provider, moat=moat,
                        policy_data=_policy_alignment, policy_news=_policy_news,
                    )
                else:
                    ai_text = analyze_stock(result, provider=provider, moat=moat)
                st.session_state[ai_key] = ai_text
                ai_loading.empty()

        if ai_key in st.session_state:
            st.markdown(st.session_state[ai_key])
            st.write("")
            if st.button("Discuss this stock", key="chat_jump_{}".format(symbol)):
                st.session_state["chat_context_stock"] = {
                    "symbol": symbol, "name": name,
                    "grade": moat["grade"], "label": moat["label"],
                    "score": moat["percentage"],
                    "analysis": st.session_state[ai_key],
                }
                st.switch_page("pages/3_chat.py")
        else:
            st.markdown(render_empty_state("--",
                "AI Deep Analysis",
                "Click the button above to generate a Buffett-style research report"),
                unsafe_allow_html=True)

    # ── 投资委员会 Tab ──────────────────────────────────────────────
    with tab_committee:
        _render_committee_tab(symbol, name, market, result, fundamentals, normalized, moat, provider, df)

    # ── 投资论点 Tab ────────────────────────────────────────────────
    with tab_thesis:
        _render_thesis_panel(_uid, symbol, market, name, moat, prev_analysis)

    # ═══════════════════════════════════════════════════════════════
    # AI 综合建议 — 产品核心能力
    # ═══════════════════════════════════════════════════════════════
    _render_ai_verdict(symbol, name, market, price, change, moat, normalized, result, provider)

    return result, moat


def _render_trend_analysis(symbol, name, market, price, change, df, normalized, moat, result, provider):
    """阶段性行情分析 — 用价值投资视角解读近期涨跌"""

    trend_key = "ai_trend_{}".format(symbol)

    # 先展示量化行情概览（不依赖 AI，秒出）
    tech = result.tech_signal

    # 计算近期行情数据
    pct_5d, pct_20d, pct_60d = None, None, None
    high_52w = normalized.get("52w_high") if normalized.get("52w_high") else None
    low_52w = normalized.get("52w_low") if normalized.get("52w_low") else None

    if not df.empty and len(df) > 5:
        pct_5d = round((df["Close"].iloc[-1] / df["Close"].iloc[-5] - 1) * 100, 2) if len(df) > 5 else None
        pct_20d = round((df["Close"].iloc[-1] / df["Close"].iloc[-20] - 1) * 100, 2) if len(df) > 20 else None
        pct_60d = round((df["Close"].iloc[-1] / df["Close"].iloc[-60] - 1) * 100, 2) if len(df) > 60 else None

    # 行情概览卡片
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        if change is not None:
            delta_str = ("+" if change >= 0 else "") + str(round(change, 2)) + "%"
            st.metric("今日", str(price), delta_str)
        else:
            st.metric("今日", str(price), "N/A")
    with m2:
        if pct_5d is not None:
            st.metric("近5日", ("+" if pct_5d >= 0 else "") + str(pct_5d) + "%", "短期动量")
        else:
            st.metric("近5日", "--", "")
    with m3:
        if pct_20d is not None:
            st.metric("近20日", ("+" if pct_20d >= 0 else "") + str(pct_20d) + "%", "月度趋势")
        else:
            st.metric("近20日", "--", "")
    with m4:
        if pct_60d is not None:
            st.metric("近60日", ("+" if pct_60d >= 0 else "") + str(pct_60d) + "%", "季度走势")
        else:
            st.metric("近60日", "--", "")

    st.markdown("---")

    # AI 阶段性行情分析
    if trend_key not in st.session_state:
        if provider:
            loading_el = st.empty()
            loading_el.markdown(
                '<div class="ai-loading-container">'
                '<div class="ai-loading-icon">' + _AI_LOADING_SVG + '</div>'
                '<div class="ai-loading-bar"></div>'
                '<div class="ai-loading-text">AI 正在撰写行情分析'
                '<span class="dot1">.</span><span class="dot2">.</span><span class="dot3">.</span></div>'
                '</div>',
                unsafe_allow_html=True,
            )
            st.session_state[trend_key] = _generate_trend_report(
                symbol, name, market, price, change, pct_5d, pct_20d, pct_60d,
                normalized, moat, tech, provider,
            )
            loading_el.empty()
        else:
            st.session_state[trend_key] = None

    report = st.session_state.get(trend_key)
    if report:
        st.markdown(report)
    else:
        st.info("配置 API Key 后可生成 AI 阶段性行情分析")

    if st.button("刷新行情分析", key="refresh_trend_{}".format(symbol)):
        st.session_state.pop(trend_key, None)
        st.rerun()


def _generate_trend_report(symbol, name, market, price, change, pct_5d, pct_20d, pct_60d,
                           normalized, moat, tech, provider):
    """调用 AI 生成阶段性行情分析报告"""

    pe = normalized.get("pe_trailing")
    roe = normalized.get("roe")
    gm = normalized.get("gross_margin")
    rg = normalized.get("revenue_growth")
    eg = normalized.get("earnings_growth")
    rsi = tech.get("rsi")
    trend = tech.get("trend", "unknown")
    signals = tech.get("signals", [])

    def _v(val, suffix=""):
        if val is None:
            return "N/A"
        return str(round(val, 2)) + suffix

    market_label = {"us": "美股", "hk": "港股", "a_share": "A股"}.get(market, market)

    prompt = (
        "你是一位融合巴菲特价值投资与段永平本分哲学的资深行情分析师，拥有20年A股、港股、美股实战经验。\n"
        "请为以下股票撰写一份**阶段性行情分析报告**，风格要求：专业、深刻、有洞察力，像给机构投资者写的晨会纪要。\n\n"
        "## 股票信息\n"
        + name + "（" + symbol + "），" + market_label + "，当前价 " + str(price) + "\n\n"
        "## 近期走势\n"
        "- 今日涨跌: " + _v(change, "%") + "\n"
        "- 近5日: " + _v(pct_5d, "%") + "\n"
        "- 近20日: " + _v(pct_20d, "%") + "\n"
        "- 近60日: " + _v(pct_60d, "%") + "\n\n"
        "## 基本面概况\n"
        "- 护城河评分: " + str(moat["percentage"]) + "/100 (" + moat["grade"] + "级)\n"
        "- PE: " + _v(pe) + " | ROE: " + _v(roe, "%") + " | 毛利率: " + _v(gm, "%") + "\n"
        "- 营收增长: " + _v(rg, "%") + " | 利润增长: " + _v(eg, "%") + "\n\n"
        "## 技术面\n"
        "- 趋势: " + trend + " | RSI: " + _v(rsi) + "\n"
        "- 信号: " + ("; ".join(signals) if signals else "无明显信号") + "\n\n"
        "---\n"
        "请用以下结构输出（直接用 Markdown 格式，不要 JSON）：\n\n"
        "### 行情复盘\n"
        "用2-3句话描述近期股价走势的阶段性特征（趋势、波动、量能），引用具体涨跌幅数据。\n\n"
        "### 驱动因素分析\n"
        "分析导致近期涨跌的核心因素（可能包括：行业政策、财报预期、资金面、宏观环境、"
        "竞争格局变化、管理层动作等），每个因素1-2句话，至少分析2-3个因素。"
        "如果数据不足，可基于该公司所处行业的一般性分析。\n\n"
        "### 价值投资视角\n"
        "站在巴菲特的角度，当前价格相对于公司内在价值是便宜了还是贵了？"
        "结合PE、ROE、护城河评分给出判断。"
        "如果股价下跌，判断是\"市场先生的恐慌\"还是\"基本面确实恶化\"。"
        "如果股价上涨，判断是\"合理价值回归\"还是\"市场先生过度乐观\"。\n\n"
        "### 段永平视角\n"
        "用1-2句话，从段永平\"本分\"和\"Stop Doing List\"角度点评：这家公司的生意模式是否经得起考验？"
        "管理层是否在做对的事？\n\n"
        "### 阶段性结论\n"
        "用1句话给出明确的阶段性判断（如：\"短期承压但长期逻辑未变，回调即是布局机会\"），不能模棱两可。\n\n"
        "要求：\n"
        "1. 语气专业但平易近人，像一位值得信赖的投资顾问在跟你聊天\n"
        "2. 每个观点都要有数据支撑，不说空话\n"
        "3. 不要出现\"仅供参考\"\"投资有风险\"等套话\n"
        "4. 总长度控制在300-500字"
    )

    try:
        return _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=1500)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Trend report failed for %s: %s", symbol, e)
        return None


def _render_valuation_hero(symbol, name, market, price, fundamentals, normalized, quote,
                           tech_signal=None, provider=None):
    """估值决策中枢 — 直接在头部下方展示，用户第一眼看到

    渲染策略：量化数据立即出现，AI 文字异步加载不阻塞。
    """
    import streamlit.components.v1 as components

    currency_map = {"us": "$", "hk": "HK$", "a_share": "¥"}
    currency = currency_map.get(market, "$")

    dcf = calc_dcf(price, fundamentals, normalized)

    # 1. 决策横幅 — 立即渲染
    verdict_html = render_valuation_verdict(dcf, symbol, name, currency)
    components.html(verdict_html, height=200, scrolling=False)

    # 2. 价格定位轴 — 立即渲染
    spectrum_html = render_price_spectrum(dcf, quote, currency)
    if spectrum_html:
        components.html(spectrum_html, height=200, scrolling=False)

    # 3. 智能洞察卡片 — 先出量化数据，AI 文字按需加载
    import streamlit.components.v1 as _cmp
    insights_key = "ai_insights_{}".format(symbol)
    ai_insights = st.session_state.get(insights_key)

    # AI 文字未加载时获取
    if ai_insights is None and provider and provider.api_key:
        with st.status("AI 智能洞察生成中...", expanded=False) as _status:
            _status.write("整理财务/技术/估值上下文")
            ai_insights = get_ai_insights(
                symbol, name, price, fundamentals, normalized,
                tech_signal or {}, dcf, provider)
            st.session_state[insights_key] = ai_insights
            _status.update(label="✓ AI 洞察已生成", state="complete", expanded=False)

    insight_html = render_insight_cards(
        price, fundamentals, normalized, tech_signal or {}, dcf, quote,
        currency, ai_insights=ai_insights)
    _cmp.html(insight_html, height=620, scrolling=False)

    # 4. 三情景 + 假设 — 展开看细节
    if dcf and dcf.get("method") != "insufficient":
        with st.expander("Scenario Analysis & Assumptions", expanded=False):
            scenario_html = render_scenario_cards(dcf, currency)
            if scenario_html:
                components.html(scenario_html, height=260, scrolling=False)
            assumptions_html = render_assumptions_panel(dcf)
            if assumptions_html:
                components.html(assumptions_html, height=300, scrolling=False)


def _render_valuation_reference(symbol, normalized, moat):
    """巴菲特 + 段永平估值参考面板 — 替代无用的刷新按钮"""

    pe = normalized.get("pe_trailing")
    pb = normalized.get("pb")
    roe = normalized.get("roe")
    gm = normalized.get("gross_margin")
    pm = normalized.get("profit_margin")
    dte = normalized.get("debt_to_equity")
    cr = normalized.get("current_ratio")
    score = moat["percentage"]

    st.markdown("")

    # 构建对照检查表
    checks = []

    # 1. ROE 检验
    if roe is not None:
        if roe >= 20:
            checks.append(("pass", "ROE {:.1f}% — 远超巴菲特 15% 门槛，盈利能力卓越".format(roe)))
        elif roe >= 15:
            checks.append(("pass", "ROE {:.1f}% — 达到巴菲特 15% 门槛".format(roe)))
        elif roe >= 10:
            checks.append(("warn", "ROE {:.1f}% — 接近但未达巴菲特 15% 标准".format(roe)))
        else:
            checks.append(("fail", "ROE {:.1f}% — 低于巴菲特 15% 底线".format(roe)))
    else:
        checks.append(("na", "ROE 数据缺失"))

    # 2. PE 检验
    if pe is not None and pe > 0:
        if pe <= 15:
            checks.append(("pass", "PE {:.1f} — 市场先生在恐慌抛售，格雷厄姆会点头".format(pe)))
        elif pe <= 25:
            checks.append(("pass", "PE {:.1f} — 估值合理，好公司值得这个价".format(pe)))
        elif pe <= 35:
            checks.append(("warn", "PE {:.1f} — 偏贵，需要确认成长性能否支撑".format(pe)))
        else:
            checks.append(("fail", "PE {:.1f} — 巴菲特不会在这个价位买入".format(pe)))
    else:
        checks.append(("na", "PE 数据缺失或为负（亏损）"))

    # 3. 毛利率 — 定价权
    if gm is not None:
        if gm >= 40:
            checks.append(("pass", "毛利率 {:.1f}% — 拥有定价权，护城河有鳄鱼".format(gm)))
        elif gm >= 25:
            checks.append(("warn", "毛利率 {:.1f}% — 定价权一般".format(gm)))
        else:
            checks.append(("fail", "毛利率 {:.1f}% — 缺乏定价权，生意模式不够好".format(gm)))

    # 4. 负债 — 段永平：不用杠杆
    if dte is not None:
        if dte <= 0.5:
            checks.append(("pass", "负债权益比 {:.2f} — 段永平：不用杠杆是本分".format(dte)))
        elif dte <= 1.0:
            checks.append(("warn", "负债权益比 {:.2f} — 负债可控但需关注".format(dte)))
        else:
            checks.append(("fail", "负债权益比 {:.2f} — 杠杆偏高，段永平会 pass".format(dte)))

    # 5. 一句话说清 + 十年后还在
    if score >= 65:
        checks.append(("pass", "护城河 {:.0f} 分 — 十年后大概率还在，值得长期持有".format(score)))
    elif score >= 50:
        checks.append(("warn", "护城河 {:.0f} 分 — 竞争优势一般，需持续跟踪".format(score)))
    else:
        checks.append(("fail", "护城河 {:.0f} 分 — 巴菲特会等待更好的标的".format(score)))

    # 渲染
    icon_map = {"pass": ":green[PASS]", "fail": ":red[FAIL]", "warn": ":orange[WARN]", "na": "N/A"}

    with st.expander("巴菲特 + 段永平估值检查表", expanded=False):
        st.caption("用大师的标准逐项审视这家公司")

        for status, text in checks:
            st.markdown(icon_map[status] + " &nbsp; " + text)

        st.markdown("---")

        # 大师语录（与当前股票相关的智慧）
        pass_count = sum(1 for s, _ in checks if s == "pass")
        fail_count = sum(1 for s, _ in checks if s == "fail")

        if fail_count == 0 and pass_count >= 3:
            quote = "以合理的价格买入优秀的企业，远胜于以便宜的价格买入平庸的企业。"
            author = "Warren Buffett"
        elif fail_count >= 2:
            quote = "Stop Doing List 比 To Do List 更重要。不懂不做，这四个字价值万亿。"
            author = "段永平"
        elif pe and pe > 30:
            quote = "价格是你付出的，价值是你得到的。市场短期是投票机，长期是称重机。"
            author = "Warren Buffett"
        else:
            quote = "投资最重要的是不要亏大钱。好公司遇到暂时困难时，往往是最好的买入机会。"
            author = "段永平"

        st.markdown("> *\"" + quote + "\"*")
        st.caption("— " + author)


def _render_ai_verdict(symbol, name, market, price, change, moat, normalized, result, provider):
    """在每只股票最后渲染 AI 综合投资建议"""
    verdict_key = "ai_verdict_{}".format(symbol)

    # 自动生成（session 内只生成一次）
    if verdict_key not in st.session_state:
        if provider:
            with st.status("AI 综合投资建议生成中...", expanded=False) as _status:
                _status.write("评估护城河、估值、技术面与风险")
                st.session_state[verdict_key] = _generate_verdict(
                    symbol, name, market, price, change, moat, normalized, result, provider
                )
                _status.update(label="✓ 投资建议已就绪", state="complete", expanded=False)
        else:
            # 无 AI 时用本地规则生成
            st.session_state[verdict_key] = _local_verdict(symbol, name, price, change, moat, normalized, result)

    verdict_data = st.session_state.get(verdict_key, {})
    if not verdict_data:
        return

    action = verdict_data.get("action", "观望")
    confidence = verdict_data.get("confidence", "中")
    reason = verdict_data.get("reason", "")
    details = verdict_data.get("details", "")

    # 颜色映射
    action_colors = {
        "强烈买入": ("#3ECF8E", "rgba(62,207,142,0.08)"),
        "买入": ("#3ECF8E", "rgba(62,207,142,0.06)"),
        "增持": ("#3ECF8E", "rgba(62,207,142,0.04)"),
        "持有": ("#60A5FA", "rgba(96,165,250,0.06)"),
        "减持": ("#F5A623", "rgba(245,166,35,0.06)"),
        "卖出": ("#EF4444", "rgba(239,68,68,0.06)"),
        "强烈卖出": ("#EF4444", "rgba(239,68,68,0.08)"),
        "观望": ("#C9A962", "rgba(201,169,98,0.06)"),
    }
    text_color, bg_color = action_colors.get(action, ("#C9A962", "rgba(201,169,98,0.06)"))

    st.markdown("---")

    # 醒目的建议卡片
    st.markdown(
        '<div style="background:' + bg_color + ';border:1px solid ' + text_color + '44;'
        'border-radius:8px;padding:20px 24px;margin:8px 0;">'
        '<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">'
        '<div style="font-size:1.3rem;font-weight:700;color:' + text_color + ';letter-spacing:2px;'
        'padding:6px 18px;background:' + text_color + '18;border-radius:4px;">' + action + '</div>'
        '<div style="font-size:0.72rem;color:#8A8A96;letter-spacing:1px;">置信度: ' + confidence + '</div>'
        '<div style="flex:1;min-width:200px;font-size:0.92rem;color:#BDBDBD;line-height:1.6;">' + reason + '</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    if details:
        with st.expander("查看 AI 详细分析依据", expanded=True):
            st.markdown(details)

    # 刷新按钮
    if st.button("刷新 AI 建议", key="refresh_verdict_{}".format(symbol)):
        del st.session_state[verdict_key]
        st.rerun()


def _generate_verdict(symbol, name, market, price, change, moat, normalized, result, provider):
    """调用 AI 生成综合投资建议"""
    tech = result.tech_signal

    # 构建数据摘要
    pe = normalized.get("pe_trailing")
    pb = normalized.get("pb")
    roe = normalized.get("roe")
    pm = normalized.get("profit_margin")
    gm = normalized.get("gross_margin")
    dte = normalized.get("debt_to_equity")
    cr = normalized.get("current_ratio")
    rg = normalized.get("revenue_growth")
    eg = normalized.get("earnings_growth")
    rsi = tech.get("rsi")
    trend = tech.get("trend", "unknown")
    roe_hist = normalized.get("roe_history", [])

    def _v(val, suffix=""):
        if val is None:
            return "N/A"
        return str(round(val, 2)) + suffix

    prompt = (
        "你是一位拥有30年经验的巴菲特风格首席投资顾问。"
        "你必须给出**明确、直接、有说服力**的投资建议，不能模棱两可。\n\n"
        "## 股票信息\n"
        "股票: " + symbol + " (" + name + ")\n"
        "当前股价: " + str(price) + " (今日" + ("+" if change >= 0 else "") + str(round(change, 2)) + "%)\n"
        "市场: " + {"us": "美股", "hk": "港股", "a_share": "A股"}.get(market, market) + "\n\n"
        "## 护城河评分\n"
        "总分: " + str(moat["percentage"]) + "/100 (" + moat["grade"] + "级 · " + moat["label"] + ")\n"
    )

    for dim_name, info in moat.get("scores", {}).items():
        prompt += "- " + dim_name + ": " + str(info["score"]) + "/" + str(info["max"]) + "\n"

    prompt += (
        "\n## 关键财务指标\n"
        "PE: " + _v(pe) + " | PB: " + _v(pb) + " | ROE: " + _v(roe, "%") + "\n"
        "净利率: " + _v(pm, "%") + " | 毛利率: " + _v(gm, "%") + "\n"
        "负债权益比: " + _v(dte) + " | 流动比率: " + _v(cr) + "\n"
        "营收增长: " + _v(rg, "%") + " | 利润增长: " + _v(eg, "%") + "\n"
        "ROE历史: " + str(roe_hist) + "\n\n"
        "## 技术面\n"
        "趋势: " + trend + " | RSI: " + _v(rsi) + "\n"
        "技术信号: " + "; ".join(tech.get("signals", [])) + "\n\n"
        "---\n"
        "请严格按以下JSON格式输出，不输出其他内容：\n"
        '{\n'
        '  "action": "强烈买入/买入/增持/持有/减持/卖出/强烈卖出/观望",\n'
        '  "confidence": "高/中/低",\n'
        '  "reason": "一句话核心理由，不超过40字，必须引用具体数据（如PE、ROE等）",\n'
        '  "details": "详细分析，用markdown格式，包含以下内容：\\n'
        '## 核心逻辑\\n[为什么给出这个建议，结合护城河评分和当前股价]\\n\\n'
        '## 基本面判断\\n[ROE/利润率/成长性的具体解读]\\n\\n'
        '## 估值判断\\n[当前PE/PB是贵了还是便宜了，对比历史和行业]\\n\\n'
        '## 技术面配合\\n[趋势和RSI是否支持当前建议]\\n\\n'
        '## 风险提示\\n[最需要警惕的1-2个风险]\\n\\n'
        '## 操作方案\\n[具体建议：建仓/加仓/减仓/清仓，建议仓位比例]"\n'
        '}\n\n'
        "核心要求：\n"
        "1. 建议必须明确，不能说\"可以考虑\"\"建议观察\"这种废话\n"
        "2. reason必须引用至少2个具体数据\n"
        "3. 如果基本面好但估值贵，说\"持有但不追高\"；如果基本面好且估值低，果断说\"买入\"\n"
        "4. 如果基本面差，不管技术面如何，都不建议买入"
    )

    try:
        import json, re
        text = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=1200)
        text = text.strip()
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text).strip()
        return json.loads(text)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("AI verdict failed for %s: %s", symbol, e)
        return _local_verdict(symbol, name, price, change, moat, normalized, result)


def _local_verdict(symbol, name, price, change, moat, normalized, result):
    """无 AI 时基于规则生成本地建议"""
    score = moat["percentage"]
    grade = moat["grade"]
    pe = normalized.get("pe_trailing")
    roe = normalized.get("roe")
    trend = result.tech_signal.get("trend", "unknown")
    rsi = result.tech_signal.get("rsi")

    # 规则引擎
    if score >= 75 and pe and pe < 20 and trend in ("bullish", "neutral"):
        action, confidence = "买入", "高"
        reason = "护城河评分{:.0f}分({}级)，PE仅{:.1f}倍，基本面优秀且估值合理".format(score, grade, pe)
    elif score >= 65 and pe and pe < 25:
        action, confidence = "增持", "中"
        reason = "护城河{:.0f}分，PE {:.1f}倍处于合理区间，值得逐步建仓".format(score, pe)
    elif score >= 65 and pe and pe >= 25:
        action, confidence = "持有", "中"
        reason = "护城河{:.0f}分({})，但PE {:.1f}偏高，持有不追高".format(score, grade, pe)
    elif score >= 50:
        action, confidence = "观望", "中"
        reason = "护城河{:.0f}分，品质尚可但不够突出，等待更好价格".format(score)
    elif score >= 35:
        action, confidence = "减持", "中"
        reason = "护城河仅{:.0f}分({}级)，竞争优势不明显".format(score, grade)
    else:
        action, confidence = "卖出", "高"
        reason = "护城河{:.0f}分({}级)，不符合价值投资标准".format(score, grade)

    # RSI 修正
    if rsi and rsi < 30 and action in ("买入", "增持"):
        reason += "，且RSI={:.0f}超卖，短期反弹概率大".format(rsi)
        confidence = "高"
    elif rsi and rsi > 70 and action in ("买入", "增持"):
        action = "持有"
        reason += "，但RSI={:.0f}超买，建议等回调再加仓".format(rsi)

    details = (
        "## 核心逻辑\n"
        "护城河综合评分 **{:.0f}/100** ({}级 · {})".format(score, grade, moat["label"])
        + ("，当前PE **{:.1f}**".format(pe) if pe else "")
        + ("，ROE **{:.1f}%**".format(roe) if roe else "")
        + "\n\n*（此为本地规则引擎生成，配置 API Key 后可获得 AI 深度分析）*"
    )

    return {"action": action, "confidence": confidence, "reason": reason, "details": details}


# ========================================
# MAIN
# ========================================
from src.config import load_config
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
                        sub += " · Rev Est. {}".format(_format_revenue(calendar["revenue_estimate"]))
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

            # Track usage
            increment_usage(_a_uid)

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
                        "ROE": _fmt_pct(_normalize_fundamentals(r.fundamentals).get("roe")),
                        "Trend": _trend_label(r.tech_signal.get("trend")),
                        "Verdict": moat["label"],
                    }
                except Exception as e:
                    return {"ok": False, "Symbol": stock.symbol, "Name": stock.name,
                            "Price": "-", "Grade": "-", "Score": 0,
                            "ROE": "-", "Trend": "-", "Verdict": str(e)[:30]}

            with ThreadPoolExecutor(max_workers=4) as exe:
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

            with ThreadPoolExecutor(max_workers=6) as exe:
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
                "ROE": _fmt_pct(norm.get("roe")),
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
