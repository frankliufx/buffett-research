"""AI Advisory — Buffett AI Persona"""

import streamlit as st
from src.config import get_active_provider
from src.ai.summarizer import chat_with_analyst
from src.ai.knowledge_base import BUFFETT_PHILOSOPHY, BUFFETT_QUOTES, MOAT_TYPES
from src.ui_theme import (get_global_css, BUFFETT_AVATAR_SVG, COLORS,
                          render_sidebar_status)
import random

from src.config import load_config
if "config" not in st.session_state:
    st.session_state.config = load_config()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
config = st.session_state.config

st.markdown(get_global_css(), unsafe_allow_html=True)

# Header
st.markdown("""
<div style="text-align:center; padding:2rem 0 1.5rem;">
    <div style="display:inline-block; margin-bottom:0.8rem;">
        {avatar}
    </div>
    <h2 style="color:{text}; margin:0.5rem 0 0.3rem; font-weight:300; letter-spacing:3px;">BUFFETT AI ADVISOR</h2>
    <p style="color:{muted}; font-size:0.82rem; letter-spacing:2px;">VALUE INVESTING · MOAT EXPERT</p>
</div>
""".format(avatar=BUFFETT_AVATAR_SVG, text=COLORS["text"], muted=COLORS["text_muted"]),
    unsafe_allow_html=True)

# Init
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ===== Sidebar =====
with st.sidebar:
    provider = get_active_provider(config)
    if provider:
        st.markdown(render_sidebar_status(provider.name, provider.model, True), unsafe_allow_html=True)
    else:
        st.markdown(render_sidebar_status("Not Configured", "--", False), unsafe_allow_html=True)

    st.divider()

    # Stock context
    ctx = st.session_state.get("chat_context_stock")
    if ctx:
        st.markdown("""
        <div class="metric-card" style="padding:0.8rem;">
            <div style="font-size:0.7rem; color:{muted}; letter-spacing:1px; margin-bottom:4px;">DISCUSSING</div>
            <div style="font-size:1.05rem; font-weight:600; color:{text};">{sym}</div>
            <div style="color:{muted}; font-size:0.82rem;">{name} · Grade {grade}</div>
        </div>
        """.format(sym=ctx["symbol"], name=ctx["name"],
                   grade=ctx.get("grade", "?"),
                   text=COLORS["text"], muted=COLORS["text_muted"]),
            unsafe_allow_html=True)
        if st.button("Clear context"):
            st.session_state.pop("chat_context_stock", None)
            st.rerun()

    st.divider()

    # Quick topics
    st.markdown('<div style="color:{}; font-size:0.72rem; letter-spacing:1px; margin-bottom:0.5rem;">QUICK TOPICS</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)
    topics = [
        "什么是护城河？如何判断一家公司的护城河深度？",
        "帮我分析关注列表中，哪些股票最符合巴菲特标准？",
        "目前市场环境下，应该采取什么仓位策略？",
        "帮我对比腾讯和阿里，谁的护城河更深？",
        "A股、港股、美股，哪个市场更有价值投资机会？",
        "请教我巴菲特的安全边际理论",
        "市场先生今天是什么情绪？我该怎么应对？",
    ]
    for q in topics:
        if st.button(q[:22] + "...", key="q_{}".format(hash(q)),
                     use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": q})
            st.rerun()

    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.pop("chat_context_stock", None)
        st.rerun()

    # Knowledge base
    st.divider()
    with st.expander("Investment Knowledge"):
        st.markdown("""
**Core Theories**
- Mr. Market
- Moat Theory (5 types)
- Margin of Safety
- Circle of Competence
- Long-term Investing
- Concentrated Portfolio
""")
        for key, info in MOAT_TYPES.items():
            st.markdown("{} **{}**\n{}".format(info["icon"], info["name"], info["description"]))


# ===== Build context =====
def build_context() -> str:
    parts = []
    parts.append(BUFFETT_PHILOSOPHY[:3000])

    ctx = st.session_state.get("chat_context_stock")
    if ctx:
        parts.append("\n## 当前讨论的股票")
        parts.append("{} ({})，护城河评级: {} ({})".format(
            ctx["symbol"], ctx["name"], ctx.get("grade", "?"), ctx.get("label", "")))
        parts.append("护城河得分: {}/100".format(ctx.get("score", "?")))
        if ctx.get("analysis"):
            parts.append("之前的分析报告:\n{}".format(ctx["analysis"][:2000]))

    watchlist = config.watchlist
    stocks_summary = []
    for market, label in [("us", "US"), ("hk", "HK"), ("a_share", "A-Share")]:
        names = ["{} ({})".format(s.name, s.symbol) for s in getattr(watchlist, market, [])]
        if names:
            stocks_summary.append("{}: {}".format(label, ", ".join(names)))
    if stocks_summary:
        parts.append("\n## Watchlist\n" + "\n".join(stocks_summary))

    return "\n\n".join(parts)


# ===== Chat area =====
if not st.session_state.chat_history:
    with st.chat_message("assistant", avatar="📊"):
        ctx = st.session_state.get("chat_context_stock")

        welcome = """你好，我是你的**巴菲特 AI 投顾**。

我深谙价值投资哲学，专注于为你找到拥有**深深护城河**的优质企业。

我可以帮你：
- **护城河分析** — 评估企业的持久竞争优势
- **个股研判** — ROE、估值、安全边际全方位分析
- **市场先生解读** — 判断当前是恐惧还是贪婪
- **投资教育** — 巴菲特价值投资方法论"""

        if ctx:
            welcome += "\n\n我看到你正在关注 **{}** ({})，护城河评级 **{}**。想深入聊聊？".format(
                ctx["symbol"], ctx["name"], ctx.get("grade", "?"))

        st.markdown(welcome)

        quote = random.choice(BUFFETT_QUOTES)
        st.markdown("""
<div class="buffett-quote">
    "{}"
    <span class="author">-- Warren Buffett</span>
</div>
""".format(quote), unsafe_allow_html=True)

# Render history
for msg in st.session_state.chat_history:
    avatar = "👤" if msg["role"] == "user" else "📊"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Handle unanswered messages from quick topic buttons
if (st.session_state.chat_history
    and st.session_state.chat_history[-1]["role"] == "user"
    and (len(st.session_state.chat_history) < 2
         or st.session_state.chat_history[-2]["role"] != "assistant"
         or len(st.session_state.chat_history) == 1)):

    provider = get_active_provider(config)
    with st.chat_message("assistant", avatar="📊"):
        with st.spinner("Thinking..."):
            context = build_context()
            reply = chat_with_analyst(
                st.session_state.chat_history,
                provider=provider,
                context=context,
            )
        st.markdown(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

# Input
user_input = st.chat_input("Ask anything about investing...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    provider = get_active_provider(config)
    with st.chat_message("assistant", avatar="📊"):
        with st.spinner("Thinking..."):
            context = build_context()
            reply = chat_with_analyst(
                st.session_state.chat_history,
                provider=provider,
                context=context,
            )
        st.markdown(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
