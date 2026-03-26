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
    max-width: 1140px !important;
    padding-top: 0 !important;
    padding-bottom: 48px !important;
    margin: auto !important;
}
/* ── Eliminate gaps between component blocks ── */
[data-testid="stVerticalBlock"] { gap: 0 !important; }
.element-container { margin-bottom: 0 !important; padding: 0 !important; }
iframe { display: block !important; border: none !important; }
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
    """Auto-playing Blackstone-style marquee hero — infinite CSS scroll, no interaction needed."""
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,300;0,400;1,300&family=Inter:wght@200;300;400&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;overflow:hidden;font-family:'Inter',-apple-system,sans-serif}

/* ── Page entry fade ── */
body{animation:pg-in 1.4s ease both}
@keyframes pg-in{from{opacity:0}to{opacity:1}}

.stage{
  position:relative;width:100%;height:100vh;
  display:flex;flex-direction:column;justify-content:center;
  overflow:hidden;
}

/* ── Top rule ── */
.top-rule{
  position:absolute;top:0;left:0;width:0;height:1px;
  background:rgba(255,255,255,0.07);
  animation:rule-in 2s ease 0.4s both;
}
@keyframes rule-in{to{width:100%}}

/* ── Brand (top-left) ── */
.brand{
  position:absolute;top:26px;left:36px;
  display:flex;align-items:center;gap:13px;z-index:10;
  animation:fade-dn 0.8s ease 0.6s both;
}
@keyframes fade-dn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
.b-mark{
  width:28px;height:28px;
  border:1px solid rgba(255,255,255,0.16);
  display:flex;align-items:center;justify-content:center;
  font-family:'Playfair Display',serif;
  font-size:0.82rem;font-weight:400;color:rgba(255,255,255,0.42);
}
.b-name{font-size:0.44rem;letter-spacing:5px;color:rgba(255,255,255,0.15);text-transform:uppercase}

/* ── Top-right tag ── */
.yr{
  position:absolute;top:30px;right:36px;z-index:10;
  font-size:0.42rem;letter-spacing:4px;color:rgba(255,255,255,0.1);text-transform:uppercase;
  animation:fade-dn 0.8s ease 0.7s both;
}

/* ── Deco label above text ── */
.deco-row{
  display:flex;align-items:center;gap:16px;
  padding:0 7%;margin-bottom:14px;
  animation:fade-up 1s ease 0.9s both;
}
@keyframes fade-up{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.deco-ln{flex:1;height:1px;background:rgba(255,255,255,0.06)}
.deco-lbl{
  font-size:0.38rem;letter-spacing:6px;
  color:rgba(255,255,255,0.12);text-transform:uppercase;white-space:nowrap;
}

/* ── Marquee container ── */
.mq-outer{
  width:100%;overflow:hidden;
  /* soft fade at edges */
  -webkit-mask-image:linear-gradient(90deg,transparent 0%,#000 5%,#000 95%,transparent 100%);
  mask-image:linear-gradient(90deg,transparent 0%,#000 5%,#000 95%,transparent 100%);
  animation:fade-up 1s ease 1s both;
}

/* ── Marquee track: duplicate text for seamless loop ── */
.mq-track{
  display:inline-flex;
  animation:march 26s linear infinite;
}
.mq-track:hover{animation-play-state:paused}

.mq-item{
  font-family:'Playfair Display',Georgia,serif;
  font-size:clamp(3.4rem,8.8vw,7rem);
  font-weight:300;
  color:#fff;
  white-space:nowrap;
  letter-spacing:0.04em;
  line-height:1.1;
  user-select:none;
}
.mq-sep{
  font-family:'Playfair Display',serif;
  font-size:clamp(3.4rem,8.8vw,7rem);
  font-weight:200;
  color:rgba(255,255,255,0.18);
  padding:0 0.4em;
  user-select:none;
}

/* translateX(-50%) because we have 2 identical copies */
@keyframes march{
  0%  {transform:translateX(0)}
  100%{transform:translateX(-50%)}
}

/* ── Sub-tags row ── */
.sub-row{
  display:flex;align-items:center;justify-content:center;gap:20px;
  margin-top:24px;
  animation:fade-up 1s ease 1.3s both;
}
.sub-tag{font-size:0.46rem;letter-spacing:5px;color:rgba(255,255,255,0.2);text-transform:uppercase}
.sub-dot{width:3px;height:3px;border-radius:50%;background:rgba(255,255,255,0.15)}

/* ── Disclaimer ── */
.disc{
  position:absolute;bottom:28px;left:36px;
  font-size:0.54rem;color:rgba(255,255,255,0.13);
  letter-spacing:0.3px;line-height:1.9;z-index:10;
  animation:fade-up 0.8s ease 1.5s both;
}

/* ── Bottom corner decoration (right) ── */
.corner-rt{
  position:absolute;bottom:24px;right:36px;z-index:10;
  display:flex;gap:5px;
  animation:fade-up 0.8s ease 1.5s both;
}
.c-dot{width:4px;height:4px;border-radius:50%;background:rgba(255,255,255,0.1)}
.c-dot.on{background:rgba(255,255,255,0.4)}

/* ── Bottom rule ── */
.bot-rule{
  position:absolute;bottom:0;left:0;
  width:100%;height:1px;background:rgba(255,255,255,0.05);
}
</style>
</head>
<body>
<div class="stage">
  <div class="top-rule"></div>

  <div class="brand">
    <div class="b-mark">B</div>
    <div class="b-name">AI Buffett</div>
  </div>
  <div class="yr">Est. 2025</div>

  <div style="width:100%;text-align:center;">
    <div class="deco-row">
      <div class="deco-ln"></div>
      <div class="deco-lbl">Value Intelligence Platform</div>
      <div class="deco-ln"></div>
    </div>

    <div class="mq-outer">
      <div class="mq-track">
        <!-- Two identical copies → seamless -50% loop -->
        <span class="mq-item">Build wealth with AI Buffett</span><span class="mq-sep">&mdash;</span>
        <span class="mq-item">Build wealth with AI Buffett</span><span class="mq-sep">&mdash;</span>
      </div>
    </div>

    <div class="sub-row">
      <span class="sub-tag">A股</span>
      <span class="sub-dot"></span>
      <span class="sub-tag">港股</span>
      <span class="sub-dot"></span>
      <span class="sub-tag">美股</span>
      <span class="sub-dot"></span>
      <span class="sub-tag">AI Research</span>
    </div>
  </div>

  <div class="disc">
    Investing involves risks,<br>including loss of capital.
  </div>

  <div class="corner-rt">
    <div class="c-dot on"></div>
    <div class="c-dot"></div>
    <div class="c-dot"></div>
  </div>

  <div class="bot-rule"></div>
</div>
</body>
</html>
"""
    components.html(html, height=540, scrolling=False)


def _render_stats():
    """Three-column stat cards — Blackstone 'About the Firm' style."""
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@300;400&family=Inter:wght@200;300;400&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;font-family:'Inter',-apple-system,sans-serif}

.grid{
  display:flex;width:100%;height:100%;
  border-top:1px solid rgba(255,255,255,0.07);
  border-bottom:1px solid rgba(255,255,255,0.07);
}

.card{
  flex:1;padding:38px 44px 32px;
  display:flex;flex-direction:column;justify-content:space-between;
  border-right:1px solid rgba(255,255,255,0.07);
  cursor:default;position:relative;overflow:hidden;
  transition:background 0.35s ease;
}
.card:last-child{border-right:none}
.card:hover{background:rgba(255,255,255,0.018)}

/* bottom slide-in line on hover */
.card::after{
  content:'';position:absolute;bottom:0;left:0;
  width:0;height:1px;
  background:linear-gradient(90deg,rgba(255,255,255,0.5),transparent);
  transition:width 0.45s cubic-bezier(0.22,0.61,0.36,1);
}
.card:hover::after{width:100%}

.c-label{
  font-size:0.4rem;letter-spacing:5px;
  color:rgba(255,255,255,0.25);text-transform:uppercase;
  margin-bottom:14px;
}
.c-value{
  font-family:'Playfair Display',serif;
  font-size:clamp(2.2rem,4vw,3rem);font-weight:300;
  color:#fff;line-height:1;margin-bottom:14px;
}
.c-desc{
  font-size:0.68rem;font-weight:300;
  color:rgba(255,255,255,0.35);line-height:1.75;
  flex:1;
}
.c-link{
  display:flex;align-items:center;gap:8px;
  margin-top:22px;
  font-size:0.46rem;letter-spacing:3px;
  color:rgba(255,255,255,0.18);text-transform:uppercase;
  transition:color 0.3s ease;
}
.card:hover .c-link{color:rgba(255,255,255,0.55)}
.c-line{
  width:18px;height:1px;background:currentColor;
  transition:width 0.35s ease;
}
.card:hover .c-line{width:28px}
</style>
</head>
<body>
<div class="grid">

  <div class="card">
    <div>
      <div class="c-label">Market Coverage</div>
      <div class="c-value">3</div>
      <div class="c-desc">A股 &middot; 港股 &middot; 美股<br>全球主要市场实时行情追踪<br>34只精选标的持续覆盖</div>
    </div>
    <div class="c-link"><span class="c-line"></span><span>Markets</span></div>
  </div>

  <div class="card">
    <div>
      <div class="c-label">Buffett Score</div>
      <div class="c-value">100</div>
      <div class="c-desc">五维度护城河评分体系<br>盈利质量 &middot; 护城河深度<br>财务堡垒 &middot; 成长确定性</div>
    </div>
    <div class="c-link"><span class="c-line"></span><span>Scoring</span></div>
  </div>

  <div class="card">
    <div>
      <div class="c-label">AI Research</div>
      <div class="c-value">AI</div>
      <div class="c-desc">DeepSeek 驱动深度研报<br>巴菲特 &middot; 段永平 双视角<br>实时 AI 投资顾问对话</div>
    </div>
    <div class="c-link"><span class="c-line"></span><span>Research</span></div>
  </div>

</div>
</body>
</html>
"""
    components.html(html, height=210, scrolling=False)


def _render_banner():
    """Full-width dark banner with grid pattern, quote, and scan-line animation."""
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,300;1,300&family=Inter:wght@200;300&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;overflow:hidden}

.banner{
  position:relative;width:100%;height:100%;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  /* subtle grid pattern */
  background-color:#050507;
  background-image:
    linear-gradient(rgba(255,255,255,0.016) 1px,transparent 1px),
    linear-gradient(90deg,rgba(255,255,255,0.016) 1px,transparent 1px);
  background-size:68px 68px;
  overflow:hidden;
}

/* Scanning glow line */
.scan{
  position:absolute;left:0;width:100%;height:120px;
  background:linear-gradient(180deg,transparent 0%,rgba(255,255,255,0.022) 50%,transparent 100%);
  animation:scan-down 10s ease-in-out infinite;
  pointer-events:none;
}
@keyframes scan-down{
  0%  {top:-120px;opacity:0}
  8%  {opacity:1}
  92% {opacity:1}
  100%{top:100%;opacity:0}
}

/* Corner brackets */
.bracket{position:absolute;width:22px;height:22px}
.bracket::before,.bracket::after{content:'';position:absolute;background:rgba(255,255,255,0.14)}
.bracket::before{width:1px;height:100%}
.bracket::after {width:100%;height:1px}
.tl{top:20px;left:20px}
.tr{top:20px;right:20px;transform:scaleX(-1)}
.bl{bottom:20px;left:20px;transform:scaleY(-1)}
.br{bottom:20px;right:20px;transform:scale(-1,-1)}

.content{
  position:relative;z-index:2;
  text-align:center;padding:0 12%;
}

.rule{
  width:44px;height:1px;
  background:rgba(255,255,255,0.22);
  margin:0 auto;
}
.rule.top{margin-bottom:26px}
.rule.bot{margin-top:26px}

.quote{
  font-family:'Playfair Display',Georgia,serif;
  font-size:clamp(1.5rem,3.2vw,2.3rem);
  font-weight:300;color:#fff;
  letter-spacing:0.04em;line-height:1.45;
  margin-bottom:18px;
}
.quote em{font-style:italic;color:rgba(255,255,255,0.65)}

.body-text{
  font-size:0.62rem;font-weight:300;
  color:rgba(255,255,255,0.26);
  letter-spacing:1px;line-height:2;
}
</style>
</head>
<body>
<div class="banner">
  <div class="scan"></div>
  <div class="bracket tl"></div>
  <div class="bracket tr"></div>
  <div class="bracket bl"></div>
  <div class="bracket br"></div>

  <div class="content">
    <div class="rule top"></div>
    <div class="quote">Value Investing &nbsp;&middot;&nbsp; <em>Redefined by AI</em></div>
    <div class="body-text">
      基于巴菲特价值投资哲学 &nbsp;&middot;&nbsp; DeepSeek AI 驱动深度分析<br>
      实时行情 &nbsp;&middot;&nbsp; 护城河评分 &nbsp;&middot;&nbsp; 深度研报 &nbsp;&middot;&nbsp; 三大市场全覆盖
    </div>
    <div class="rule bot"></div>
  </div>
</div>
</body>
</html>
"""
    components.html(html, height=280, scrolling=False)


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
    """Blackstone-inspired login/register — auto-marquee hero + stats + banner + form."""
    _inject_page_css()
    _render_hero()
    _render_stats()
    _render_banner()

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
