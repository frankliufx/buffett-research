"""认证模块 — 登录验证 + 用户管理"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

import streamlit as st
import yaml

logger = logging.getLogger(__name__)

_USERS_FILE = Path(__file__).parent.parent / "users.yaml"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.strip().encode()).hexdigest()


def _load_users() -> dict:
    """加载用户列表，优先级：Streamlit secrets > users.yaml"""
    # 1. Streamlit Cloud secrets（生产环境）
    try:
        if hasattr(st, "secrets") and "users" in st.secrets:
            return {k: dict(v) if hasattr(v, "keys") else {"password": v}
                    for k, v in st.secrets["users"].items()}
    except Exception:
        pass

    # 2. 本地 users.yaml（本地开发）
    if _USERS_FILE.exists():
        try:
            with open(_USERS_FILE) as f:
                data = yaml.safe_load(f) or {}
            return data.get("users", {})
        except Exception as e:
            logger.warning("users.yaml read failed: %s", e)

    return {}


def authenticate(username: str, password: str) -> Optional[dict]:
    """验证用户名密码，返回用户信息 dict 或 None"""
    if not username or not password:
        return None
    users = _load_users()
    username = username.strip().lower()
    user = users.get(username)
    if not user:
        return None
    stored_hash = user.get("password", user) if isinstance(user, dict) else user
    if stored_hash == hash_password(password):
        return {
            "username": username,
            "name": user.get("name", username.title()) if isinstance(user, dict) else username.title(),
            "role": user.get("role", "viewer") if isinstance(user, dict) else "viewer",
        }
    return None


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def get_current_user() -> Optional[dict]:
    return st.session_state.get("auth_user")


def logout():
    st.session_state["authenticated"] = False
    st.session_state.pop("auth_user", None)
    st.rerun()


# ── 登录页面 CSS ──────────────────────────────────────────────────

_LOGIN_CSS = """
<style>
/* ── 隐藏 Streamlit 默认 UI ── */
#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stDeployButton { display: none !important; }

[data-testid="stSidebar"] { display: none !important; }

/* ── 全屏黑色背景 ── */
.stApp, [data-testid="stAppViewContainer"] {
    background: #08080C !important;
}

/* ── 登录容器居中 ── */
.main .block-container {
    max-width: 460px !important;
    margin: 0 auto !important;
    padding: 0 24px !important;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

/* ── 输入框 ── */
[data-testid="stTextInput"] label {
    font-size: 0.6rem !important;
    letter-spacing: 3px !important;
    color: #5A5A68 !important;
    font-weight: 400 !important;
    text-transform: uppercase !important;
}
[data-testid="stTextInput"] input {
    background: #0F0F14 !important;
    border: 1px solid #2A2A35 !important;
    border-radius: 2px !important;
    color: #EAEAEA !important;
    font-size: 0.92rem !important;
    padding: 14px 16px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #C9A962 !important;
    box-shadow: 0 0 0 1px #C9A96230 !important;
}

/* ── 登录按钮 ── */
[data-testid="stButton"] button {
    width: 100% !important;
    background: linear-gradient(135deg, #C9A962, #B8954F) !important;
    color: #08080C !important;
    font-weight: 700 !important;
    letter-spacing: 3px !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 2px !important;
    padding: 14px 0 !important;
    margin-top: 8px !important;
    cursor: pointer !important;
    transition: opacity 0.2s !important;
}
[data-testid="stButton"] button:hover {
    opacity: 0.9 !important;
}

/* ── 错误提示 ── */
[data-testid="stAlert"] {
    background: #1A0A0A !important;
    border: 1px solid #3A1A1A !important;
    border-radius: 2px !important;
    color: #EF4444 !important;
}

/* ── 分割线 ── */
hr { border-color: #1E1E26 !important; }
</style>
"""

_LOGIN_HEADER_HTML = """
<div style="text-align:center; padding: 0 0 40px; user-select:none;">

    <!-- 钻石 Logo 动画 -->
    <div style="position:relative; display:inline-block; margin-bottom:32px;">
        <div style="
            width:72px; height:72px;
            background: linear-gradient(135deg, #C9A962 0%, #8A6A2A 50%, #C9A962 100%);
            clip-path: polygon(50% 0%, 100% 35%, 80% 100%, 20% 100%, 0% 35%);
            margin: 0 auto;
            box-shadow: 0 0 40px #C9A96240;
        "></div>
        <div style="
            position:absolute; top:50%; left:50%;
            transform:translate(-50%,-50%);
            font-size:1.6rem; color:#08080C; font-weight:700; line-height:1;
        ">◆</div>
    </div>

    <!-- Brand -->
    <div style="
        font-size:0.5rem; letter-spacing:6px; color:#C9A962;
        text-transform:uppercase; font-weight:500; margin-bottom:14px;
    ">Value Intelligence Platform</div>

    <div style="
        font-size:1.9rem; font-weight:200; color:#EAEAEA;
        letter-spacing:8px; text-transform:uppercase; line-height:1.1;
        margin-bottom:6px;
    ">BUFFETT</div>
    <div style="
        font-size:1.9rem; font-weight:700; color:#C9A962;
        letter-spacing:8px; text-transform:uppercase; line-height:1.1;
        margin-bottom:28px;
    ">RESEARCH</div>

    <!-- 装饰线 -->
    <div style="display:flex; align-items:center; gap:12px; margin: 0 auto; max-width:260px;">
        <div style="flex:1; height:1px; background:linear-gradient(to right, transparent, #2A2A35);"></div>
        <div style="font-size:0.55rem; color:#3A3A46; letter-spacing:3px; white-space:nowrap;">AUTHORIZED ACCESS ONLY</div>
        <div style="flex:1; height:1px; background:linear-gradient(to left, transparent, #2A2A35);"></div>
    </div>
</div>
"""

_LOGIN_FOOTER_HTML = """
<div style="
    text-align:center; margin-top:48px;
    font-size:0.55rem; color:#2A2A35;
    letter-spacing:2px; text-transform:uppercase;
    line-height:2;
">
    © 2025 BUFFETT RESEARCH&nbsp;&nbsp;·&nbsp;&nbsp;CONFIDENTIAL<br>
    FOR AUTHORIZED SUBSCRIBERS ONLY
</div>
"""


def render_login_page():
    """渲染黑金风格登录页面"""
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(_LOGIN_HEADER_HTML, unsafe_allow_html=True)

    # 表单容器
    st.markdown('<div style="margin-top:8px;">', unsafe_allow_html=True)

    username = st.text_input(
        "Username",
        placeholder="输入用户名",
        key="login_username",
    )
    password = st.text_input(
        "Password",
        type="password",
        placeholder="输入密码",
        key="login_password",
    )

    st.markdown('<div style="margin-top:4px;"></div>', unsafe_allow_html=True)

    if st.button("SIGN IN", key="login_btn"):
        user = authenticate(username, password)
        if user:
            st.session_state["authenticated"] = True
            st.session_state["auth_user"] = user
            st.rerun()
        else:
            st.error("用户名或密码错误，请联系管理员获取访问权限。")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(_LOGIN_FOOTER_HTML, unsafe_allow_html=True)
