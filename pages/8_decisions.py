"""组合决策摘要 — 一站式查看 watchlist 所有股票的最新 AI 决策。

核心价值：用户打开就看到"今天该关注哪几只"，不用逐只点开 hedgefund 页。
数据源：本地 PostgreSQL hedge_fund_decisions 表（DB_FIRST_ENABLED 开启时落库）。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import streamlit as st

from src.ui_theme import get_global_css, COLORS
from src.auth import get_current_user
from src.user_data import load_watchlist

logger = logging.getLogger(__name__)

st.set_page_config(page_title="组合决策摘要", layout="wide")
st.markdown(get_global_css(), unsafe_allow_html=True)

# ── DB 可用性检查 ─────────────────────────────────────────────────────────────
try:
    from src.db.session import db_available
    from src.db.decisions import get_latest_for_watchlist
    DB_OK = db_available()
except Exception as e:
    logger.warning("DB not available: %s", e)
    DB_OK = False
    get_latest_for_watchlist = None

if not DB_OK:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0a0d14 0%,#141822 100%);
         border:1px solid rgba(245,166,35,0.3);border-radius:6px;padding:32px;
         margin:40px auto;max-width:680px;text-align:center">
        <div style="font-size:0.42rem;letter-spacing:5px;color:rgba(201,169,98,0.5);
             text-transform:uppercase;margin-bottom:12px">portfolio decision summary</div>
        <div style="font-size:1.5rem;font-weight:700;color:#F5A623;margin-bottom:14px">
            数据库未连接</div>
        <div style="font-size:0.95rem;color:#a8a39a;line-height:1.7">
            组合决策摘要依赖本地 PostgreSQL 的决策日志。<br>
            请先在 .env 中设置 <code style="color:#C9A962">DB_FIRST_ENABLED=true</code>
            并确保 SSH tunnel 已启动。<br><br>
            云端 Streamlit 默认未配置数据库，无法使用此功能。
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── 加载 watchlist ───────────────────────────────────────────────────────────
user = get_current_user()
uid = (user or {}).get("username", "anonymous")

raw_wl = load_watchlist(uid)
# Fallback to config.yaml watchlist when user's is empty (mirrors dashboard pattern)
if not any(raw_wl.values()):
    if "config" not in st.session_state:
        from src.config import load_config
        st.session_state.config = load_config()
    config_wl = st.session_state.config.watchlist
    raw_wl = {
        "us": [{"symbol": s.symbol, "name": s.name} for s in config_wl.us],
        "hk": [{"symbol": s.symbol, "name": s.name} for s in config_wl.hk],
        "a_share": [{"symbol": s.symbol, "name": s.name} for s in config_wl.a_share],
    }

all_stocks = []
for market in ("us", "hk", "a_share"):
    for item in raw_wl.get(market, []):
        all_stocks.append({
            "symbol": item["symbol"],
            "name": item.get("name", item["symbol"]),
            "market": market,
        })

if not all_stocks:
    st.markdown("""
    <div style="text-align:center;padding:60px;color:#888">
        <div style="font-size:1.2rem;color:#C9A962;margin-bottom:8px">暂无关注股票</div>
        <div style="font-size:0.9rem">前往 Dashboard 添加自选股</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── 批量读取最新决策 ─────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _load_summary(stocks_tuple: tuple) -> dict:
    """tuple → dict: 用 tuple 让 cache 可哈希。"""
    stocks = [{"symbol": s, "market": m, "name": n} for s, m, n in stocks_tuple]
    return get_latest_for_watchlist(stocks) or {}


stocks_key = tuple((s["symbol"], s["market"], s["name"]) for s in all_stocks)
latest = _load_summary(stocks_key)

# 构造完整列表（含未分析的）
rows = []
for st_item in all_stocks:
    sym, mk = st_item["symbol"], st_item["market"]
    decision = latest.get((sym, mk))
    rows.append({**st_item, "decision": decision})


# ── 顶部摘要 ────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin:20px 0 30px">
    <div style="font-size:0.42rem;letter-spacing:6px;color:rgba(201,169,98,0.6);
         text-transform:uppercase;margin-bottom:6px">portfolio · decision summary</div>
    <div style="font-size:2.2rem;font-weight:300;color:#fff;letter-spacing:-0.5px">
        组合决策摘要</div>
    <div style="font-size:0.85rem;color:#888;margin-top:4px">
        基于 13 大师投票 · 新闻情绪 · 风险评估的综合建议</div>
</div>
""", unsafe_allow_html=True)


def _action_color(act: str) -> str:
    return {
        "买入": "#00C853", "加仓": "#26A69A", "持有": "#C9A962",
        "减仓": "#FF8A65", "卖出": "#F44336",
    }.get(act, "#6B6B75")


def _action_priority(act: str | None) -> int:
    """排序优先级：买入>加仓>卖出>减仓>持有>未分析"""
    return {
        "买入": 0, "加仓": 1, "卖出": 2, "减仓": 3, "持有": 4,
    }.get(act or "", 5)


# 决策分布统计
counts = {"买入": 0, "加仓": 0, "持有": 0, "减仓": 0, "卖出": 0, "未分析": 0}
total_pos = 0.0
for r in rows:
    if r["decision"]:
        a = r["decision"]["action"]
        counts[a] = counts.get(a, 0) + 1
        if r["decision"].get("position_pct"):
            total_pos += r["decision"]["position_pct"]
    else:
        counts["未分析"] += 1

analyzed = len(all_stocks) - counts["未分析"]

cols = st.columns([2, 1, 1, 1, 1, 1, 1])
with cols[0]:
    st.markdown(f"""
    <div style="background:rgba(201,169,98,0.04);border:1px solid rgba(201,169,98,0.18);
         border-radius:6px;padding:18px 22px">
        <div style="font-size:0.42rem;letter-spacing:4px;color:rgba(201,169,98,0.6);
             text-transform:uppercase;margin-bottom:6px">分析进度</div>
        <div style="font-size:1.6rem;font-weight:700;color:#fff">
            {analyzed} <span style="font-size:0.9rem;color:#888;font-weight:400">/ {len(all_stocks)}</span></div>
        <div style="font-size:0.78rem;color:#a8a39a;margin-top:2px">
            建议总仓位 {total_pos:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

for i, (act, n) in enumerate([("买入", counts["买入"]), ("加仓", counts["加仓"]),
                                ("持有", counts["持有"]), ("减仓", counts["减仓"]),
                                ("卖出", counts["卖出"]), ("未分析", counts["未分析"])]):
    with cols[i + 1]:
        color = _action_color(act) if act != "未分析" else "#6B6B75"
        st.markdown(f"""
        <div style="background:rgba(10,13,20,0.6);border:1px solid rgba(201,169,98,0.08);
             border-radius:6px;padding:18px 16px;text-align:center">
            <div style="font-size:0.42rem;letter-spacing:3px;color:{color};
                 text-transform:uppercase;margin-bottom:6px">{act}</div>
            <div style="font-size:1.6rem;font-weight:700;color:{color}">{n}</div>
        </div>
        """, unsafe_allow_html=True)


# ── 排序与过滤 ──────────────────────────────────────────────────────────────
st.markdown("<div style='margin:30px 0 14px'></div>", unsafe_allow_html=True)
ctrl_cols = st.columns([2, 2, 2, 6])
with ctrl_cols[0]:
    sort_by = st.selectbox("排序", ["决策优先级", "综合分↓", "综合分↑", "决策时间↓", "市场"], index=0)
with ctrl_cols[1]:
    filter_action = st.selectbox("筛选动作", ["全部", "买入", "加仓", "持有", "减仓", "卖出", "未分析"], index=0)
with ctrl_cols[2]:
    filter_market = st.selectbox("筛选市场", ["全部", "美股", "港股", "A股"], index=0)
with ctrl_cols[3]:
    if st.button("🔄 刷新缓存", help="重新读取最新决策（清除 60s 本地缓存）"):
        _load_summary.clear()
        st.rerun()


# 应用筛选
def _market_label(m: str) -> str:
    return {"us": "美股", "hk": "港股", "a_share": "A股"}.get(m, m)


filtered = rows
if filter_action != "全部":
    if filter_action == "未分析":
        filtered = [r for r in filtered if not r["decision"]]
    else:
        filtered = [r for r in filtered if r["decision"] and r["decision"]["action"] == filter_action]

if filter_market != "全部":
    market_map = {"美股": "us", "港股": "hk", "A股": "a_share"}
    filtered = [r for r in filtered if r["market"] == market_map[filter_market]]

# 应用排序
if sort_by == "决策优先级":
    filtered.sort(key=lambda r: (
        _action_priority(r["decision"]["action"]) if r["decision"] else 5,
        -(r["decision"]["combined_score"]) if r["decision"] else 0,
    ))
elif sort_by == "综合分↓":
    filtered.sort(key=lambda r: -(r["decision"]["combined_score"]) if r["decision"] else 999)
elif sort_by == "综合分↑":
    filtered.sort(key=lambda r: (r["decision"]["combined_score"]) if r["decision"] else -999)
elif sort_by == "决策时间↓":
    filtered.sort(key=lambda r: r["decision"]["decided_at"] if r["decision"] else datetime.min.replace(tzinfo=timezone.utc), reverse=True)
elif sort_by == "市场":
    filtered.sort(key=lambda r: ({"us": 0, "hk": 1, "a_share": 2}.get(r["market"], 9), r["symbol"]))


# ── 决策列表 ────────────────────────────────────────────────────────────────
if not filtered:
    st.info("没有符合条件的股票")
    st.stop()

now = datetime.now(timezone.utc)
STALE_DAYS = 7

table_rows = []
for r in filtered:
    sym, name, mk = r["symbol"], r["name"], r["market"]
    d = r["decision"]
    market_lbl = _market_label(mk)

    if d is None:
        table_rows.append(f"""
        <tr style="border-bottom:1px solid rgba(201,169,98,0.06)">
            <td style="padding:12px 14px;color:#fff;font-weight:600">{sym}</td>
            <td style="padding:12px 14px;color:#a8a39a">{name}</td>
            <td style="padding:12px 14px;color:#888;font-size:0.78rem">{market_lbl}</td>
            <td colspan="7" style="padding:12px 14px;color:#666;font-style:italic;font-size:0.85rem">
                未分析 — 在 AI Hedge Fund 页面运行后将自动落库</td>
        </tr>""")
        continue

    age_days = (now - d["decided_at"]).total_seconds() / 86400
    is_stale = age_days > STALE_DAYS
    age_label = "{:.0f}小时前".format(age_days * 24) if age_days < 1 else "{:.0f}天前".format(age_days)
    age_color = "#F5A623" if is_stale else "#888"

    ac = _action_color(d["action"])
    cs = d["combined_score"]
    cs_sign = "+" if cs > 0 else ""
    pos = "{:.1f}%".format(d["position_pct"]) if d.get("position_pct") else "—"

    # 价格偏离入场区间
    entry = d.get("entry_payload") or {}
    ideal = entry.get("ideal")
    price_now = d["price"]
    price_drift = ""
    if ideal and price_now:
        drift_pct = (price_now - ideal) / ideal * 100
        if abs(drift_pct) >= 5:
            color = "#FF8A65" if drift_pct > 0 else "#26A69A"
            price_drift = f'<span style="color:{color};font-size:0.7rem;margin-left:4px">({drift_pct:+.1f}%)</span>'

    table_rows.append(f"""
    <tr style="border-bottom:1px solid rgba(201,169,98,0.06)" class="dec-row">
        <td style="padding:12px 14px">
            <div style="color:#fff;font-weight:600">{sym}</div>
            <div style="color:#888;font-size:0.72rem;margin-top:2px">{market_lbl}</div>
        </td>
        <td style="padding:12px 14px;color:#a8a39a;font-size:0.85rem">{name}</td>
        <td style="padding:12px 14px;color:#fff;font-weight:500">
            {price_now:.2f}{price_drift}</td>
        <td style="padding:12px 14px">
            <div style="display:inline-block;padding:4px 12px;border:1px solid {ac};
                 border-radius:3px;color:{ac};font-weight:700;font-size:0.85rem">{d['action']}</div>
        </td>
        <td style="padding:12px 14px;color:#a8a39a;font-size:0.78rem">{d['conviction']}</td>
        <td style="padding:12px 14px;color:#fff;font-weight:600;text-align:right">
            {cs_sign}{cs}</td>
        <td style="padding:12px 14px;color:#C9A962;font-weight:500;text-align:right">{pos}</td>
        <td style="padding:12px 14px;color:#a8a39a;font-size:0.78rem">{d.get('news_label') or '—'}</td>
        <td style="padding:12px 14px;color:#a8a39a;font-size:0.78rem">{d.get('risk_level') or '—'}</td>
        <td style="padding:12px 14px;color:{age_color};font-size:0.78rem">{age_label}{' ⚠️' if is_stale else ''}</td>
    </tr>""")

st.markdown(f"""
<div style="background:rgba(10,13,20,0.6);border:1px solid rgba(201,169,98,0.12);
     border-radius:6px;overflow:hidden;margin-top:6px">
    <table style="width:100%;border-collapse:collapse">
        <thead>
            <tr style="background:rgba(201,169,98,0.06);
                 border-bottom:1px solid rgba(201,169,98,0.18)">
                <th style="padding:14px;text-align:left;font-size:0.65rem;
                     letter-spacing:2px;color:rgba(201,169,98,0.7)">股票</th>
                <th style="padding:14px;text-align:left;font-size:0.65rem;
                     letter-spacing:2px;color:rgba(201,169,98,0.7)">名称</th>
                <th style="padding:14px;text-align:left;font-size:0.65rem;
                     letter-spacing:2px;color:rgba(201,169,98,0.7)">现价</th>
                <th style="padding:14px;text-align:left;font-size:0.65rem;
                     letter-spacing:2px;color:rgba(201,169,98,0.7)">决策</th>
                <th style="padding:14px;text-align:left;font-size:0.65rem;
                     letter-spacing:2px;color:rgba(201,169,98,0.7)">信心</th>
                <th style="padding:14px;text-align:right;font-size:0.65rem;
                     letter-spacing:2px;color:rgba(201,169,98,0.7)">综合分</th>
                <th style="padding:14px;text-align:right;font-size:0.65rem;
                     letter-spacing:2px;color:rgba(201,169,98,0.7)">建议仓位</th>
                <th style="padding:14px;text-align:left;font-size:0.65rem;
                     letter-spacing:2px;color:rgba(201,169,98,0.7)">新闻</th>
                <th style="padding:14px;text-align:left;font-size:0.65rem;
                     letter-spacing:2px;color:rgba(201,169,98,0.7)">风险</th>
                <th style="padding:14px;text-align:left;font-size:0.65rem;
                     letter-spacing:2px;color:rgba(201,169,98,0.7)">更新</th>
            </tr>
        </thead>
        <tbody>{''.join(table_rows)}</tbody>
    </table>
</div>
""", unsafe_allow_html=True)

st.caption("⚠️ 标记为超过 {} 天的决策。点击 AI Hedge Fund 页面重新分析以更新。".format(STALE_DAYS))
