"""
BUFFETT RESEARCH — AI-Powered Value Intelligence Platform
"""

import streamlit as st

st.set_page_config(
    page_title="AI Buffett · Research",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 登录验证（必须在任何页面内容之前）──────────────────────────────
from src.auth import is_authenticated, render_login_page

if not is_authenticated():
    render_login_page()
    st.stop()  # 未登录时阻止后续内容渲染

# ── 已登录：初始化应用 ────────────────────────────────────────────
from src.config import load_config
from src.auth import get_current_user, logout

if "config" not in st.session_state:
    st.session_state.config = load_config()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Auto-start background scheduler if notifications are enabled
if st.session_state.config.notify.enabled:
    try:
        from src.scheduler import start_background_scheduler
        start_background_scheduler()
    except Exception:
        pass

# ── 侧边栏顶部：用户信息 + 登出 ──────────────────────────────────
user = get_current_user()
if user:
    with st.sidebar:
        st.markdown(
            """
            <div style="
                padding: 12px 16px;
                background: #0F0F14;
                border: 1px solid #1E1E26;
                border-radius: 2px;
                margin-bottom: 16px;
            ">
                <div style="font-size:0.6rem; color:#C9A962; letter-spacing:2px; text-transform:uppercase; margin-bottom:4px;">
                    {role}
                </div>
                <div style="font-size:0.92rem; color:#EAEAEA; font-weight:500;">
                    {name}
                </div>
            </div>
            """.format(
                role=user.get("role", "viewer").upper(),
                name=user.get("name", user.get("username", "")),
            ),
            unsafe_allow_html=True,
        )
        if st.button("退出登录", key="logout_btn", use_container_width=True):
            logout()

# ── 页面导航 ──────────────────────────────────────────────────────
pg = st.navigation({
    "概览": [
        st.Page("pages/0_home.py",        title="首页",       icon="🏠", default=True),
        st.Page("pages/1_dashboard.py",   title="市场行情",   icon="📊"),
        st.Page("pages/5_portfolio.py",   title="我的持仓",   icon="💼"),
    ],
    "分析工具": [
        st.Page("pages/2_analysis.py",    title="深度分析",   icon="🔍"),
        st.Page("pages/7_hedgefund.py",   title="AI对冲基金", icon="🏦"),
        st.Page("pages/3_chat.py",        title="AI投资顾问", icon="💬"),
        st.Page("pages/9_screener.py",    title="智能选股",   icon="🔎"),
    ],
    "洞察": [
        st.Page("pages/1_sentiment.py",   title="市场情绪",   icon="📡"),
        st.Page("pages/6_trackrecord.py", title="历史战绩",   icon="🏆"),
        st.Page("pages/8_decisions.py",   title="投资决策",   icon="📋"),
    ],
    "设置": [
        st.Page("pages/4_settings.py",    title="系统设置",   icon="⚙️"),
    ],
})

pg.run()
