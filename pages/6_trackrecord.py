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

def _html(body, height=300):
    page = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,'
        'wght@0,300;0,400;0,700;1,300&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">'
        '<style>*{margin:0;padding:0;box-sizing:border-box;}'
        'body{background:#0A0A0F;font-family:\'Inter\',-apple-system,sans-serif;'
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
<div style="padding:80px 48px;background:#0A0A0F;text-align:center;">
  <div style="font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;
    text-transform:uppercase;font-weight:500;margin-bottom:24px;">Track Record</div>
  <div class="serif" style="font-size:2.4rem;font-weight:300;color:#5A5A66;margin-bottom:16px;">
    你的战绩档案即将开始
  </div>
  <p style="font-size:0.85rem;color:#5A5A66;line-height:2;max-width:440px;margin:0 auto 32px;">
    每次分析自动存档。回到 Analysis 页面，分析任意股票——<br>
    第一条记录就会出现在这里，飞轮开始转动。
  </p>
  <div style="display:inline-block;padding:12px 32px;border:1px solid #2A2A36;
    font-size:0.65rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;">
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
enriched = stats.get("records_with_return", [])

# ══════════════════════════════════════════════════════════════════════════════
# HERO — 战绩总览
# ══════════════════════════════════════════════════════════════════════════════
total    = stats.get("total_analyzed", 0)
unique   = stats.get("unique_stocks", 0)
hi_avg   = stats.get("high_score_avg")
beat_pct = stats.get("beat_market_pct")

_html("""
<div style="position:relative;overflow:hidden;padding:60px 48px 52px;background:#0A0A0F;">
  <div style="position:absolute;inset:0;pointer-events:none;opacity:0.025;
    background-image:linear-gradient(#C9A962 1px,transparent 1px),
                     linear-gradient(90deg,#C9A962 1px,transparent 1px);
    background-size:80px 80px;"></div>
  <div style="position:absolute;left:0;top:0;width:3px;height:100%;
    background:linear-gradient(180deg,transparent,#C9A962 25%,#C9A962 75%,transparent);"></div>
  <div style="position:relative;">
    <div style="font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;
      text-transform:uppercase;font-weight:500;margin-bottom:20px;">Track Record</div>
    <h1 class="serif" style="font-size:clamp(2rem,4vw,3.2rem);font-weight:300;
      color:#F0EEE8;line-height:1.1;margin-bottom:8px;">
      可验证的投资洞察
    </h1>
    <p style="font-size:0.85rem;color:#5A5A66;line-height:1.8;max-width:560px;margin-bottom:0;">
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
        '<div style="font-size:0.5rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;margin-top:6px;">{}</div>'
        '{}'
        '</div>'
    ).format(
        color, value, label,
        '<div style="font-size:0.68rem;color:#5A5A66;margin-top:4px;">{}</div>'.format(sub) if sub else ""
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
<div style="padding:0 48px 40px;background:#0A0A0F;border-top:1px solid #1A1A22;">
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
        '<div style="font-size:0.78rem;color:#5A5A66;">{} 只</div>'
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
<div style="padding:48px 48px 40px;border-top:1px solid #1A1A22;background:#0A0A0F;">
  <div style="font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;
    text-transform:uppercase;font-weight:500;margin-bottom:8px;">Score Performance</div>
  <h2 class="serif" style="font-size:1.9rem;font-weight:300;color:#E8E8F0;
    margin-bottom:32px;letter-spacing:-0.3px;">评分分层 · 实际回报</h2>
  <div style="grid-template-columns:140px 60px 1fr 100px;display:grid;
    padding-bottom:12px;border-bottom:1px solid #1A1A22;gap:20px;">
    <div style="font-size:0.62rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;">评分区间</div>
    <div style="font-size:0.62rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;">数量</div>
    <div style="font-size:0.62rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;">平均回报</div>
    <div></div>
  </div>
""" + tier_rows + "</div>", height=300)

# ══════════════════════════════════════════════════════════════════════════════
# Hall of Fame & Wall of Shame — the moat made visible
# (only thing competitors literally cannot reproduce: your real prediction record)
# ══════════════════════════════════════════════════════════════════════════════
_records_with_returns = [r for r in enriched if r.get("return_pct") is not None]
if _records_with_returns:
    # Top 3 best AND worst by absolute return
    _best = sorted(_records_with_returns, key=lambda r: r.get("return_pct") or -999, reverse=True)[:3]
    _worst = sorted(_records_with_returns, key=lambda r: r.get("return_pct") or 999)[:3]

    def _wall_card(rec, *, color, accent_emoji):
        sym = rec.get("symbol", "")
        name = (rec.get("name", "") or "")[:18]
        ret = rec.get("return_pct") or 0
        score = rec.get("score_total", 0) or 0
        days = _days_ago(rec.get("timestamp", ""))
        ret_str = "{:+.1f}%".format(ret)
        verdict = rec.get("verdict", "")[:20]
        return f"""
<div style="background:#0D0D14;border:1px solid #1E1E2A;border-left:3px solid {color};
  border-radius:6px;padding:14px 16px;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;font-weight:600;color:#F2F2F5;letter-spacing:-0.01em;">
      {sym}
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:700;color:{color};letter-spacing:-0.01em;">
      {accent_emoji} {ret_str}
    </div>
  </div>
  <div style="font-size:0.72rem;color:#9A9AA8;margin-bottom:8px;line-height:1.3;">
    {name}
  </div>
  <div style="display:flex;align-items:center;gap:10px;font-size:0.6rem;color:#5A5A66;letter-spacing:0.3px;">
    <span>MOAT <span style="color:#C9A962;font-family:'JetBrains Mono',monospace;font-weight:600;">{score:.0f}</span></span>
    <span>·</span>
    <span>{days} days ago</span>
    <span>·</span>
    <span style="color:#7A7A88;">{verdict}</span>
  </div>
</div>"""

    _hof_html = "".join(_wall_card(r, color="#3ECF8E", accent_emoji="▲") for r in _best)
    _wos_html = "".join(_wall_card(r, color="#EF4444", accent_emoji="▼") for r in _worst)

    components.html(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0A0A0F;font-family:'Inter',-apple-system,sans-serif;padding:32px 0 0;color:#F2F2F5}}
.section-title{{font-family:'Cormorant Garamond',serif;font-size:1.6rem;font-weight:600;color:#F2F2F5;line-height:1.2;margin-bottom:4px}}
.section-title .accent{{font-style:italic;color:#C9A962;font-weight:600}}
.section-sub{{font-size:0.66rem;color:#5A5A66;letter-spacing:0.5px;margin-bottom:16px}}
.split{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.col-header{{display:flex;align-items:center;gap:8px;font-size:0.6rem;letter-spacing:1.5px;text-transform:uppercase;font-weight:500;margin-bottom:10px}}
.col-rows{{display:flex;flex-direction:column;gap:8px}}
@media (max-width:720px){{.split{{grid-template-columns:1fr}}}}
</style></head><body>
<div class="section-title">Your <span class="accent">Track Record</span> — verifiable, time-stamped.</div>
<div class="section-sub">Every analysis is a public-to-yourself prediction. Time scores the work.</div>
<div class="split">
  <div>
    <div class="col-header" style="color:#3ECF8E;">
      <span style="font-size:1rem;">🏆</span>
      <span>Hall of Fame · Top {len(_best)} returns</span>
    </div>
    <div class="col-rows">{_hof_html}</div>
  </div>
  <div>
    <div class="col-header" style="color:#EF4444;">
      <span style="font-size:1rem;">⚠️</span>
      <span>Wall of Shame · Worst {len(_worst)} returns</span>
    </div>
    <div class="col-rows">{_wos_html}</div>
  </div>
</div>
</body></html>""", height=460, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
# 分析明细表
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style='font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;
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
    gap:8px;padding:8px 12px;background:#0A0A0F;border:1px solid #1A1A22;
    font-size:0.62rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;'>
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

# ── footer note ───────────────────────────────────────────────────────────────
st.markdown("""
<div style='font-size:0.55rem;color:#5A5A66;letter-spacing:1px;
padding:24px 0 8px;text-align:center;'>
回报基于分析时价格与当前价格对比，不含股息。仅供研究参考，不构成投资建议。
</div>
""", unsafe_allow_html=True)
