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
/* Hero iframe gets full width; form section is narrower via columns */
.block-container {
    max-width: 960px !important;
    padding-top: 0 !important;
    padding-bottom: 40px !important;
    margin: auto !important;
}
/* ── Form inputs ── */
div[data-testid="stTextInput"] label p {
    font-size: 0.5rem;
    letter-spacing: 4px;
    color: rgba(255,255,255,0.22);
    text-transform: uppercase;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
div[data-testid="stTextInput"] input {
    background-color: rgba(255,255,255,0.02) !important;
    border: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 0 !important;
    color: #FFFFFF !important;
    font-size: 0.88rem !important;
    padding: 14px 4px !important;
    letter-spacing: 1px !important;
}
div[data-testid="stTextInput"] input:focus {
    border-bottom-color: rgba(255,255,255,0.45) !important;
    box-shadow: none !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color: rgba(255,255,255,0.1) !important;
}
/* ── Buttons ── */
div[data-testid="stButton"] > button {
    width: 100% !important;
    background: #FFFFFF !important;
    color: #000000 !important;
    font-weight: 700 !important;
    letter-spacing: 5px !important;
    font-size: 0.6rem !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 16px 0 !important;
    margin-top: 12px !important;
    transition: opacity 0.2s !important;
}
div[data-testid="stButton"] > button:hover {
    opacity: 0.82 !important;
}
/* ── Tabs ── */
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(255,255,255,0.07) !important;
    gap: 0 !important;
    margin-bottom: 28px !important;
}
div[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    color: rgba(255,255,255,0.2) !important;
    font-size: 0.52rem !important;
    letter-spacing: 5px !important;
    text-transform: uppercase !important;
    padding: 14px 28px !important;
    border: none !important;
    border-radius: 0 !important;
    font-weight: 500 !important;
}
div[data-testid="stTabs"] [aria-selected="true"] {
    color: #FFFFFF !important;
    border-bottom: 1px solid rgba(255,255,255,0.6) !important;
    background: transparent !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
div[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
}
/* ── Column gutters ── */
[data-testid="column"] { padding: 0 !important; }
/* ── Divider line ── */
hr { border-color: rgba(255,255,255,0.06) !important; margin: 0 !important; }
</style>
""", unsafe_allow_html=True)


def _render_hero():
    """Scroll-driven hero — text slides left as user scrolls, Blackstone-style."""
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;1,400&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }

html, body {
    background: #000;
    width: 100%;
    height: 100%;
    overflow: hidden;
    font-family: 'Inter', -apple-system, sans-serif;
}

.stage {
    position: relative;
    width: 100%;
    height: 100vh;
    overflow: hidden;
    display: flex;
    align-items: center;
}

/* ── Brand mark (top-left) ── */
.brand {
    position: absolute;
    top: 28px; left: 36px;
    display: flex;
    align-items: center;
    gap: 14px;
    z-index: 10;
}
.brand-mark {
    width: 30px; height: 30px;
    border: 1px solid rgba(255,255,255,0.14);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Playfair Display', serif;
    font-size: 0.85rem; font-weight: 600;
    color: rgba(255,255,255,0.35);
}
.brand-name {
    font-size: 0.47rem;
    letter-spacing: 5px;
    color: rgba(255,255,255,0.16);
    text-transform: uppercase;
}

/* ── Year tag (top-right) ── */
.year-tag {
    position: absolute;
    top: 32px; right: 36px;
    font-size: 0.45rem;
    letter-spacing: 4px;
    color: rgba(255,255,255,0.1);
    text-transform: uppercase;
    z-index: 10;
}

/* ── Hero text wrapper: fade edges ── */
.hero-wrap {
    width: 100%;
    overflow: hidden;
    -webkit-mask-image: linear-gradient(90deg,
        transparent 0%,
        #000 7%,
        #000 93%,
        transparent 100%);
    mask-image: linear-gradient(90deg,
        transparent 0%,
        #000 7%,
        #000 93%,
        transparent 100%);
}

/* ── The big text ── */
.hero-text {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: clamp(3.2rem, 8.5vw, 6.8rem);
    font-weight: 400;
    color: #fff;
    white-space: nowrap;
    letter-spacing: 0.045em;
    line-height: 1.12;
    /* starts with text offset right — only partial text visible */
    transform: translateX(28%);
    will-change: transform;
    user-select: none;
    /* very gentle momentum feel */
    transition: transform 0.18s cubic-bezier(0.22, 0.61, 0.36, 1);
}

/* ── Secondary tagline (fades in as text moves) ── */
.tagline {
    margin-top: 22px;
    font-size: 0.5rem;
    letter-spacing: 7px;
    color: rgba(255,255,255,0);
    text-transform: uppercase;
    text-align: center;
    transition: color 0.5s ease;
    user-select: none;
}

/* ── Disclaimer (bottom-left) ── */
.disclaimer {
    position: absolute;
    bottom: 30px; left: 36px;
    font-size: 0.56rem;
    color: rgba(255,255,255,0.16);
    letter-spacing: 0.3px;
    line-height: 1.9;
    z-index: 10;
}

/* ── Scroll indicator (bottom-right) ── */
.scroll-indicator {
    position: absolute;
    bottom: 28px; right: 36px;
    display: flex; flex-direction: column;
    align-items: center; gap: 8px;
    z-index: 10;
    transition: opacity 0.4s ease;
}
.scroll-indicator.fade { opacity: 0; pointer-events: none; }
.si-label {
    font-size: 0.42rem;
    letter-spacing: 4px;
    color: rgba(255,255,255,0.14);
    text-transform: uppercase;
}
.si-line {
    width: 1px; height: 28px;
    background: linear-gradient(to bottom, rgba(255,255,255,0.22), transparent);
    animation: si-pulse 2.2s ease-in-out infinite;
}
@keyframes si-pulse {
    0%, 100% { opacity: 0.3; transform: scaleY(0.9); }
    50%       { opacity: 1;   transform: scaleY(1.15); }
}

/* ── Thin progress line at very bottom ── */
.progress-track {
    position: absolute;
    bottom: 0; left: 0;
    width: 100%; height: 1px;
    background: rgba(255,255,255,0.04);
}
.progress-fill {
    height: 100%;
    width: 0%;
    background: rgba(255,255,255,0.18);
    transition: width 0.12s ease;
}

/* ── Entry animation: fade in on load ── */
.stage { animation: stage-in 1.2s ease both; }
@keyframes stage-in {
    from { opacity: 0; }
    to   { opacity: 1; }
}
</style>
</head>
<body>
<div class="stage">

    <div class="brand">
        <div class="brand-mark">B</div>
        <div class="brand-name">AI Buffett</div>
    </div>

    <div class="year-tag">Est. 2025</div>

    <!-- centre column: headline + tagline -->
    <div style="width:100%; text-align:center;">
        <div class="hero-wrap">
            <div class="hero-text" id="ht">Build wealth with AI Buffett</div>
        </div>
        <div class="tagline" id="tl">AI &nbsp;&middot;&nbsp; Powered &nbsp;&middot;&nbsp; Value &nbsp;&middot;&nbsp; Intelligence</div>
    </div>

    <div class="disclaimer">
        Investing involves risks,<br>including loss of capital.
    </div>

    <div class="scroll-indicator" id="si">
        <div class="si-label">Scroll</div>
        <div class="si-line"></div>
    </div>

    <div class="progress-track">
        <div class="progress-fill" id="pf"></div>
    </div>

</div>

<script>
(function () {
    var ht = document.getElementById('ht');
    var tl = document.getElementById('tl');
    var si = document.getElementById('si');
    var pf = document.getElementById('pf');

    /* 0 = initial (text right), 1 = fully scrolled (text left) */
    var progress  = 0;
    var animDone  = false;
    var velocity  = 0;        /* for momentum smoothing */
    var rafId     = null;

    var START_X   =  32;      /* translateX % at progress 0 */
    var END_X     = -72;      /* translateX % at progress 1 */
    var THRESHOLD = 0.98;     /* when to consider animation "done" */

    function lerp(a, b, t) { return a + (b - a) * t; }
    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

    function render() {
        var x = lerp(START_X, END_X, progress);
        ht.style.transform = 'translateX(' + x + '%)';

        /* tagline fades in above 65% progress */
        var alpha = clamp((progress - 0.65) / 0.35, 0, 1) * 0.28;
        tl.style.color = 'rgba(255,255,255,' + alpha + ')';

        /* hide scroll indicator after 18% */
        if (progress > 0.18) si.classList.add('fade');
        else                  si.classList.remove('fade');

        /* progress bar */
        pf.style.width = (progress * 100) + '%';

        animDone = (progress >= THRESHOLD);
    }

    /* ── Wheel handler ── */
    window.addEventListener('wheel', function (e) {
        /* block page scroll while animation is not done, or while scrolling back */
        if (!animDone || e.deltaY < 0) {
            e.preventDefault();
        }
        progress += e.deltaY / 1100;
        progress  = clamp(progress, 0, 1);
        render();
    }, { passive: false });

    /* ── Touch handler ── */
    var lastTouchY = 0;
    window.addEventListener('touchstart', function (e) {
        lastTouchY = e.touches[0].clientY;
    }, { passive: true });

    window.addEventListener('touchmove', function (e) {
        var dy = lastTouchY - e.touches[0].clientY;
        lastTouchY = e.touches[0].clientY;
        if (!animDone || dy < 0) e.preventDefault();
        progress += dy / 600;
        progress  = clamp(progress, 0, 1);
        render();
    }, { passive: false });

    /* initialise */
    render();
}());
</script>
</body>
</html>
"""
    components.html(html, height=520, scrolling=False)


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
<div class="footer">&copy; 2025-2026 AI Buffett &nbsp;&middot;&nbsp; AI-Powered Value Intelligence</div>
</body>
</html>
"""
    components.html(html, height=50, scrolling=False)


def _save_user(username: str, data: dict) -> bool:
    """Append a new user to users.yaml. Returns True on success."""
    try:
        if _USERS_FILE.exists():
            with open(_USERS_FILE, encoding="utf-8") as f:
                content = yaml.safe_load(f) or {}
        else:
            content = {}
        users = content.setdefault("users", {})
        users[username] = data
        with open(_USERS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(content, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        logger.error("Failed to save user: %s", e)
        return False


import re as _re

def _validate_registration(username, display_name, email, password, confirm) -> Optional[str]:
    """Returns error message string, or None if valid."""
    if not all([username, display_name, email, password, confirm]):
        return "All fields are required."
    if not _re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return "Username must be 3–20 characters, letters/numbers/underscore only."
    if not _re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return "Invalid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if password != confirm:
        return "Passwords do not match."
    users = _load_users()
    if username.lower() in users:
        return "Username already taken."
    return None


def register_user(username: str, display_name: str, email: str, password: str) -> bool:
    """Create a new free-tier user. Returns True on success."""
    data = {
        "password": hash_password(password),
        "name": display_name.strip(),
        "email": email.strip().lower(),
        "role": "viewer",
    }
    return _save_user(username.strip().lower(), data)


def render_login_page():
    """Blackstone-inspired login/register — scroll-driven hero + centered tab form."""
    _inject_page_css()
    _render_hero()

    # Narrow the form to ~380px by using a centred column
    _, col, _ = st.columns([1, 1.6, 1])

    with col:
        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        # ── Login tab ──
        with tab_login:
            username = st.text_input("Username", placeholder="username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="password", key="login_password")

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

        # ── Register tab ──
        with tab_register:
            reg_username     = st.text_input("Username",         placeholder="e.g. john_doe",     key="reg_username")
            reg_display_name = st.text_input("Full Name",        placeholder="e.g. John Doe",      key="reg_name")
            reg_email        = st.text_input("Email",            placeholder="you@example.com",    key="reg_email")
            reg_password     = st.text_input("Password",         type="password", placeholder="min 8 characters", key="reg_password")
            reg_confirm      = st.text_input("Confirm Password", type="password", placeholder="repeat password",   key="reg_confirm")

            if st.button("CREATE  ACCOUNT", key="reg_btn"):
                err = _validate_registration(reg_username, reg_display_name, reg_email, reg_password, reg_confirm)
                if err:
                    st.error(err)
                else:
                    ok = register_user(reg_username, reg_display_name, reg_email, reg_password)
                    if ok:
                        st.success("Account created. You can now sign in.")
                    else:
                        st.error("Registration failed. Please try again.")

    _render_footer()
