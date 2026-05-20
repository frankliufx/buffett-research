"""Portfolio — Position Tracking · P&L · Allocation"""

import json
import datetime
import streamlit as st
import streamlit.components.v1 as components
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.ui_theme import get_global_css, COLORS
from src.auth import get_current_user
from src.config import load_config
from src.user_data import load_portfolio, add_position, delete_position
from src.cache_config import CACHE_TTL

if "config" not in st.session_state:
    st.session_state.config = load_config()

user = get_current_user()
_uid = (user or {}).get("username", "anonymous")

st.markdown(get_global_css(), unsafe_allow_html=True)


def _detect_market(symbol: str) -> str:
    s = symbol.lower()
    if s.startswith("sh") or s.startswith("sz"):
        return "a_share"
    if s.endswith(".hk"):
        return "hk"
    return "us"


def _currency(market: str) -> str:
    return {"us": "$", "hk": "HK$", "a_share": "¥"}.get(market, "$")


# ── Header ────────────────────────────────────────────────────────────────────
components.html("""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:24px 0 8px}
.title{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.8rem;font-weight:300;color:#E8E8F0;letter-spacing:3px;text-transform:uppercase}
.title b{font-weight:700;color:#C9A962}
.sub{font-size:0.55rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-top:6px}
.divider{height:1px;background:linear-gradient(90deg,transparent,#C9A962 30%,transparent);margin-top:16px;opacity:0.3}
</style></head><body>
<div class="title">My <b>Portfolio</b></div>
<div class="sub">Position Tracking &middot; Profit & Loss &middot; Allocation</div>
<div class="divider"></div>
</body></html>
""", height=90, scrolling=False)


# ── Load positions + live prices ──────────────────────────────────────────────
if "portfolio_loaded" not in st.session_state or st.session_state.get("_port_uid") != _uid:
    st.session_state.portfolio = load_portfolio(_uid)
    st.session_state.portfolio_loaded = True
    st.session_state._port_uid = _uid

positions = st.session_state.portfolio


@st.cache_data(ttl=CACHE_TTL["quote"], show_spinner=False)
def _fetch_live_prices(symbols_json: str) -> dict:
    """批量获取实时价格"""
    from src.data.price import fetch_quote
    items = json.loads(symbols_json)
    results = {}
    cfg = st.session_state.get("config") or load_config()

    def _fetch_one(item):
        try:
            q = fetch_quote(item["symbol"], item["market"])
            return item["symbol"], q
        except Exception:
            return item["symbol"], {}

    with ThreadPoolExecutor(max_workers=cfg.parallel.portfolio_workers) as executor:
        futures = [executor.submit(_fetch_one, it) for it in items]
        for f in as_completed(futures):
            sym, q = f.result()
            results[sym] = q
    return results


# ── Add Position Form ─────────────────────────────────────────────────────────
with st.expander("Add Position", expanded=len(positions) == 0):
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        p_symbol = st.text_input("Symbol", placeholder="e.g. AAPL", key="p_sym")
    with ac2:
        p_shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0, key="p_shares")
    with ac3:
        p_cost = st.number_input("Cost Price", min_value=0.0, value=0.0, step=0.01, key="p_cost")

    ac4, ac5 = st.columns(2)
    with ac4:
        p_name = st.text_input("Name (optional)", placeholder="e.g. Apple Inc", key="p_name")
    with ac5:
        p_date = st.date_input("Buy Date", value=datetime.date.today(), key="p_date")

    p_note = st.text_input("Note (optional)", placeholder="e.g. Q4 earnings play", key="p_note")

    if st.button("Add to Portfolio", key="p_add", use_container_width=True):
        sym = p_symbol.strip().upper()
        if sym and p_shares > 0 and p_cost > 0:
            mkt = _detect_market(sym)
            pos = {
                "symbol": sym,
                "name": p_name.strip() or sym,
                "market": mkt,
                "shares": float(p_shares),
                "cost_price": float(p_cost),
                "buy_date": str(p_date),
                "note": p_note.strip(),
            }
            add_position(_uid, pos)
            st.session_state.portfolio.insert(0, pos)
            st.rerun()
        else:
            st.warning("Please fill in Symbol, Shares, and Cost Price.")


# ── Portfolio Dashboard ───────────────────────────────────────────────────────
if not positions:
    components.html('''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:40px 0;text-align:center}
.empty-icon{font-size:2.5rem;margin-bottom:12px;opacity:0.3}
.empty-title{font-family:'Cormorant Garamond',serif;font-size:1.3rem;color:#5A5A6A;margin-bottom:6px}
.empty-desc{font-size:0.7rem;color:#3A3A4A;letter-spacing:0.5px}
</style></head><body>
<div class="empty-icon">&#x1F4BC;</div>
<div class="empty-title">No Positions Yet</div>
<div class="empty-desc">Add your first position above to start tracking</div>
</body></html>''', height=150, scrolling=False)
    st.stop()

# Fetch live prices
unique_stocks = {}
for p in positions:
    sym = p.get("symbol", "")
    if sym and sym not in unique_stocks:
        unique_stocks[sym] = {"symbol": sym, "market": p.get("market", "us")}

with st.spinner("Loading live prices..."):
    live_prices = _fetch_live_prices(json.dumps(list(unique_stocks.values())))

# Calculate P&L for each position
enriched = []
total_cost = 0
total_value = 0
total_pnl = 0

for p in positions:
    sym = p.get("symbol", "")
    shares = float(p.get("shares", 0))
    cost_price = float(p.get("cost_price", 0))
    mkt = p.get("market", "us")

    quote = live_prices.get(sym, {})
    current_price = quote.get("price", 0)
    change_pct = quote.get("change_pct", 0)

    cost_total = shares * cost_price
    market_value = shares * current_price if current_price else 0
    pnl = market_value - cost_total
    pnl_pct = (pnl / cost_total * 100) if cost_total > 0 else 0

    total_cost += cost_total
    total_value += market_value
    total_pnl += pnl

    enriched.append({
        **p,
        "current_price": current_price,
        "change_pct": change_pct,
        "cost_total": cost_total,
        "market_value": market_value,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
    })

total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

# ── Summary Cards ─────────────────────────────────────────────────────────────
pnl_color = "#00C853" if total_pnl >= 0 else "#F44336"
pnl_arrow = "&#x25B2;" if total_pnl >= 0 else "&#x25BC;"

def _fmt_money(val):
    if abs(val) >= 1e6:
        return "{:,.0f}".format(val)
    return "{:,.2f}".format(val)

components.html('''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:16px 0}}
.summary-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.s-card{{background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:18px 20px}}
.s-label{{font-size:0.5rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:8px}}
.s-value{{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.6rem;font-weight:700;color:#E8E8F0;line-height:1}}
.s-value.pnl{{color:{pnl_color}}}
.s-sub{{font-size:0.6rem;color:#5A5A6A;margin-top:4px;letter-spacing:0.5px}}
</style></head><body>
<div class="summary-grid">
    <div class="s-card">
        <div class="s-label">Total Value</div>
        <div class="s-value">${value}</div>
        <div class="s-sub">{count} positions</div>
    </div>
    <div class="s-card">
        <div class="s-label">Total Cost</div>
        <div class="s-value">${cost}</div>
    </div>
    <div class="s-card">
        <div class="s-label">Total P&amp;L</div>
        <div class="s-value pnl">{arrow} ${pnl}</div>
        <div class="s-sub" style="color:{pnl_color}">{pnl_pct:+.2f}%</div>
    </div>
    <div class="s-card">
        <div class="s-label">Today</div>
        <div class="s-value pnl">{today_arrow} ${today_pnl}</div>
    </div>
</div>
</body></html>'''.format(
    pnl_color=pnl_color,
    value=_fmt_money(total_value),
    cost=_fmt_money(total_cost),
    count=len(positions),
    arrow=pnl_arrow,
    pnl=_fmt_money(abs(total_pnl)),
    pnl_pct=total_pnl_pct,
    today_arrow="&#x25B2;" if sum(e["change_pct"] for e in enriched) >= 0 else "&#x25BC;",
    today_pnl=_fmt_money(abs(sum(e["market_value"] * e["change_pct"] / 100 for e in enriched if e["market_value"]))),
), height=120, scrolling=False)


# ── Allocation Pie + Positions Table ──────────────────────────────────────────
col_chart, col_table = st.columns([1, 2])

with col_chart:
    st.markdown('<div style="font-size:0.5rem;letter-spacing:4px;color:#C9A962;text-transform:uppercase;margin-bottom:8px">ALLOCATION</div>',
                unsafe_allow_html=True)
    if total_value > 0:
        import plotly.graph_objects as go
        labels = [e["symbol"] for e in enriched if e["market_value"] > 0]
        values = [e["market_value"] for e in enriched if e["market_value"] > 0]
        colors = ["#C9A962", "#69F0AE", "#00C853", "#FF9800", "#F44336",
                  "#5A5A6A", "#8888A0", "#AAAABC", "#3A3A4A", "#1E1E2A"]
        fig = go.Figure(data=[go.Pie(
            labels=labels, values=values,
            hole=0.55, textinfo="label+percent",
            textfont=dict(size=11, color="#E8E8F0"),
            marker=dict(colors=colors[:len(labels)], line=dict(color="#08080C", width=2)),
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
        )])
        fig.update_layout(
            showlegend=False, height=280, margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="#08080C", plot_bgcolor="#08080C",
            font=dict(color="#E8E8F0"),
            annotations=[dict(text="<b>${:,.0f}</b>".format(total_value),
                             x=0.5, y=0.5, font_size=16, font_color="#C9A962",
                             showarrow=False)],
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No market value data available.")

with col_table:
    st.markdown('<div style="font-size:0.5rem;letter-spacing:4px;color:#C9A962;text-transform:uppercase;margin-bottom:8px">POSITIONS</div>',
                unsafe_allow_html=True)

    # Sort by market value descending
    enriched.sort(key=lambda x: x.get("market_value", 0), reverse=True)

    rows_html = ""
    for e in enriched:
        pnl = e["pnl"]
        pnl_pct = e["pnl_pct"]
        pc = "#00C853" if pnl >= 0 else "#F44336"
        cur = _currency(e.get("market", "us"))
        cp = e["current_price"]
        cp_fmt = "{}{:,.2f}".format(cur, cp) if cp else "--"
        cost_fmt = "{}{:,.2f}".format(cur, e["cost_price"])
        pnl_fmt = "{:+,.0f}".format(pnl) if abs(pnl) >= 100 else "{:+,.2f}".format(pnl)
        alloc = (e["market_value"] / total_value * 100) if total_value > 0 else 0

        rows_html += '''<tr>
            <td class="sym">{sym}</td>
            <td>{shares:.0f}</td>
            <td>{cost}</td>
            <td>{price}</td>
            <td style="color:{pc}">{pnl} ({pnl_pct:+.1f}%)</td>
            <td>{alloc:.1f}%</td>
        </tr>'''.format(
            sym=e["symbol"], shares=e["shares"], cost=cost_fmt,
            price=cp_fmt, pc=pc, pnl=pnl_fmt, pnl_pct=pnl_pct, alloc=alloc,
        )

    components.html('''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:0}}
table{{width:100%;border-collapse:collapse}}
th{{font-size:0.5rem;letter-spacing:2px;color:#5A5A6A;text-transform:uppercase;text-align:left;padding:6px 8px;border-bottom:1px solid #1A1A22;font-weight:500}}
th:nth-child(n+2){{text-align:right}}
td{{padding:8px 8px;border-bottom:1px solid #0F0F18;font-size:0.7rem;color:#AAAABC}}
td:nth-child(n+2){{text-align:right}}
tr:hover{{background:#0F0F18}}
.sym{{color:#C9A962;font-weight:600;letter-spacing:1px}}
</style></head><body>
<table>
<tr><th>Symbol</th><th>Shares</th><th>Cost</th><th>Price</th><th>P&L</th><th>Alloc</th></tr>
{rows}
</table>
</body></html>'''.format(rows=rows_html), height=max(60, len(enriched) * 36 + 36), scrolling=False)


# ── Delete Position ───────────────────────────────────────────────────────────
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
with st.expander("Manage Positions", expanded=False):
    del_options = ["{} — {} shares @ {}".format(
        p.get("symbol", "?"), p.get("shares", 0), p.get("cost_price", 0))
        for p in positions]
    del_idx = st.selectbox("Select position to remove", range(len(del_options)),
                            format_func=lambda i: del_options[i], key="del_pos")
    if st.button("Remove Position", key="del_pos_btn"):
        pos = positions[del_idx]
        pid = pos.get("id", "")
        if pid:
            delete_position(_uid, pid)
        st.session_state.portfolio.pop(del_idx)
        st.rerun()
