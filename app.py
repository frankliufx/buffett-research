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

# ── 侧边栏顶部：v2 brand mark + 用户信息 + 登出 ──────────────────
user = get_current_user()
if user:
    with st.sidebar:
        # v2 brand mark — replaces the bare role text with a workspace identity
        st.markdown(
            """
            <div style="
                padding: 14px 4px 18px;
                margin-bottom: 8px;
                border-bottom: 1px solid #2A2A33;
            ">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
                    <div style="width:6px;height:6px;background:#C9A962;border-radius:50%;"></div>
                    <span style="font-family:'Cormorant Garamond',Georgia,serif;font-size:1.1rem;font-weight:600;color:#F2F2F5;letter-spacing:0.005em;">
                        AI <span style="color:#C9A962;font-style:italic;">Buffett</span>
                    </span>
                </div>
                <div style="
                    background: #16161F;
                    border: 1px solid #2A2A33;
                    border-radius: 6px;
                    padding: 10px 12px;
                ">
                    <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:4px;">
                        <span style="font-family:'JetBrains Mono',monospace;font-size:0.74rem;font-weight:600;color:#F2F2F5;letter-spacing:-0.01em;">{name}</span>
                        <span style="font-size:0.55rem;color:#C9A962;border:1px solid #C9A96255;background:#C9A96212;padding:1px 6px;border-radius:3px;letter-spacing:0.5px;text-transform:uppercase;">{role}</span>
                    </div>
                    <div style="font-size:0.6rem;color:#5A5A66;letter-spacing:0.3px;">workspace · v2</div>
                </div>
            </div>
            """.format(
                role=user.get("role", "viewer").lower(),
                name=user.get("name", user.get("username", "")),
            ),
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", key="logout_btn", use_container_width=True):
            logout()

# ── 页面导航（v2 audit-recommended order）──────────────────────────
# Group 1: 工作流 (workspace + daily loops)
# Group 2: 飞轮记录 (the moat — promoted to #4 from #8)
# Group 3: 工具/参考 (auxiliary)
pg = st.navigation({
    "Workspace": [
        st.Page("pages/0_home.py",        title="Home",         icon="🏠", default=True),
        st.Page("pages/1_dashboard.py",   title="Dashboard",    icon="📊"),
        st.Page("pages/2_analysis.py",    title="Analysis",     icon="🔍"),
        st.Page("pages/6_trackrecord.py", title="Track Record", icon="🏆"),
    ],
    "AI Tools": [
        st.Page("pages/7_hedgefund.py",   title="AI Hedge Fund", icon="🏦"),
        st.Page("pages/3_chat.py",        title="AI Advisor",   icon="💬"),
    ],
    "Markets": [
        st.Page("pages/5_portfolio.py",   title="Portfolio",    icon="💼"),
        st.Page("pages/1_sentiment.py",   title="Sentiment",    icon="📡"),
    ],
    "Account": [
        st.Page("pages/4_settings.py",    title="Settings",     icon="⚙️"),
    ],
})

pg.run()
