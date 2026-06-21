"""AI Advisory — Buffett + Duan Yongping AI Partner"""

import re
import streamlit as st
import streamlit.components.v1 as components
import random
from datetime import date

from src.config import get_premium_provider, load_config
from src.ai.summarizer import stream_chat_with_analyst
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


# ── 股票代码识别 ──────────────────────────────────────────────────────────────
# 常见公司名 → 代码映射（补充识别中文名）
_NAME_TO_TICKER = {
    "英伟达": ("NVDA", "us"), "nvidia": ("NVDA", "us"),
    "苹果": ("AAPL", "us"), "apple": ("AAPL", "us"),
    "微软": ("MSFT", "us"), "microsoft": ("MSFT", "us"),
    "谷歌": ("GOOGL", "us"), "google": ("GOOGL", "us"), "alphabet": ("GOOGL", "us"),
    "亚马逊": ("AMZN", "us"), "amazon": ("AMZN", "us"),
    "特斯拉": ("TSLA", "us"), "tesla": ("TSLA", "us"),
    "meta": ("META", "us"), "facebook": ("META", "us"),
    "伯克希尔": ("BRK-B", "us"), "berkshire": ("BRK-B", "us"),
    "腾讯": ("00700.HK", "hk"), "tencent": ("00700.HK", "hk"),
    "阿里巴巴": ("BABA", "us"), "alibaba": ("BABA", "us"),
    "比亚迪": ("002594", "a_share"), "byd": ("002594", "a_share"),
    "茅台": ("600519", "a_share"), "贵州茅台": ("600519", "a_share"),
    "招商银行": ("600036", "a_share"),
    "宁德时代": ("300750", "a_share"), "catl": ("300750", "a_share"),
}

def _detect_stocks(text: str) -> list[tuple[str, str]]:
    """从文本中识别股票代码和市场，返回 [(symbol, market), ...]"""
    found = []
    low = text.lower()
    # 中英文公司名匹配
    for name, (sym, mkt) in _NAME_TO_TICKER.items():
        if name in low or name in text:
            if (sym, mkt) not in found:
                found.append((sym, mkt))
    # 美股代码：1-5大写字母（独立单词）
    for m in re.finditer(r'\b([A-Z]{1,5}(?:-[A-Z])?)\b', text):
        sym = m.group(1)
        if sym not in ("AI", "PE", "PB", "ROE", "ETF", "IPO", "DCF", "GDP", "API", "USD", "HK"):
            if ("us", sym) not in [(s, mk) for s, mk in found]:
                found.append((sym, "us"))
    # A股6位数字
    for m in re.finditer(r'\b([036]\d{5})\b', text):
        found.append((m.group(1), "a_share"))
    # 港股 xxxxx.HK
    for m in re.finditer(r'\b(\d{4,5}\.HK)\b', text, re.IGNORECASE):
        found.append((m.group(1).upper(), "hk"))
    return found[:3]  # 最多取前3只


def _fetch_live_data(symbol: str, market: str) -> str:
    """拉取实时行情+基本面，返回格式化文本，失败时返回空字符串"""
    try:
        from src.data.price import fetch_quote
        from src.data.financial import fetch_fundamentals
        q = fetch_quote(symbol, market)
        f = fetch_fundamentals(symbol, market)
        price = q.get("price") or q.get("close")
        change = q.get("change_pct", 0)
        lines = [
            "## {} 实时数据（{}）".format(symbol, date.today().isoformat()),
            "当前价格: {} | 今日涨跌: {:.2f}%".format(price, float(change or 0)),
        ]
        for key, label in [
            ("pe_ratio", "市盈率PE"), ("pb_ratio", "市净率PB"),
            ("roe", "ROE"), ("profit_margin", "净利率"),
            ("gross_margin", "毛利率"), ("market_cap", "市值(亿)"),
            ("revenue_growth", "营收增长"), ("earnings_growth", "利润增长"),
            ("debt_to_equity", "负债权益比"), ("free_cashflow", "自由现金流"),
        ]:
            val = f.get(key)
            if val is not None and str(val) not in ("None", "N/A", "nan"):
                lines.append("{}: {}".format(label, val))
        return "\n".join(lines)
    except Exception:
        return ""


# ── Build context ─────────────────────────────────────────────────────────────
def build_context(last_user_msg: str = "") -> str:
    parts = []

    # Core knowledge (truncated for context window management)
    parts.append(BUFFETT_PHILOSOPHY)
    parts.append(DUAN_YONGPING_PHILOSOPHY)
    parts.append(BUFFETT_CASES[:2000])
    parts.append(DUAN_YONGPING_CASES[:1500])
    parts.append(EVALUATION_FRAMEWORK)

    # ── 实时行情注入 ──────────────────────────────────────────────────────────
    # 优先从 chat_context_stock（深度分析页跳转过来的股票）取，否则识别最新消息
    ctx = st.session_state.get("chat_context_stock")
    if ctx:
        parts.append("\n## 当前讨论的股票（已完成深度分析）")
        parts.append("{} ({})，护城河评级: {} ({}分/100)".format(
            ctx["symbol"], ctx["name"], ctx.get("grade", "?"), ctx.get("score", "?")))
        if ctx.get("analysis"):
            parts.append("之前的分析报告:\n{}".format(ctx["analysis"][:2000]))
        # 补充实时价格
        live = _fetch_live_data(ctx["symbol"], ctx.get("market", "us"))
        if live:
            parts.append(live)
    elif last_user_msg:
        stocks = _detect_stocks(last_user_msg)
        live_blocks = []
        for sym, mkt in stocks:
            block = _fetch_live_data(sym, mkt)
            if block:
                live_blocks.append(block)
        if live_blocks:
            parts.append("\n## 实时市场数据（今日最新，请基于此数据分析，不要使用过时数据）")
            parts.extend(live_blocks)

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
        last_msg = next((m["content"] for m in reversed(st.session_state.chat_history) if m["role"] == "user"), "")
        context = build_context(last_msg)
        reply = st.write_stream(stream_chat_with_analyst(
            st.session_state.chat_history,
            provider=provider,
            context=context,
        ))
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

# Input
user_input = st.chat_input("Ask me anything about investing...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    provider = get_premium_provider(config)
    with st.chat_message("assistant", avatar="🧐"):
        last_msg = next((m["content"] for m in reversed(st.session_state.chat_history) if m["role"] == "user"), "")
        context = build_context(last_msg)
        reply = st.write_stream(stream_chat_with_analyst(
            st.session_state.chat_history,
            provider=provider,
            context=context,
        ))
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
