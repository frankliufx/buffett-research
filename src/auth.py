"""Authentication module — login verification and user management"""

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
    """Load users from Streamlit secrets (production) or users.yaml (local dev)."""
    # 1. Streamlit secrets (Streamlit Cloud)
    try:
        if hasattr(st, "secrets") and "users" in st.secrets:
            result = {}
            for k, v in st.secrets["users"].items():
                result[str(k).lower()] = dict(v) if hasattr(v, "keys") else {"password": str(v)}
            return result
    except Exception as e:
        logger.debug("Secrets load skipped: %s", e)

    # 2. Local users.yaml (local development)
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
# Login page — Blackstone / BlackRock style (black & gold)
# ---------------------------------------------------------------------------

_LOGIN_CSS = """
<style>
/* Hide default Streamlit chrome */
#MainMenu { visibility: hidden; }
header { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }

/* Full-screen dark background */
.stApp {
    background-color: #08080C;
}

/* Center the login card */
[data-testid="stAppViewContainer"] > .main {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
}

[data-testid="stAppViewContainer"] > .main .block-container {
    width: 100%;
    max-width: 420px;
    padding: 0 32px;
    margin: auto;
}

/* Input labels */
div[data-testid="stTextInput"] label p {
    font-size: 0.62rem;
    letter-spacing: 3px;
    color: #5A5A6A;
    font-weight: 400;
    text-transform: uppercase;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Input boxes */
div[data-testid="stTextInput"] input {
    background-color: #0F0F16 !important;
    border: 1px solid #252530 !important;
    border-radius: 2px !important;
    color: #E8E8F0 !important;
    font-size: 0.9rem !important;
    padding: 13px 16px !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}

div[data-testid="stTextInput"] input:focus {
    border-color: #C9A962 !important;
    box-shadow: 0 0 0 2px rgba(201,169,98,0.15) !important;
    outline: none !important;
}

/* Sign In button */
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
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    cursor: pointer !important;
    transition: background 0.2s !important;
}

div[data-testid="stButton"] > button:hover {
    background: #B89440 !important;
}

/* Error alert */
div[data-testid="stAlert"] {
    background-color: #180808 !important;
    border: 1px solid #3A1010 !important;
    border-radius: 2px !important;
    color: #FF6B6B !important;
}

/* Remove extra padding */
.block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
</style>
"""

_LOGO_HTML = """
<div style="text-align:center; padding:48px 0 36px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

    <!-- Diamond mark -->
    <div style="
        display:inline-block;
        width:56px; height:56px;
        background:#C9A962;
        transform:rotate(45deg);
        margin-bottom:28px;
        box-shadow:0 0 32px rgba(201,169,98,0.25);
    ">
        <div style="
            transform:rotate(-45deg);
            display:flex; align-items:center; justify-content:center;
            width:100%; height:100%;
            font-size:1.4rem; color:#08080C; font-weight:900; line-height:1;
        ">B</div>
    </div>

    <!-- Platform label -->
    <div style="
        font-size:0.52rem; letter-spacing:5px; color:#C9A962;
        text-transform:uppercase; font-weight:500; margin-bottom:12px;
    ">Value Intelligence Platform</div>

    <!-- Brand name -->
    <div style="
        font-size:1.75rem; font-weight:200; color:#E8E8F0;
        letter-spacing:7px; text-transform:uppercase; line-height:1.1;
        margin-bottom:4px;
    ">BUFFETT</div>
    <div style="
        font-size:1.75rem; font-weight:700; color:#C9A962;
        letter-spacing:7px; text-transform:uppercase; line-height:1.1;
        margin-bottom:28px;
    ">RESEARCH</div>

    <!-- Divider -->
    <div style="
        display:flex; align-items:center; gap:10px;
        margin:0 auto; max-width:280px;
    ">
        <div style="flex:1; height:1px; background:linear-gradient(to right,transparent,#252530);"></div>
        <div style="font-size:0.52rem; color:#34343F; letter-spacing:2px; white-space:nowrap;">
            AUTHORIZED ACCESS ONLY
        </div>
        <div style="flex:1; height:1px; background:linear-gradient(to left,transparent,#252530);"></div>
    </div>
</div>
"""

_FOOTER_HTML = """
<div style="
    text-align:center; margin-top:40px; padding-bottom:32px;
    font-size:0.52rem; color:#252530;
    letter-spacing:2px; text-transform:uppercase; line-height:2;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
">
    &copy; 2025 BUFFETT RESEARCH &nbsp;&middot;&nbsp; CONFIDENTIAL
</div>
"""


def render_login_page():
    """Render the Blackstone-style login page."""
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(_LOGO_HTML, unsafe_allow_html=True)

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

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

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

    st.markdown(_FOOTER_HTML, unsafe_allow_html=True)
