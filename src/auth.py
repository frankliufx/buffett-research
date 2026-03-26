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
    """Inject CSS — pure black Blackstone aesthetic."""
    st.markdown("""
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stSidebar"] {display: none !important;}
[data-testid="collapsedControl"] {display: none !important;}
.stApp {background-color: #000000 !important;}
.block-container {
    max-width: 380px !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    margin: auto !important;
}
div[data-testid="stTextInput"] label p {
    font-size: 0.55rem;
    letter-spacing: 4px;
    color: rgba(255,255,255,0.25);
    text-transform: uppercase;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
div[data-testid="stTextInput"] input {
    background-color: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 0 !important;
    color: #FFFFFF !important;
    font-size: 0.85rem !important;
    padding: 14px 16px !important;
    letter-spacing: 1px !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: rgba(255,255,255,0.3) !important;
    box-shadow: none !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color: rgba(255,255,255,0.12) !important;
}
div[data-testid="stButton"] > button {
    width: 100% !important;
    background: #FFFFFF !important;
    color: #000000 !important;
    font-weight: 600 !important;
    letter-spacing: 4px !important;
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 15px 0 !important;
    margin-top: 8px !important;
    transition: opacity 0.2s !important;
}
div[data-testid="stButton"] > button:hover {
    background: #FFFFFF !important;
    opacity: 0.85 !important;
}
</style>
""", unsafe_allow_html=True)


def _render_hero():
    """Blackstone-style scrolling hero — 纯黑背景、超大衬线字、水平滚动动画"""
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }

body {
    background: #000000;
    overflow: hidden;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    font-family: 'Inter', -apple-system, sans-serif;
}

/* ── Scrolling headline ── */
.hero-track {
    white-space: nowrap;
    font-family: 'Playfair Display', Georgia, 'Times New Roman', serif;
    font-size: clamp(3.5rem, 10vw, 7rem);
    font-weight: 400;
    color: #FFFFFF;
    letter-spacing: 0.04em;
    line-height: 1.1;
    animation: scroll-left 20s linear infinite;
    padding: 0 40px;
    user-select: none;
}

@keyframes scroll-left {
    0%   { transform: translateX(10%); }
    100% { transform: translateX(-55%); }
}

/* Fade edges for seamless look */
.hero-mask {
    position: relative;
    overflow: hidden;
}
.hero-mask::before,
.hero-mask::after {
    content: '';
    position: absolute;
    top: 0; bottom: 0; width: 80px;
    z-index: 2;
    pointer-events: none;
}
.hero-mask::before {
    left: 0;
    background: linear-gradient(90deg, #000000, transparent);
}
.hero-mask::after {
    right: 0;
    background: linear-gradient(90deg, transparent, #000000);
}

/* ── Top: small brand mark ── */
.top-bar {
    position: absolute;
    top: 28px; left: 36px;
    display: flex;
    align-items: center;
    gap: 14px;
}
.mark {
    width: 32px; height: 32px;
    border: 1px solid rgba(255,255,255,0.15);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Playfair Display', serif;
    font-size: 0.9rem;
    font-weight: 700;
    color: rgba(255,255,255,0.4);
}
.brand-text {
    font-size: 0.55rem;
    letter-spacing: 5px;
    color: rgba(255,255,255,0.2);
    text-transform: uppercase;
}

/* ── Bottom left: risk disclaimer ── */
.disclaimer {
    position: absolute;
    bottom: 28px; left: 36px;
    font-size: 0.6rem;
    color: rgba(255,255,255,0.18);
    letter-spacing: 1px;
    line-height: 1.8;
    max-width: 300px;
}

/* ── Bottom right: subtle CTA hint ── */
.cta-hint {
    position: absolute;
    bottom: 28px; right: 36px;
    font-size: 0.5rem;
    letter-spacing: 4px;
    color: rgba(255,255,255,0.12);
    text-transform: uppercase;
}

/* Pause animation on hover */
.hero-mask:hover .hero-track {
    animation-play-state: paused;
}
</style>
</head>
<body>
    <div class="top-bar">
        <div class="mark">B</div>
        <div class="brand-text">Buffett Research</div>
    </div>

    <div class="hero-mask">
        <div class="hero-track">
            Invest with conviction, not with emotion&nbsp;&nbsp;&nbsp;&mdash;&nbsp;&nbsp;&nbsp;Build wealth with Buffett Research&nbsp;&nbsp;&nbsp;&mdash;&nbsp;&nbsp;&nbsp;Value investing, redefined by AI
        </div>
    </div>

    <div class="disclaimer">
        Investing involves risks, including<br>loss of capital.
    </div>

    <div class="cta-hint">Sign in below &darr;</div>
</body>
</html>
"""
    components.html(html, height=420, scrolling=False)


def _render_footer():
    """Minimal footer"""
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
    background: #000000;
    display: flex; align-items: center; justify-content: center;
    height: 100%; padding: 16px 0;
}
.footer {
    text-align: center;
    font-size: 0.45rem;
    color: rgba(255,255,255,0.1);
    letter-spacing: 3px;
    text-transform: uppercase;
}
</style>
</head>
<body>
<div class="footer">&copy; 2025-2026 Buffett Research &nbsp;&middot;&nbsp; AI-Powered Value Intelligence</div>
</body>
</html>
"""
    components.html(html, height=50, scrolling=False)


def render_login_page():
    """Blackstone-inspired login — scrolling hero + minimal form."""
    _inject_page_css()
    _render_hero()

    username = st.text_input(
        "Username",
        placeholder="username",
        key="login_username",
    )
    password = st.text_input(
        "Password",
        type="password",
        placeholder="password",
        key="login_password",
    )

    if st.button("SIGN  IN", key="login_btn"):
        if not username or not password:
            st.error("Please enter credentials.")
        else:
            user = authenticate(username, password)
            if user:
                st.session_state["authenticated"] = True
                st.session_state["auth_user"] = user
                st.rerun()
            else:
                st.error("Invalid credentials.")

    _render_footer()
