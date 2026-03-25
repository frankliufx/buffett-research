"""
BUFFETT RESEARCH — AI-Powered Value Intelligence Platform
"""

import streamlit as st

st.set_page_config(
    page_title="Buffett Research · AI",
    page_icon="◆",
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
        if st.button("Sign Out", key="logout_btn", use_container_width=True):
            logout()

# ── 页面导航 ──────────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/0_home.py",       title="Home",       icon="🏠", default=True),
    st.Page("pages/1_dashboard.py",  title="Dashboard",  icon="📊"),
    st.Page("pages/1_sentiment.py",  title="Sentiment",  icon="📡"),
    st.Page("pages/2_analysis.py",   title="Analysis",   icon="🔍"),
    st.Page("pages/3_chat.py",       title="AI Advisor", icon="💬"),
    st.Page("pages/4_settings.py",   title="Settings",   icon="⚙️"),
])

pg.run()
