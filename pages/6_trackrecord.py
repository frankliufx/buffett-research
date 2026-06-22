"""战绩追踪 — 分析历史 · 评分回报 · 可验证信用记录

这是飞轮的可视化层：
把积累的分析快照 + 实时价格对比，
呈现出"高分股票实际表现如何"的答案。

这个答案会随时间积累变得越来越有力，
是任何竞争对手无法快速复制的资产。
"""

import streamlit as st
from datetime import datetime, timezone

from src.auth import get_current_user
from src.tracker import load_user_analysis_history, compute_track_record
from src.data.price import fetch_quote
from src.ui_theme import get_global_css, COLORS
import streamlit.components.v1 as components
import html as _html_module
import logging
from src.db.decisions import get_decisions_for_accuracy
from src.db.session import db_available
from src.analysis.accuracy import compute_hedge_fund_accuracy

st.markdown(get_global_css(), unsafe_allow_html=True)

# ── auth ─────────────────────────────────────────────────────────────────────
user = get_current_user()
if not user:
    st.warning("请先登录")
    st.stop()
uid = user.get("username", "anonymous")

# ── helpers ───────────────────────────────────────────────────────────────────
def _days_ago(iso_str: str) -> int:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return 0

def _color(val):
    if val is None:   return COLORS.get("text_muted", "#5A5A6A")
    if val > 0:       return "#3ECF8E"
    if val < 0:       return "#EF4444"
    return "#5A5A6A"

def _fmt_ret(val):
    if val is None: return "—"
    return "{:+.1f}%".format(val)

def _score_color(s):
    if s >= 80: return "#3ECF8E"
    if s >= 60: return "#C9A962"
    return "#EF4444"

logger = logging.getLogger(__name__)

def _html(body, height=300):
    page = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,'
        'wght@0,300;0,400;0,700;1,300&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">'
        '<style>*{margin:0;padding:0;box-sizing:border-box;}'
        'body{background:#06060A;font-family:\'Inter\',-apple-system,sans-serif;'
        'color:#E8E8F0;-webkit-font-smoothing:antialiased;}'
        '.serif{font-family:\'Cormorant Garamond\',Georgia,serif;}'
        '</style></head><body>' + body + '</body></html>'
    )
    components.html(page, height=height, scrolling=False)

# ── load data ─────────────────────────────────────────────────────────────────
with st.spinner("加载分析历史…"):
    records = load_user_analysis_history(uid, limit=200)

# ── 空状态引导（首次使用）────────────────────────────────────────────────────
if not records:
    _html("""
<div style="padding:80px 48px;background:#06060A;text-align:center;">
  <div style="font-size:0.52rem;letter-spacing:6px;color:#C9A962;
    text-transform:uppercase;font-weight:500;margin-bottom:24px;">Track Record</div>
  <div class="serif" style="font-size:2.4rem;font-weight:300;color:#3A3A4A;margin-bottom:16px;">
    你的战绩档案即将开始
  </div>
  <p style="font-size:0.85rem;color:#2A2A36;line-height:2;max-width:440px;margin:0 auto 32px;">
    每次分析自动存档。回到 Analysis 页面，分析任意股票——<br>
    第一条记录就会出现在这里，飞轮开始转动。
  </p>
  <div style="display:inline-block;padding:12px 32px;border:1px solid #2A2A36;
    font-size:0.65rem;letter-spacing:3px;color:#3A3A4A;text-transform:uppercase;">
    前往 Analysis → 开始第一次分析
  </div>
</div>
""", height=380)
    st.stop()

# Fetch current prices for all unique symbols
_sym_markets = list({(r["symbol"], r["market"]) for r in records})
current_prices = {}
if _sym_markets:
    with st.spinner("获取当前价格…"):
        for sym, mkt in _sym_markets:
            try:
                q = fetch_quote(sym, mkt)
                p = q.get("price")
                if p:
                    current_prices["{}:{}".format(mkt, sym)] = float(p)
            except Exception:
                pass

stats = compute_track_record(records, current_prices) if records else {}

# ── AI 大师准确率（DB 可用时加载）─────────────────────────────────────────────
_analyst_accuracy: dict = {}
_past_decisions: list = []
if db_available():
    try:
        _past_decisions = get_decisions_for_accuracy(min_age_days=30, limit=300)
        if _past_decisions:
            _acc_symbols = list({(d["symbol"], d["market"]) for d in _past_decisions})
            _acc_prices: dict[str, float] = {}
            for sym, mkt in _acc_symbols:
                try:
                    q = fetch_quote(sym, mkt)
                    p = q.get("price")
                    if p is not None:
                        _acc_prices["{}:{}".format(mkt, sym)] = float(p)
                except Exception:
                    pass
            _analyst_accuracy = compute_hedge_fund_accuracy(_past_decisions, _acc_prices)
    except Exception as _e:
        logger.warning("Failed to load analyst accuracy: %s", _e)
enriched = stats.get("records_with_return", [])

# ══════════════════════════════════════════════════════════════════════════════
# HERO — 战绩总览
# ══════════════════════════════════════════════════════════════════════════════
total    = stats.get("total_analyzed", 0)
unique   = stats.get("unique_stocks", 0)
hi_avg   = stats.get("high_score_avg")
beat_pct = stats.get("beat_market_pct")

_html("""
<div style="position:relative;overflow:hidden;padding:60px 48px 52px;background:#06060A;">
  <div style="position:absolute;inset:0;pointer-events:none;opacity:0.025;
    background-image:linear-gradient(#C9A962 1px,transparent 1px),
                     linear-gradient(90deg,#C9A962 1px,transparent 1px);
    background-size:80px 80px;"></div>
  <div style="position:absolute;left:0;top:0;width:3px;height:100%;
    background:linear-gradient(180deg,transparent,#C9A962 25%,#C9A962 75%,transparent);"></div>
  <div style="position:relative;">
    <div style="font-size:0.52rem;letter-spacing:6px;color:#C9A962;
      text-transform:uppercase;font-weight:500;margin-bottom:20px;">Track Record</div>
    <h1 class="serif" style="font-size:clamp(2rem,4vw,3.2rem);font-weight:300;
      color:#F0EEE8;line-height:1.1;margin-bottom:8px;">
      可验证的投资洞察
    </h1>
    <p style="font-size:0.85rem;color:#5A5A6A;line-height:1.8;max-width:560px;margin-bottom:0;">
      每一次分析都会自动存档评分快照。随着时间积累，
      这里将呈现 AI Buffett 评分体系的真实预测能力——
      高分股票的实际回报，是我们唯一的信用证明。
    </p>
  </div>
</div>
""", height=280)

# ══════════════════════════════════════════════════════════════════════════════
# 核心数据卡
# ══════════════════════════════════════════════════════════════════════════════
def _stat_card(label, value, sub="", color="#C9A962"):
    return (
        '<div style="flex:1;padding:24px 20px;border-right:1px solid #1A1A22;text-align:center;">'
        '<div class="serif" style="font-size:2.4rem;font-weight:600;color:{};line-height:1;">{}</div>'
        '<div style="font-size:0.5rem;letter-spacing:3px;color:#3A3A4A;text-transform:uppercase;margin-top:6px;">{}</div>'
        '{}'
        '</div>'
    ).format(
        color, value, label,
        '<div style="font-size:0.68rem;color:#5A5A6A;margin-top:4px;">{}</div>'.format(sub) if sub else ""
    )

hi_avg_str   = "{:+.1f}%".format(hi_avg)   if hi_avg is not None else "积累中"
beat_str     = "{:.0f}%".format(beat_pct)  if beat_pct is not None else "积累中"
hi_color     = "#3ECF8E" if (hi_avg or 0) > 0 else "#C9A962"

cards_html = (
    '<div style="display:flex;border:1px solid #1A1A22;border-top:none;">'
    + _stat_card("Total Analyses",   str(total),     "累计分析次数")
    + _stat_card("Stocks Covered",   str(unique),    "覆盖股票数")
    + _stat_card("Score ≥80 Avg Return", hi_avg_str, "高分股票平均回报", hi_color)
    + _stat_card("Positive Return",  beat_str,       "回报为正的比例")
    + '</div>'
)
_html("""
<div style="padding:0 48px 40px;background:#06060A;border-top:1px solid #1A1A22;">
""" + cards_html + "</div>", height=140)

# ══════════════════════════════════════════════════════════════════════════════
# 评分分层回报
# ══════════════════════════════════════════════════════════════════════════════
hi_cnt = stats.get("high_count", 0)
mi_cnt = stats.get("mid_count", 0)
lo_cnt = stats.get("low_count", 0)
mi_avg = stats.get("mid_score_avg")
lo_avg = stats.get("low_score_avg")

def _tier_row(label, count, avg_ret, bar_color):
    avg_str = "{:+.1f}%".format(avg_ret) if avg_ret is not None else "—"
    avg_c   = _color(avg_ret)
    bar_w   = min(100, abs(avg_ret or 0) * 3)
    return (
        '<div style="display:grid;grid-template-columns:140px 60px 1fr 100px;'
        'align-items:center;gap:20px;padding:16px 0;border-bottom:1px solid #0E0E16;">'
        '<div style="font-size:0.82rem;font-weight:500;color:#C8C8D8;">{}</div>'
        '<div style="font-size:0.78rem;color:#5A5A6A;">{} 只</div>'
        '<div style="height:4px;background:#0E0E16;border-radius:2px;">'
        '<div style="width:{}%;height:100%;background:{};border-radius:2px;transition:width 0.6s ease;"></div>'
        '</div>'
        '<div style="font-size:0.9rem;font-weight:600;color:{};text-align:right;">{}</div>'
        '</div>'
    ).format(label, count, bar_w, bar_color, avg_c, avg_str)

tier_rows = (
    _tier_row("评分 ≥ 80 · 优质", hi_cnt, hi_avg, "#3ECF8E")
    + _tier_row("评分 60–79 · 良好", mi_cnt, mi_avg, "#C9A962")
    + _tier_row("评分 < 60 · 谨慎", lo_cnt, lo_avg, "#EF4444")
)

_html("""
<div style="padding:48px 48px 40px;border-top:1px solid #1A1A22;background:#08080E;">
  <div style="font-size:0.52rem;letter-spacing:5px;color:#C9A962;
    text-transform:uppercase;font-weight:500;margin-bottom:8px;">Score Performance</div>
  <h2 class="serif" style="font-size:1.9rem;font-weight:300;color:#E8E8F0;
    margin-bottom:32px;letter-spacing:-0.3px;">评分分层 · 实际回报</h2>
  <div style="grid-template-columns:140px 60px 1fr 100px;display:grid;
    padding-bottom:12px;border-bottom:1px solid #1A1A22;gap:20px;">
    <div style="font-size:0.46rem;letter-spacing:3px;color:#3A3A4A;text-transform:uppercase;">评分区间</div>
    <div style="font-size:0.46rem;letter-spacing:3px;color:#3A3A4A;text-transform:uppercase;">数量</div>
    <div style="font-size:0.46rem;letter-spacing:3px;color:#3A3A4A;text-transform:uppercase;">平均回报</div>
    <div></div>
  </div>
""" + tier_rows + "</div>", height=300)

# ══════════════════════════════════════════════════════════════════════════════
# 分析明细表
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style='font-size:0.52rem;letter-spacing:5px;color:#C9A962;
text-transform:uppercase;font-weight:500;padding:32px 0 12px;'>Analysis Log</div>
""", unsafe_allow_html=True)

if not enriched:
    st.info("暂无分析记录。回到「分析」页面分析任意股票，记录将自动积累。")
else:
    # Filter controls
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        mkt_filter = st.selectbox("市场", ["全部", "us", "hk", "a_share"], key="tr_mkt")
    with col_f2:
        score_filter = st.selectbox("评分", ["全部", "≥80", "60-79", "<60"], key="tr_score")

    filtered = enriched
    if mkt_filter != "全部":
        filtered = [r for r in filtered if r.get("market") == mkt_filter]
    if score_filter == "≥80":
        filtered = [r for r in filtered if r.get("score_total", 0) >= 80]
    elif score_filter == "60-79":
        filtered = [r for r in filtered if 60 <= r.get("score_total", 0) < 80]
    elif score_filter == "<60":
        filtered = [r for r in filtered if r.get("score_total", 0) < 60]

    # Table header
    st.markdown("""
    <div style='display:grid;grid-template-columns:80px 1fr 60px 60px 80px 80px 80px 80px;
    gap:8px;padding:8px 12px;background:#09090F;border:1px solid #1A1A22;
    font-size:0.44rem;letter-spacing:3px;color:#3A3A4A;text-transform:uppercase;'>
      <div>日期</div><div>股票</div><div>市场</div>
      <div>评分</div><div>结论</div><div>分析时价格</div><div>当前价格</div><div>回报</div>
    </div>
    """, unsafe_allow_html=True)

    for rec in filtered[:50]:
        sym      = rec.get("symbol", "")
        mkt      = rec.get("market", "")
        nm       = rec.get("name", sym)
        score    = rec.get("score_total", 0)
        verdict  = rec.get("verdict", "—")
        ep       = rec.get("price")
        cp       = rec.get("current_price")
        ret      = rec.get("return_pct")
        days     = _days_ago(rec.get("analyzed_at", ""))
        sc_color = _score_color(score)
        r_color  = _color(ret)

        ep_str = "{:.2f}".format(ep) if ep else "—"
        cp_str = "{:.2f}".format(cp) if cp else "—"

        st.markdown("""
        <div style='display:grid;grid-template-columns:80px 1fr 60px 60px 80px 80px 80px 80px;
        gap:8px;padding:10px 12px;border:1px solid #0E0E16;border-top:none;
        font-size:0.78rem;color:#7A7A88;align-items:center;'>
          <div style='color:#4A4A5A;font-size:0.72rem;'>{days}天前</div>
          <div style='color:#C8C8D8;font-weight:500;'>{nm}<br>
            <span style='font-size:0.65rem;color:#4A4A5A;'>{sym}</span></div>
          <div style='font-size:0.65rem;letter-spacing:2px;text-transform:uppercase;
            color:#4A4A5A;'>{mkt}</div>
          <div style='font-weight:700;color:{sc_color};'>{score:.0f}</div>
          <div style='font-size:0.68rem;color:#8A8A96;'>{verdict}</div>
          <div>{ep_str}</div>
          <div style='color:#9A9AA8;'>{cp_str}</div>
          <div style='font-weight:600;color:{r_color};'>{ret_str}</div>
        </div>
        """.format(
            days=days, nm=nm, sym=sym, mkt=mkt,
            sc_color=sc_color, score=score,
            verdict=verdict, ep_str=ep_str, cp_str=cp_str,
            r_color=r_color, ret_str=_fmt_ret(ret),
        ), unsafe_allow_html=True)

    if len(filtered) > 50:
        st.caption("显示最近 50 条，共 {} 条记录".format(len(filtered)))

# ══════════════════════════════════════════════════════════════════════════════
# AI 大师准确率（需 DB 启用）
# ══════════════════════════════════════════════════════════════════════════════
if _analyst_accuracy:
    sorted_analysts = sorted(
        _analyst_accuracy.items(),
        key=lambda x: (x[1]["hit_rate"], x[1]["total"]),
        reverse=True,
    )

    rows_html = ""
    for rank, (aid, rec) in enumerate(sorted_analysts, 1):
        name_safe = _html_module.escape(str(rec.get("name", aid)))
        total = rec["total"]
        hits = rec["hits"]
        hit_rate = rec["hit_rate"]
        avg_conf = rec["avg_confidence"]

        bar_w = int(hit_rate * 100)
        bar_color = "#3ECF8E" if hit_rate >= 0.6 else ("#C9A962" if hit_rate >= 0.4 else "#EF4444")
        rate_color = bar_color
        rank_color = "#C9A962" if rank == 1 else "#3A3A4A"

        rows_html += (
            '<div style="display:grid;grid-template-columns:36px 160px 60px 60px 1fr 80px;'
            'align-items:center;gap:16px;padding:14px 0;border-bottom:1px solid #0E0E16;">'
            '<div style="font-size:0.72rem;font-weight:700;color:{rank_color};text-align:center;">#{rank}</div>'
            '<div style="font-size:0.82rem;font-weight:500;color:#C8C8D8;">{name}</div>'
            '<div style="font-size:0.78rem;color:#5A5A6A;text-align:center;">{hits}/{total}</div>'
            '<div style="font-size:0.75rem;color:#5A5A6A;text-align:center;">{conf:.0f}%</div>'
            '<div style="height:4px;background:#0E0E16;border-radius:2px;">'
            '<div style="width:{bar_w}%;height:100%;background:{bar_color};border-radius:2px;"></div>'
            '</div>'
            '<div style="font-size:0.9rem;font-weight:700;color:{rate_color};text-align:right;">{rate:.0f}%</div>'
            '</div>'
        ).format(
            rank=rank, rank_color=rank_color,
            name=name_safe, hits=hits, total=total,
            conf=avg_conf, bar_w=bar_w, bar_color=bar_color,
            rate_color=rate_color, rate=hit_rate * 100,
        )

    header_html = (
        '<div style="display:grid;grid-template-columns:36px 160px 60px 60px 1fr 80px;'
        'align-items:center;gap:16px;padding-bottom:12px;border-bottom:1px solid #1A1A22;">'
        '<div></div>'
        '<div style="font-size:0.46rem;letter-spacing:3px;color:#3A3A4A;text-transform:uppercase;">大师</div>'
        '<div style="font-size:0.46rem;letter-spacing:3px;color:#3A3A4A;text-transform:uppercase;text-align:center;">命中/总计</div>'
        '<div style="font-size:0.46rem;letter-spacing:3px;color:#3A3A4A;text-transform:uppercase;text-align:center;">平均置信</div>'
        '<div style="font-size:0.46rem;letter-spacing:3px;color:#3A3A4A;text-transform:uppercase;">准确率</div>'
        '<div></div>'
        '</div>'
    )

    total_decisions = len(_past_decisions)

    _html("""
<div style="padding:48px 48px 40px;border-top:1px solid #1A1A22;background:#06060A;">
  <div style="font-size:0.52rem;letter-spacing:5px;color:#C9A962;
    text-transform:uppercase;font-weight:500;margin-bottom:8px;">AI Master Accuracy</div>
  <h2 class="serif" style="font-size:1.9rem;font-weight:300;color:#E8E8F0;
    margin-bottom:8px;letter-spacing:-0.3px;">AI 大师准确率 · 最近 30 天</h2>
  <p style="font-size:0.72rem;color:#3A3A4A;margin-bottom:28px;">
    基于 {total} 次决策的历史验证 · 上涨预测在价格上涨时命中，下跌预测在价格下跌时命中
  </p>
""".format(total=total_decisions) + header_html + rows_html + "</div>", height=80 + len(sorted_analysts) * 44 + 120)

elif db_available():
    st.info("暂无足够历史决策数据（需至少 30 天前的记录）。随着使用积累，AI 大师准确率将自动呈现。")

# ── footer note ───────────────────────────────────────────────────────────────
st.markdown("""
<div style='font-size:0.55rem;color:#2A2A36;letter-spacing:1px;
padding:24px 0 8px;text-align:center;'>
回报基于分析时价格与当前价格对比，不含股息。仅供研究参考，不构成投资建议。
</div>
""", unsafe_allow_html=True)
