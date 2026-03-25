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

# Init
from src.config import load_config

if "config" not in st.session_state:
    st.session_state.config = load_config()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Navigation
pg = st.navigation([
    st.Page("pages/0_home.py", title="Home", icon="◈", default=True),
    st.Page("pages/1_sentiment.py", title="Sentiment", icon="◉"),
    st.Page("pages/2_analysis.py", title="Analysis", icon="◆"),
    st.Page("pages/3_chat.py", title="AI Advisor", icon="◇"),
    st.Page("pages/4_settings.py", title="Settings", icon="○"),
])

pg.run()
