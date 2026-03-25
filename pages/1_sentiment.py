"""市场情绪中心 — 恐惧贪婪指数 · 资金流向 · 投资者观点"""

import streamlit as st
from src.ui_theme import get_global_css, COLORS
from src.data.sentiment import get_market_sentiment
from src.data.news import fetch_market_news
from src.config import load_config, get_active_provider
from src.ai.summarizer import _call_llm

if "config" not in st.session_state:
    st.session_state.config = load_config()
config = st.session_state.config

st.markdown(get_global_css(), unsafe_allow_html=True)

# ── 载入动画样式 ──
_SENTIMENT_LOADING_CSS = """
<style>
@keyframes heartbeat {
    0%, 100% { transform: scale(1); }
    15% { transform: scale(1.15); }
    30% { transform: scale(1); }
    45% { transform: scale(1.1); }
}
@keyframes wave-bar {
    0%, 100% { height: 8px; }
    50% { height: 24px; }
}
@keyframes fade-text {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 1; }
}
.sentiment-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 0;
    gap: 24px;
}
.sentiment-loading-icon {
    animation: heartbeat 1.5s ease-in-out infinite;
}
.sentiment-wave {
    display: flex;
    align-items: flex-end;
    gap: 4px;
    height: 28px;
}
.sentiment-wave-bar {
    width: 4px;
    border-radius: 2px;
    animation: wave-bar 1.2s ease-in-out infinite;
}
.sentiment-loading-text {
    font-size: 0.88rem;
    color: #8A8A96;
    letter-spacing: 1px;
    animation: fade-text 2s ease-in-out infinite;
}
</style>
"""
st.markdown(_SENTIMENT_LOADING_CSS, unsafe_allow_html=True)

# 心电图风格 SVG — 代表市场脉搏
_PULSE_SVG = """
<svg width="80" height="56" viewBox="0 0 80 56" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M0 28 L16 28 L22 12 L28 44 L34 8 L40 48 L46 20 L52 28 L80 28"
        stroke="#C9A962" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none">
    <animate attributeName="stroke-dasharray" values="0 200;200 0" dur="2s" repeatCount="indefinite"/>
  </path>
  <circle cx="40" cy="28" r="4" fill="#C9A962" opacity="0.6">
    <animate attributeName="r" values="3;6;3" dur="1.5s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.6;1;0.6" dur="1.5s" repeatCount="indefinite"/>
  </circle>
</svg>
"""

def _show_sentiment_loading():
    """市场脉搏风格载入动画"""
    # 波形条 — 模拟市场活跃度
    bars = ""
    colors = ["#EF4444", "#F5A623", "#C9A962", "#60A5FA", "#3ECF8E"]
    delays = [0, 0.15, 0.3, 0.45, 0.6, 0.45, 0.3, 0.15, 0]
    for i, delay in enumerate(delays):
        c = colors[i % len(colors)]
        bars += (
            '<div class="sentiment-wave-bar" style="background:' + c
            + ';animation-delay:' + str(delay) + 's;"></div>'
        )

    return st.markdown(
        '<div class="sentiment-loading">'
        '<div class="sentiment-loading-icon">' + _PULSE_SVG + '</div>'
        '<div class="sentiment-wave">' + bars + '</div>'
        '<div class="sentiment-loading-text">正在感知市场脉搏</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── 缓存 ──
@st.cache_data(ttl=300, show_spinner=False)
def cached_sentiment():
    return get_market_sentiment()

@st.cache_data(ttl=600, show_spinner=False)
def cached_news(market, limit=10):
    return fetch_market_news(market, limit)

# ── 载入数据（带动画）──
_loading_el = st.empty()
with _loading_el.container():
    _show_sentiment_loading()

data = cached_sentiment()
_loading_el.empty()

# ═══════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════
score = data["fear_greed_score"]
mood = data["mood"]
mc = data["mood_color"]

st.markdown("### Market Sentiment")
st.caption("巴菲特说：别人恐惧时贪婪，别人贪婪时恐惧")

# ═══════════════════════════════════════════════════════════════════
# ROW 1: 恐惧贪婪指数 + 三大指数
# ═══════════════════════════════════════════════════════════════════
col_fg, col_idx = st.columns([1, 2])

with col_fg:
    st.metric(
        label="Fear & Greed Index",
        value=str(score) + " / 100",
        delta=mood,
        delta_color="normal" if score >= 50 else "inverse",
    )

    # 成交额 & 北向
    amt = data["total_amount_yi"]
    north = data["northbound_yi"]
    vol_label = "火热" if amt > 15000 else "活跃" if amt > 10000 else "正常" if amt > 8000 else "低迷"

    c1, c2 = st.columns(2)
    with c1:
        st.metric("两市成交", str(round(amt)) + " 亿", vol_label)
    with c2:
        if north != 0:
            north_delta = ("+" if north > 0 else "") + str(north) + " 亿"
            st.metric("北向资金", north_delta, "沪港通+深港通")
        else:
            st.metric("北向资金", "暂无数据", "非交易时段")

with col_idx:
    idx_cols = st.columns(3)
    for i, idx in enumerate(data.get("indices", [])):
        with idx_cols[i]:
            change = idx["change_pct"]
            sign = "+" if change >= 0 else ""
            st.metric(
                label=idx["name"],
                value=str(idx["price"]),
                delta=sign + str(change) + "%",
            )
            amt_yi = round(idx.get("amount", 0) / 1e8)
            st.caption("成交 " + str(amt_yi) + " 亿")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════
# ROW 2: 板块资金流向 + 个股主力资金
# ═══════════════════════════════════════════════════════════════════
col_sector, col_stock = st.columns(2)

with col_sector:
    st.markdown("**板块资金流向 TOP**")
    st.caption("主力净流入排名 — 反映热点板块方向")
    sector_data = data.get("sector_flow", [])
    if sector_data:
        for s in sector_data[:8]:
            chg = s["change_pct"]
            flow = s["net_flow"]
            chg_color = "green" if chg >= 0 else "red"
            flow_color = "green" if flow >= 0 else "red"
            st.markdown(
                "**" + s["name"] + "** &nbsp; "
                + ":" + chg_color + "[" + ("+" if chg >= 0 else "") + str(chg) + "%] &nbsp; "
                + "主力 :" + flow_color + "[" + ("+" if flow >= 0 else "") + str(flow) + "亿]"
            )
    else:
        st.info("暂无板块数据（非交易时段）")

with col_stock:
    st.markdown("**个股主力资金 TOP**")
    st.caption("聪明钱在买什么 — 主力净流入排名")
    flow_in = data.get("stock_flow_in", [])
    if flow_in:
        for s in flow_in[:8]:
            chg = s["change_pct"]
            flow = s["net_flow"]
            chg_color = "green" if chg >= 0 else "red"
            st.markdown(
                "**" + s["name"] + "** (" + s["code"] + ") &nbsp; "
                + ":" + chg_color + "[" + ("+" if chg >= 0 else "") + str(chg) + "%] &nbsp; "
                + ":green[+" + str(flow) + "亿]"
            )
    else:
        st.info("暂无数据（非交易时段）")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════
# ROW 3: 资金流出 + 散户人气
# ═══════════════════════════════════════════════════════════════════
col_out, col_pop = st.columns(2)

with col_out:
    st.markdown("**主力资金出逃 TOP**")
    st.caption("主力在卖什么 — 风险预警参考")
    flow_out = data.get("stock_flow_out", [])
    if flow_out:
        for s in flow_out[:8]:
            chg = s["change_pct"]
            flow = s["net_flow"]
            chg_color = "green" if chg >= 0 else "red"
            st.markdown(
                "**" + s["name"] + "** (" + s["code"] + ") &nbsp; "
                + ":" + chg_color + "[" + ("+" if chg >= 0 else "") + str(chg) + "%] &nbsp; "
                + ":red[" + str(flow) + "亿]"
            )
    else:
        st.info("暂无数据（非交易时段）")

with col_pop:
    st.markdown("**散户人气榜 TOP**")
    st.caption("散户最关注 — 偶尔可作反向指标")
    pop = data.get("popularity", [])
    if pop:
        # 人气榜有代码，尝试从资金流数据中查找名称
        all_stocks = {s["code"]: s["name"] for s in flow_in + flow_out}
        for p in pop[:10]:
            code = p["code"]
            # 转换格式 SZ002594 -> 002594
            short_code = code[2:] if len(code) > 2 else code
            name = all_stocks.get(short_code, "")
            rank_str = str(p["rank"])
            if name:
                st.markdown("**#" + rank_str + "** &nbsp; " + name + " (" + short_code + ")")
            else:
                st.markdown("**#" + rank_str + "** &nbsp; " + code)
    else:
        st.info("暂无数据")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════
# ROW 4: 市场资讯（各路观点）
# ═══════════════════════════════════════════════════════════════════
st.markdown("**市场资讯与观点**")
st.caption("新浪财经实时新闻 — 感知市场温度、汇聚各路讨论")

tab_a, tab_us, tab_hk = st.tabs(["A 股", "美股", "港股"])

for tab, market in [(tab_a, "a_share"), (tab_us, "us"), (tab_hk, "hk")]:
    with tab:
        news = cached_news(market, 10)
        if news:
            for n in news:
                title = n.get("title", "")
                source = n.get("source", "")
                time_str = n.get("time", "")
                url = n.get("url", "")
                meta = source + (" · " + time_str if time_str else "")
                if url:
                    st.markdown("- [" + title + "](" + url + ")")
                else:
                    st.markdown("- " + title)
                st.caption("&nbsp;&nbsp;&nbsp;&nbsp;" + meta)
        else:
            st.info("暂无新闻")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════
# ROW 5: AI 情绪研判
# ═══════════════════════════════════════════════════════════════════
st.markdown("**AI 情绪研判**")
st.caption("AI 结合以上数据，给出巴菲特视角的市场情绪解读")

ai_key = "ai_sentiment_analysis"

if st.button("生成 AI 情绪研判", type="primary"):
    provider = get_active_provider(config)
    if not provider:
        st.warning("请先在 Settings 页面配置 API Key")
    else:
        idx_summary = ""
        for idx in data.get("indices", []):
            idx_summary += "- " + idx["name"] + ": " + str(idx["price"]) + " (" + str(idx["change_pct"]) + "%)\n"

        sector_summary = ""
        for s in data.get("sector_flow", [])[:5]:
            sector_summary += "- " + s["name"] + ": " + str(s["change_pct"]) + "%, 主力净流入 " + str(s["net_flow"]) + "亿\n"

        stock_in_summary = ""
        for s in data.get("stock_flow_in", [])[:5]:
            stock_in_summary += "- " + s["name"] + " (" + s["code"] + "): " + str(s["change_pct"]) + "%, 主力净流入 " + str(s["net_flow"]) + "亿\n"

        prompt = (
            "你是一位深谙巴菲特价值投资哲学的市场情绪分析师。基于以下实时市场数据，给出今日情绪研判。\n\n"
            "## 实时数据\n"
            "恐惧贪婪指数: " + str(score) + "/100 (" + mood + ")\n"
            "两市成交额: " + str(round(amt)) + " 亿\n"
            "北向资金: " + str(north) + " 亿\n\n"
            "## 大盘指数\n" + idx_summary + "\n"
            "## 板块资金流向 Top 5\n" + sector_summary + "\n"
            "## 个股主力净流入 Top 5\n" + stock_in_summary + "\n"
            "---\n"
            "请输出：\n\n"
            "## 今日市场情绪\n[1-2 句话概括今天市场整体情绪，引用具体数据]\n\n"
            "## 巴菲特会怎么看\n[用巴菲特的视角解读当前情绪，2-3 句话]\n\n"
            "## 资金信号解读\n[板块轮动方向、主力资金动向，1-2 句话]\n\n"
            "## 操作建议\n[明确的仓位建议和方向，1-2 句话]\n\n"
            "## 反向指标提醒\n[如果散户人气榜异常集中或情绪极端，给出反向思考]\n\n"
            "用中文，语气专业但平易近人。建议明确，不说废话。"
        )

        with st.spinner("AI 正在分析市场情绪..."):
            try:
                result = _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=1500)
                st.session_state[ai_key] = result
            except Exception as e:
                st.error("AI 分析失败: " + str(e))

if ai_key in st.session_state:
    st.markdown(st.session_state[ai_key])

# 刷新按钮
st.markdown("---")
col_refresh, col_disclaimer = st.columns([1, 3])
with col_refresh:
    if st.button("刷新数据"):
        cached_sentiment.clear()
        cached_news.clear()
        st.session_state.pop(ai_key, None)
        st.rerun()
with col_disclaimer:
    st.caption("数据来源：东方财富、新浪财经。市场情绪仅供参考，不构成投资建议。")
