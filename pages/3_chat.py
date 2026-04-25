"""AI Advisory — Buffett + Duan Yongping AI Partner"""

import streamlit as st
import streamlit.components.v1 as components
import random

from src.config import get_premium_provider, load_config
from src.ai.summarizer import chat_with_analyst_stream
from src.ai.knowledge_base import (
    BUFFETT_PHILOSOPHY, BUFFETT_CASES, BUFFETT_QUOTES,
    DUAN_YONGPING_PHILOSOPHY, DUAN_YONGPING_CASES, DUAN_YONGPING_QUOTES,
    EVALUATION_FRAMEWORK, MOAT_TYPES,
)
from src.ui_theme import get_global_css, COLORS

if "config" not in st.session_state:
    st.session_state.config = load_config()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
config = st.session_state.config

st.markdown(get_global_css(), unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
components.html("""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:24px 0 8px;text-align:center}
.icon{font-size:2.2rem;margin-bottom:12px;opacity:0.8}
.title{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.6rem;font-weight:300;color:#E8E8F0;letter-spacing:4px;text-transform:uppercase}
.title b{font-weight:700;color:#C9A962}
.sub{font-size:0.55rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-top:6px}
.divider{height:1px;background:linear-gradient(90deg,transparent,#C9A962 30%,transparent);margin-top:16px;opacity:0.3}
</style></head><body>
<div class="icon">&#x1F9D0;</div>
<div class="title">AI <b>Advisor</b></div>
<div class="sub">Buffett &middot; Duan Yongping &middot; Value Investing Partner</div>
<div class="divider"></div>
</body></html>
""", height=130, scrolling=False)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    provider = get_premium_provider(config)
    if provider and provider.api_key:
        st.markdown(
            '<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:10px 14px;margin-bottom:8px">'
            '<div style="font-size:0.5rem;letter-spacing:3px;color:#00C853;text-transform:uppercase;margin-bottom:4px">ONLINE</div>'
            '<div style="font-size:0.75rem;color:#E8E8F0">{}</div>'
            '<div style="font-size:0.6rem;color:#5A5A6A;margin-top:2px">{}</div>'
            '</div>'.format(provider.name, provider.model),
            unsafe_allow_html=True)
    else:
        st.warning("API not configured. Go to Settings.")

    st.divider()

    # Stock context
    ctx = st.session_state.get("chat_context_stock")
    if ctx:
        grade = ctx.get("grade", "?")
        gc = {"S": "#00C853", "A": "#69F0AE", "B": "#C9A962", "C": "#FF9800"}.get(grade, "#5A5A6A")
        st.markdown(
            '<div style="background:#0D0D14;border:1px solid #1E1E2A;border-left:3px solid {};border-radius:4px;padding:10px 14px;margin-bottom:8px">'
            '<div style="font-size:0.5rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:4px">Discussing</div>'
            '<div style="font-size:1rem;font-weight:600;color:#C9A962">{}</div>'
            '<div style="font-size:0.7rem;color:#8888A0;margin-top:2px">{} &middot; Grade {}</div>'
            '</div>'.format(gc, ctx["symbol"], ctx["name"], grade),
            unsafe_allow_html=True)
        if st.button("Clear context", use_container_width=True):
            st.session_state.pop("chat_context_stock", None)
            st.rerun()
        st.divider()

    # Quick topics
    st.markdown('<div style="font-size:0.55rem;letter-spacing:3px;color:#C9A962;text-transform:uppercase;margin-bottom:8px">ASK ME</div>',
                unsafe_allow_html=True)
    topics = [
        ("这只股票值得买吗？帮我做完整评估", "full_eval"),
        ("当前市场是恐惧还是贪婪？仓位怎么定？", "market_mood"),
        ("帮我对比两家公司的护城河深度", "moat_compare"),
        ("我关注列表里哪些最符合巴菲特标准？", "watchlist_check"),
        ("这家公司的管理层值得信任吗？", "management"),
        ("段永平会怎么看这只股票？", "duan_view"),
        ("帮我制定一个价值投资的买入计划", "buy_plan"),
        ("请教：什么是真正的安全边际？", "education"),
    ]
    for text, key in topics:
        if st.button(text, key="q_{}".format(key), use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": text})
            st.rerun()

    st.divider()
    if st.button("Clear conversation", use_container_width=True, key="clear_chat"):
        st.session_state.chat_history = []
        st.session_state.pop("chat_context_stock", None)
        st.rerun()


# ── Build context ─────────────────────────────────────────────────────────────
def build_context() -> str:
    parts = []

    # Core knowledge (truncated for context window management)
    parts.append(BUFFETT_PHILOSOPHY)
    parts.append(DUAN_YONGPING_PHILOSOPHY)
    parts.append(BUFFETT_CASES[:2000])
    parts.append(DUAN_YONGPING_CASES[:1500])
    parts.append(EVALUATION_FRAMEWORK)

    # Stock-specific context
    ctx = st.session_state.get("chat_context_stock")
    if ctx:
        parts.append("\n## 当前讨论的股票")
        parts.append("{} ({})，护城河评级: {} ({}分/100)".format(
            ctx["symbol"], ctx["name"], ctx.get("grade", "?"), ctx.get("score", "?")))
        if ctx.get("analysis"):
            parts.append("之前的分析报告:\n{}".format(ctx["analysis"][:2000]))

    # Watchlist context
    watchlist = config.watchlist
    stocks_summary = []
    for market, label in [("us", "US"), ("hk", "HK"), ("a_share", "A-Share")]:
        names = ["{} ({})".format(s.name, s.symbol) for s in getattr(watchlist, market, [])]
        if names:
            stocks_summary.append("{}: {}".format(label, ", ".join(names)))
    if stocks_summary:
        parts.append("\n## 用户关注列表\n" + "\n".join(stocks_summary))

    return "\n\n".join(parts)


# ── Chat area ─────────────────────────────────────────────────────────────────
if not st.session_state.chat_history:
    ctx = st.session_state.get("chat_context_stock")

    welcome = """你好，我是你的**价值投资AI合伙人**。

我深入研究了巴菲特60年的投资记录和段永平的所有公开言论，
将他们的投资智慧融合为一套可执行的分析框架。

**我可以帮你：**
- **完整评估一只股票** — 从护城河到安全边际，像巴菲特一样逐步分析
- **判断买入时机** — 市场先生现在是恐惧还是贪婪？
- **管理层评估** — 像段永平一样看人、看文化
- **制定投资计划** — 明确的买入区间、仓位、止损

我会给你**明确的方向性判断**，不说"仅供参考"。"""

    if ctx:
        welcome += "\n\n我看到你正在分析 **{}** ({})，评级 **{}**。要我做完整评估吗？".format(
            ctx["symbol"], ctx["name"], ctx.get("grade", "?"))

    with st.chat_message("assistant", avatar="🧐"):
        st.markdown(welcome)
        quote = random.choice(BUFFETT_QUOTES + DUAN_YONGPING_QUOTES)
        st.markdown('> *"{}"*'.format(quote))

# Render history
for msg in st.session_state.chat_history:
    avatar = "👤" if msg["role"] == "user" else "🧐"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Handle unanswered quick topic
if (st.session_state.chat_history
    and st.session_state.chat_history[-1]["role"] == "user"
    and (len(st.session_state.chat_history) < 2
         or st.session_state.chat_history[-2]["role"] != "assistant"
         or len(st.session_state.chat_history) == 1)):

    provider = get_premium_provider(config)
    with st.chat_message("assistant", avatar="🧐"):
        context = build_context()
        # st.write_stream renders the generator progressively and returns the
        # full concatenated string for history persistence.
        reply = st.write_stream(
            chat_with_analyst_stream(
                st.session_state.chat_history,
                provider=provider,
                context=context,
            )
        )
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

# Input
user_input = st.chat_input("Ask me anything about investing...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    provider = get_premium_provider(config)
    with st.chat_message("assistant", avatar="🧐"):
        context = build_context()
        reply = st.write_stream(
            chat_with_analyst_stream(
                st.session_state.chat_history,
                provider=provider,
                context=context,
            )
        )
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
