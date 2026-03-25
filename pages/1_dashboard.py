"""Personal Dashboard — Watchlist · Investment Journal · Market Compass"""

import datetime
import streamlit as st
import streamlit.components.v1 as components
from src.ui_theme import get_global_css, COLORS
from src.auth import get_current_user
from src.journal import load_journal, save_journal, export_json, import_json

# ── Session defaults ──────────────────────────────────────────────────────────
if "config" not in st.session_state:
    from src.config import load_config
    st.session_state.config = load_config()

if "dashboard_watchlist" not in st.session_state:
    st.session_state.dashboard_watchlist = ["BRK.B", "AAPL", "KO", "BAC", "OXY"]

# Load journal from disk on first visit (not on every rerun)
if "journal_loaded" not in st.session_state:
    st.session_state.journal_entries = load_journal()
    st.session_state.journal_loaded = True
elif "journal_entries" not in st.session_state:
    st.session_state.journal_entries = []

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(get_global_css(), unsafe_allow_html=True)

# ── Page header ───────────────────────────────────────────────────────────────
user = get_current_user()
display_name = user.get("name", "Investor") if user else "Investor"

components.html(f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    background: #08080C;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    padding: 28px 0 8px;
}}
.greeting {{ font-size:0.55rem; letter-spacing:4px; color:#C9A962;
    text-transform:uppercase; margin-bottom:6px; }}
.title {{ font-size:1.6rem; font-weight:300; color:#E8E8F0; letter-spacing:3px;
    text-transform:uppercase; }}
.title b {{ font-weight:700; color:#C9A962; }}
.subtitle {{ font-size:0.6rem; letter-spacing:3px; color:#3A3A4A;
    text-transform:uppercase; margin-top:6px; }}
.divider {{ height:1px; background:linear-gradient(90deg,transparent,#C9A962 30%,transparent);
    margin-top:18px; opacity:0.3; }}
</style></head><body>
<div class="greeting">Welcome back, {display_name}</div>
<div class="title">Personal <b>Dashboard</b></div>
<div class="subtitle">Watchlist &nbsp;&middot;&nbsp; Investment Journal &nbsp;&middot;&nbsp; Market Compass</div>
<div class="divider"></div>
</body></html>
""", height=110, scrolling=False)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
components.html("""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#08080C; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; padding:8px 0 4px; }}
.section-label {{ font-size:0.5rem; letter-spacing:4px; color:#C9A962; text-transform:uppercase; }}
.section-title {{ font-size:1.05rem; font-weight:600; color:#E8E8F0; letter-spacing:1px; margin-top:2px; }}
</style></head><body>
<div class="section-label">Portfolio Intelligence</div>
<div class="section-title">My Watchlist</div>
</body></html>
""", height=52, scrolling=False)

# Watchlist management
wl_col1, wl_col2 = st.columns([3, 1])
with wl_col1:
    new_ticker = st.text_input(
        "Add ticker", placeholder="e.g. MSFT or 600519.SH",
        key="wl_new_ticker", label_visibility="collapsed"
    )
with wl_col2:
    if st.button("＋ Add", key="wl_add_btn", use_container_width=True):
        t = new_ticker.strip().upper()
        if t and t not in st.session_state.dashboard_watchlist:
            st.session_state.dashboard_watchlist.append(t)
            st.rerun()

# Display watchlist chips + remove buttons
watchlist = st.session_state.dashboard_watchlist
if watchlist:
    # Render chips via components.html
    chips_html = " ".join(
        f'<span class="chip">{t}</span>'
        for t in watchlist
    )
    components.html(f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#08080C; font-family:-apple-system,BlinkMacSystemFont,sans-serif; padding:6px 0; display:flex; flex-wrap:wrap; gap:8px; }}
.chip {{
    display:inline-block; padding:5px 14px;
    border:1px solid #C9A962; border-radius:2px;
    color:#C9A962; font-size:0.75rem; font-weight:600;
    letter-spacing:2px; background:#0F0F16;
}}
</style></head><body>{chips_html}</body></html>
""", height=48, scrolling=False)

    # Remove selector
    remove_ticker = st.selectbox(
        "Remove ticker", options=["— select to remove —"] + watchlist,
        key="wl_remove_sel", label_visibility="collapsed"
    )
    if remove_ticker and remove_ticker != "— select to remove —":
        if st.button(f"✕ Remove {remove_ticker}", key="wl_remove_btn"):
            st.session_state.dashboard_watchlist.remove(remove_ticker)
            st.rerun()

    # Quick snapshot via Analysis
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if st.button("⚡ Quick Scan Watchlist", key="wl_scan_btn", use_container_width=False):
        from src.data.financial import get_stock_score
        results = []
        progress = st.progress(0, text="Scanning…")
        for i, ticker in enumerate(watchlist):
            try:
                score_data = get_stock_score(ticker)
                results.append((ticker, score_data))
            except Exception:
                results.append((ticker, None))
            progress.progress((i + 1) / len(watchlist), text=f"Scanned {ticker}")
        progress.empty()

        cols = st.columns(min(len(results), 5))
        grade_color = {"A+": "#00C853", "A": "#69F0AE", "B": "#C9A962",
                       "C": "#FF9800", "D": "#F44336", "F": "#B71C1C"}
        for col, (ticker, sd) in zip(cols, results):
            with col:
                if sd:
                    grade = sd.get("grade", "—")
                    score = sd.get("score", 0)
                    color = grade_color.get(grade, "#E8E8F0")
                    st.markdown(
                        f"""<div style='background:#0F0F16;border:1px solid #1E1E26;
                        border-radius:2px;padding:12px;text-align:center;'>
                        <div style='font-size:1.5rem;font-weight:700;color:{color}'>{grade}</div>
                        <div style='font-size:0.65rem;color:#5A5A6A;letter-spacing:2px;
                        text-transform:uppercase;margin:2px 0'>{ticker}</div>
                        <div style='font-size:0.8rem;color:#E8E8F0'>{score:.1f}</div>
                        </div>""",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""<div style='background:#0F0F16;border:1px solid #1E1E26;
                        border-radius:2px;padding:12px;text-align:center;'>
                        <div style='font-size:1rem;color:#3A3A4A'>—</div>
                        <div style='font-size:0.65rem;color:#5A5A6A;letter-spacing:2px;
                        text-transform:uppercase;margin:2px 0'>{ticker}</div>
                        </div>""",
                        unsafe_allow_html=True
                    )
else:
    st.markdown(
        "<div style='color:#3A3A4A;font-size:0.8rem;padding:8px 0'>No tickers yet. Add some above.</div>",
        unsafe_allow_html=True
    )

st.markdown("<div style='height:24px;border-top:1px solid #1A1A22;margin-top:20px'></div>",
            unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — INVESTMENT JOURNAL
# ══════════════════════════════════════════════════════════════════════════════
components.html("""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#08080C; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; padding:8px 0 4px; }
.section-label { font-size:0.5rem; letter-spacing:4px; color:#C9A962; text-transform:uppercase; }
.section-title { font-size:1.05rem; font-weight:600; color:#E8E8F0; letter-spacing:1px; margin-top:2px; }
</style></head><body>
<div class="section-label">Reflective Practice</div>
<div class="section-title">Investment Journal</div>
</body></html>
""", height=52, scrolling=False)

journal_tab1, journal_tab2, journal_tab3 = st.tabs([
    "📋  Decision Log",
    "🔍  Trade Review",
    "🌐  Market Notes",
])

# ── Tab 1: Decision Log ──────────────────────────────────────────────────────
with journal_tab1:
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    with st.expander("＋ New Decision Entry", expanded=False):
        d_date = st.date_input("Date", value=datetime.date.today(), key="d_date")
        d_ticker = st.text_input("Ticker / Asset", placeholder="e.g. BRK.B", key="d_ticker")
        d_action = st.selectbox("Action", ["Buy", "Sell", "Hold", "Watch", "Research"], key="d_action")
        d_thesis = st.text_area(
            "Investment Thesis",
            placeholder="Why are you making this decision? Key valuation drivers, catalysts, risks…",
            height=100, key="d_thesis"
        )
        d_conviction = st.slider("Conviction Level", 1, 10, 7, key="d_conviction")
        if st.button("Save Decision", key="d_save"):
            if d_ticker.strip():
                entry = {
                    "type": "decision",
                    "date": str(d_date),
                    "ticker": d_ticker.strip().upper(),
                    "action": d_action,
                    "thesis": d_thesis,
                    "conviction": d_conviction,
                }
                st.session_state.journal_entries.insert(0, entry)
                save_journal(st.session_state.journal_entries)
                st.success("Decision saved.")
                st.rerun()

    decisions = [e for e in st.session_state.journal_entries if e.get("type") == "decision"]
    if decisions:
        for e in decisions:
            conviction_bar = "█" * e["conviction"] + "░" * (10 - e["conviction"])
            st.markdown(
                f"""<div style='background:#0D0D12;border:1px solid #1E1E26;border-radius:2px;
                padding:14px 16px;margin-bottom:8px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>
                    <span style='font-size:0.85rem;font-weight:600;color:#C9A962'>{e["ticker"]}</span>
                    <span style='font-size:0.6rem;color:#3A3A4A;letter-spacing:2px'>{e["date"]} &nbsp;·&nbsp; {e["action"].upper()}</span>
                </div>
                <div style='font-size:0.8rem;color:#AAAABC;line-height:1.5;margin-bottom:8px'>{e["thesis"] or "—"}</div>
                <div style='font-size:0.6rem;color:#5A5A6A;letter-spacing:1px'>
                    CONVICTION &nbsp;<span style='color:#C9A962;font-family:monospace'>{conviction_bar}</span>&nbsp; {e["conviction"]}/10
                </div>
                </div>""",
                unsafe_allow_html=True
            )
    else:
        st.markdown("<div style='color:#3A3A4A;font-size:0.8rem;padding:8px 0'>No decisions logged yet.</div>",
                    unsafe_allow_html=True)

# ── Tab 2: Trade Review ──────────────────────────────────────────────────────
with journal_tab2:
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    with st.expander("＋ New Trade Review", expanded=False):
        r_date = st.date_input("Review Date", value=datetime.date.today(), key="r_date")
        r_ticker = st.text_input("Ticker", placeholder="e.g. KO", key="r_ticker")
        r_outcome = st.selectbox("Outcome", ["Profit", "Loss", "Break-even", "Ongoing"], key="r_outcome")
        r_what_worked = st.text_area(
            "What Worked",
            placeholder="Entry timing, valuation model accuracy, patience…",
            height=80, key="r_what_worked"
        )
        r_mistakes = st.text_area(
            "Mistakes / What to Improve",
            placeholder="Emotional bias, missed signals, position sizing…",
            height=80, key="r_mistakes"
        )
        r_lesson = st.text_area(
            "Key Lesson",
            placeholder="One clear rule or principle to carry forward…",
            height=60, key="r_lesson"
        )
        if st.button("Save Review", key="r_save"):
            if r_ticker.strip():
                entry = {
                    "type": "review",
                    "date": str(r_date),
                    "ticker": r_ticker.strip().upper(),
                    "outcome": r_outcome,
                    "what_worked": r_what_worked,
                    "mistakes": r_mistakes,
                    "lesson": r_lesson,
                }
                st.session_state.journal_entries.insert(0, entry)
                save_journal(st.session_state.journal_entries)
                st.success("Review saved.")
                st.rerun()

    reviews = [e for e in st.session_state.journal_entries if e.get("type") == "review"]
    outcome_color = {"Profit": "#00C853", "Loss": "#F44336",
                     "Break-even": "#FF9800", "Ongoing": "#C9A962"}
    if reviews:
        for e in reviews:
            oc = outcome_color.get(e["outcome"], "#E8E8F0")
            st.markdown(
                f"""<div style='background:#0D0D12;border:1px solid #1E1E26;border-radius:2px;
                padding:14px 16px;margin-bottom:8px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>
                    <span style='font-size:0.85rem;font-weight:600;color:#C9A962'>{e["ticker"]}</span>
                    <span style='font-size:0.7rem;font-weight:700;color:{oc}'>{e["outcome"].upper()}</span>
                    <span style='font-size:0.6rem;color:#3A3A4A;letter-spacing:2px'>{e["date"]}</span>
                </div>
                {"<div style='font-size:0.75rem;color:#5A5A6A;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px'>What Worked</div><div style='font-size:0.8rem;color:#AAAABC;line-height:1.5;margin-bottom:8px'>" + (e["what_worked"] or "—") + "</div>" if e.get("what_worked") else ""}
                {"<div style='font-size:0.75rem;color:#5A5A6A;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px'>Mistakes</div><div style='font-size:0.8rem;color:#AAAABC;line-height:1.5;margin-bottom:8px'>" + (e["mistakes"] or "—") + "</div>" if e.get("mistakes") else ""}
                {"<div style='font-size:0.75rem;color:#C9A962;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px'>Key Lesson</div><div style='font-size:0.8rem;color:#E8E8F0;line-height:1.5;font-style:italic'>" + (e["lesson"] or "—") + "</div>" if e.get("lesson") else ""}
                </div>""",
                unsafe_allow_html=True
            )
    else:
        st.markdown("<div style='color:#3A3A4A;font-size:0.8rem;padding:8px 0'>No reviews yet.</div>",
                    unsafe_allow_html=True)

# ── Tab 3: Market Notes ──────────────────────────────────────────────────────
with journal_tab3:
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    with st.expander("＋ New Market Note", expanded=False):
        n_date = st.date_input("Date", value=datetime.date.today(), key="n_date")
        n_category = st.selectbox(
            "Category",
            ["Macro / Economy", "Industry Trend", "New Observation", "Risk Watch", "Other"],
            key="n_category"
        )
        n_title = st.text_input("Title / Headline", placeholder="Brief description", key="n_title")
        n_body = st.text_area(
            "Analysis",
            placeholder="What does this signal? How does it affect portfolio thesis?",
            height=100, key="n_body"
        )
        n_impact = st.selectbox("Portfolio Impact", ["Positive", "Negative", "Neutral", "Monitoring"], key="n_impact")
        if st.button("Save Note", key="n_save"):
            if n_title.strip():
                entry = {
                    "type": "note",
                    "date": str(n_date),
                    "category": n_category,
                    "title": n_title.strip(),
                    "body": n_body,
                    "impact": n_impact,
                }
                st.session_state.journal_entries.insert(0, entry)
                save_journal(st.session_state.journal_entries)
                st.success("Note saved.")
                st.rerun()

    notes = [e for e in st.session_state.journal_entries if e.get("type") == "note"]
    impact_color = {"Positive": "#00C853", "Negative": "#F44336",
                    "Neutral": "#5A5A6A", "Monitoring": "#FF9800"}
    cat_icon = {
        "Macro / Economy": "🌍",
        "Industry Trend": "📈",
        "New Observation": "🔭",
        "Risk Watch": "⚠️",
        "Other": "📝",
    }
    if notes:
        for e in notes:
            ic = impact_color.get(e["impact"], "#E8E8F0")
            icon = cat_icon.get(e["category"], "📝")
            st.markdown(
                f"""<div style='background:#0D0D12;border:1px solid #1E1E26;border-radius:2px;
                padding:14px 16px;margin-bottom:8px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>
                    <span style='font-size:0.8rem;font-weight:600;color:#E8E8F0'>{icon}&nbsp; {e["title"]}</span>
                    <span style='font-size:0.65rem;font-weight:600;color:{ic};letter-spacing:1px'>{e["impact"].upper()}</span>
                </div>
                <div style='font-size:0.6rem;color:#3A3A4A;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px'>{e["date"]} &nbsp;·&nbsp; {e["category"]}</div>
                <div style='font-size:0.8rem;color:#AAAABC;line-height:1.5'>{e["body"] or "—"}</div>
                </div>""",
                unsafe_allow_html=True
            )
    else:
        st.markdown("<div style='color:#3A3A4A;font-size:0.8rem;padding:8px 0'>No market notes yet.</div>",
                    unsafe_allow_html=True)

st.markdown("<div style='height:24px;border-top:1px solid #1A1A22;margin-top:20px'></div>",
            unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — MARKET COMPASS
# ══════════════════════════════════════════════════════════════════════════════
components.html("""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#08080C; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; padding:8px 0 4px; }
.section-label { font-size:0.5rem; letter-spacing:4px; color:#C9A962; text-transform:uppercase; }
.section-title { font-size:1.05rem; font-weight:600; color:#E8E8F0; letter-spacing:1px; margin-top:2px; }
</style></head><body>
<div class="section-label">Macro Intelligence</div>
<div class="section-title">Market Compass</div>
</body></html>
""", height=52, scrolling=False)

if st.button("🌐 Refresh Macro Data", key="compass_refresh"):
    st.cache_data.clear()

@st.cache_data(ttl=3600)
def _load_macro():
    try:
        from src.data.macro import get_macro_overview
        return get_macro_overview()
    except Exception as e:
        return {"error": str(e)}

with st.spinner("Loading macro indicators…"):
    macro = _load_macro()

if "error" in macro:
    st.warning(f"Macro data unavailable: {macro['error']}")
else:
    # Layout: two columns
    mc1, mc2 = st.columns(2)

    def _compass_metric(label, value, delta=None, delta_good=True):
        if delta is not None:
            arrow = "▲" if delta >= 0 else "▼"
            d_color = "#00C853" if (delta >= 0) == delta_good else "#F44336"
            delta_html = f"<span style='font-size:0.7rem;color:{d_color}'>{arrow} {abs(delta):.2f}%</span>"
        else:
            delta_html = ""
        return f"""<div style='background:#0D0D12;border:1px solid #1E1E26;border-radius:2px;
            padding:14px 16px;margin-bottom:8px;'>
            <div style='font-size:0.55rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:4px'>{label}</div>
            <div style='font-size:1.2rem;font-weight:600;color:#E8E8F0'>{value} &nbsp;{delta_html}</div>
            </div>"""

    # Gather keys from macro dict (structure depends on macro.py implementation)
    buffett_pct = macro.get("buffett_indicator_pct") or macro.get("buffett_pct")
    sp500 = macro.get("sp500") or macro.get("sp500_price")
    pe_ratio = macro.get("sp500_pe") or macro.get("pe_ratio")
    vix = macro.get("vix") or macro.get("vix_current")
    dxy = macro.get("dxy") or macro.get("usd_index")
    cn_gdp = macro.get("cn_gdp_growth") or macro.get("china_gdp")
    us_yield = macro.get("us_10y_yield") or macro.get("treasury_10y")
    cn_yield = macro.get("cn_10y_yield")

    with mc1:
        if buffett_pct is not None:
            st.markdown(_compass_metric("Buffett Indicator", f"{buffett_pct:.1f}%"), unsafe_allow_html=True)
        if sp500 is not None:
            st.markdown(_compass_metric("S&P 500", f"{sp500:,.0f}"), unsafe_allow_html=True)
        if pe_ratio is not None:
            st.markdown(_compass_metric("S&P 500 P/E", f"{pe_ratio:.1f}x"), unsafe_allow_html=True)
        if us_yield is not None:
            st.markdown(_compass_metric("US 10Y Treasury", f"{us_yield:.2f}%"), unsafe_allow_html=True)

    with mc2:
        if vix is not None:
            st.markdown(_compass_metric("VIX (Fear Index)", f"{vix:.1f}"), unsafe_allow_html=True)
        if dxy is not None:
            st.markdown(_compass_metric("DXY (USD Index)", f"{dxy:.1f}"), unsafe_allow_html=True)
        if cn_yield is not None:
            st.markdown(_compass_metric("CN 10Y Treasury", f"{cn_yield:.2f}%"), unsafe_allow_html=True)
        if cn_gdp is not None:
            st.markdown(_compass_metric("China GDP Growth", f"{cn_gdp:.1f}%"), unsafe_allow_html=True)

    # If nothing rendered, show raw dict
    key_fields = [buffett_pct, sp500, pe_ratio, vix, dxy, us_yield, cn_yield, cn_gdp]
    if not any(v is not None for v in key_fields):
        st.json(macro)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:24px;border-top:1px solid #1A1A22;margin-top:20px'></div>",
            unsafe_allow_html=True)

# ── Journal export / import ───────────────────────────────────────────────────
components.html("""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#08080C; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; padding:8px 0 4px; }
.section-label { font-size:0.5rem; letter-spacing:4px; color:#C9A962; text-transform:uppercase; }
.section-title { font-size:1.05rem; font-weight:600; color:#E8E8F0; letter-spacing:1px; margin-top:2px; }
</style></head><body>
<div class="section-label">Data Management</div>
<div class="section-title">Journal Backup</div>
</body></html>
""", height=52, scrolling=False)

ex_col, im_col, cl_col = st.columns(3)

with ex_col:
    entries = st.session_state.journal_entries
    if entries:
        st.download_button(
            label="⬇ Export Journal (JSON)",
            data=export_json(entries),
            file_name=f"journal_{datetime.date.today()}.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.button("⬇ Export (empty)", disabled=True, use_container_width=True)

with im_col:
    uploaded = st.file_uploader("⬆ Import Journal", type=["json"], key="journal_import",
                                label_visibility="collapsed")
    if uploaded is not None:
        try:
            imported = import_json(uploaded.read().decode("utf-8"))
            st.session_state.journal_entries = imported
            save_journal(imported)
            st.success(f"Imported {len(imported)} entries.")
            st.rerun()
        except Exception as e:
            st.error(f"Import failed: {e}")

with cl_col:
    if st.button("🗑 Clear All Entries", use_container_width=True):
        if st.session_state.get("confirm_clear_journal"):
            st.session_state.journal_entries = []
            save_journal([])
            st.session_state.confirm_clear_journal = False
            st.rerun()
        else:
            st.session_state.confirm_clear_journal = True
            st.warning("Click again to confirm deletion.")

st.caption(f"Journal auto-saved · {len(st.session_state.journal_entries)} entries stored")
