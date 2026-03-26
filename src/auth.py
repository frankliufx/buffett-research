"""Authentication module — login verification and user management"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components
import yaml

logger = logging.getLogger(__name__)

_USERS_FILE = Path(__file__).parent.parent / "users.yaml"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.strip().encode()).hexdigest()


def _load_users() -> dict:
    """Load users from Streamlit secrets (production) or users.yaml (local dev)."""
    try:
        if hasattr(st, "secrets") and "users" in st.secrets:
            result = {}
            for k, v in st.secrets["users"].items():
                result[str(k).lower()] = dict(v) if hasattr(v, "keys") else {"password": str(v)}
            return result
    except Exception as e:
        logger.debug("Secrets load skipped: %s", e)

    if _USERS_FILE.exists():
        try:
            with open(_USERS_FILE, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("users", {})
        except Exception as e:
            logger.warning("users.yaml read failed: %s", e)

    return {}


def authenticate(username: str, password: str) -> Optional[dict]:
    """Verify credentials. Returns user info dict or None."""
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


# ---------------------------------------------------------------------------
# Login page rendering
# ---------------------------------------------------------------------------

def _inject_page_css():
    """Inject CSS to style the page and Streamlit widgets."""
    st.markdown("""
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stSidebar"] {display: none !important;}
[data-testid="collapsedControl"] {display: none !important;}
.stApp {background-color: #08080C !important;}
.block-container {
    max-width: 420px !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    margin: auto !important;
}
div[data-testid="stTextInput"] label p {
    font-size: 0.62rem;
    letter-spacing: 3px;
    color: #5A5A6A;
    text-transform: uppercase;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
div[data-testid="stTextInput"] input {
    background-color: #0F0F16 !important;
    border: 1px solid #252530 !important;
    border-radius: 2px !important;
    color: #E8E8F0 !important;
    font-size: 0.9rem !important;
    padding: 13px 16px !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #C9A962 !important;
    box-shadow: 0 0 0 2px rgba(201,169,98,0.15) !important;
}
div[data-testid="stButton"] > button {
    width: 100% !important;
    background: #C9A962 !important;
    color: #08080C !important;
    font-weight: 700 !important;
    letter-spacing: 3px !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 2px !important;
    padding: 14px 0 !important;
    margin-top: 6px !important;
}
div[data-testid="stButton"] > button:hover {
    background: #B89440 !important;
}
</style>
""", unsafe_allow_html=True)


def _render_logo():
    """Render the logo header using components.html (bypasses markdown parser)."""
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
    background: #06060A;
    font-family: 'Inter', -apple-system, sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 36px 0 28px;
}
.wrap { text-align: center; }

/* Logo mark — minimal square with letter */
.logo-mark {
    width: 52px;
    height: 52px;
    border: 1.5px solid #C9A962;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 24px;
    position: relative;
}
.logo-mark::before {
    content: '';
    position: absolute;
    inset: 4px;
    border: 1px solid rgba(201,169,98,0.25);
}
.logo-mark-letter {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #C9A962;
    line-height: 1;
}

.brand-name {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.9rem;
    font-weight: 300;
    color: #E8E8F0;
    letter-spacing: 8px;
    text-transform: uppercase;
    line-height: 1;
    margin-bottom: 6px;
}
.brand-sub {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.9rem;
    font-weight: 700;
    color: #C9A962;
    letter-spacing: 8px;
    text-transform: uppercase;
    line-height: 1;
    margin-bottom: 24px;
}
.divider {
    display: flex;
    align-items: center;
    gap: 12px;
    max-width: 260px;
    margin: 0 auto;
}
.divider-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, transparent, #C9A962);
}
.divider-line.right {
    background: linear-gradient(90deg, #C9A962, transparent);
}
.divider-text {
    font-size: 0.48rem;
    color: #2A2A36;
    letter-spacing: 3px;
    text-transform: uppercase;
    white-space: nowrap;
    font-family: 'Inter', sans-serif;
}
</style>
</head>
<body>
<div class="wrap">
    <div class="logo-mark">
        <div class="logo-mark-letter">B</div>
    </div>
    <div class="brand-name">BUFFETT</div>
    <div class="brand-sub">RESEARCH</div>
    <div class="divider">
        <div class="divider-line"></div>
        <div class="divider-text">AUTHORIZED ACCESS ONLY</div>
        <div class="divider-line right"></div>
    </div>
</div>
</body>
</html>
"""
    components.html(html, height=300, scrolling=False)


def _render_footer():
    """Render footer using components.html."""
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
    background: #08080C;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 24px 0;
}
.footer {
    text-align: center;
    font-size: 0.5rem;
    color: #252530;
    letter-spacing: 2px;
    text-transform: uppercase;
    line-height: 2;
}
</style>
</head>
<body>
<div class="footer">
    &copy; 2025-2026 BUFFETT RESEARCH &nbsp;&middot;&nbsp; CONFIDENTIAL
</div>
</body>
</html>
"""
    components.html(html, height=80, scrolling=False)


def render_login_page():
    """Render the Blackstone-style login page."""
    _inject_page_css()
    _render_logo()

    username = st.text_input(
        "Username",
        placeholder="Enter username",
        key="login_username",
    )
    password = st.text_input(
        "Password",
        type="password",
        placeholder="Enter password",
        key="login_password",
    )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if st.button("SIGN  IN", key="login_btn"):
        if not username or not password:
            st.error("Please enter username and password.")
        else:
            user = authenticate(username, password)
            if user:
                st.session_state["authenticated"] = True
                st.session_state["auth_user"] = user
                st.rerun()
            else:
                st.error("Invalid credentials. Contact admin for access.")

    _render_footer()
