"""Home — AI Buffett · AI-Powered Value Intelligence"""

import random
import streamlit as st
import streamlit.components.v1 as components
from src.ui_theme import get_global_css
from src.ai.knowledge_base import BUFFETT_QUOTES, DUAN_YONGPING_QUOTES
from src.data.macro import get_buffett_indicator

st.markdown(get_global_css(), unsafe_allow_html=True)

# ── data ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _load_bi():
    try:
        return get_buffett_indicator()
    except Exception:
        return {}

bi = _load_bi()

# Sample quotes
_bq4 = random.sample(BUFFETT_QUOTES,        min(4, len(BUFFETT_QUOTES)))
_dq4 = random.sample(DUAN_YONGPING_QUOTES,  min(4, len(DUAN_YONGPING_QUOTES)))
buffett_q = _bq4[0]
duan_q    = _dq4[0]

# ── html helper ───────────────────────────────────────────────────────────────
_FONT = (
    "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght"
    "@0,300;0,400;0,600;0,700;1,300;1,400&family=Inter:wght@300;400;500;600;700&display=swap"
)
_BASE = (
    "*{margin:0;padding:0;box-sizing:border-box;}"
    "body{background:#0A0A0F;font-family:'Inter',-apple-system,sans-serif;"
    "color:#E8E8F0;-webkit-font-smoothing:antialiased;}"
    ".serif{font-family:'Cormorant Garamond',Georgia,serif;}"
    "@keyframes fu{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}"
    ".fu{animation:fu 0.7s ease both;}"
    ".d1{animation-delay:.1s}.d2{animation-delay:.25s}.d3{animation-delay:.4s}.d4{animation-delay:.55s}.d5{animation-delay:.7s}"
)

def _html(body: str, height: int = 400):
    page = (
        f'<!DOCTYPE html><html><head><meta charset="utf-8">'
        f'<link href="{_FONT}" rel="stylesheet">'
        f'<style>{_BASE}</style></head><body>'
        + body + "</body></html>"
    )
    components.html(page, height=height, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
# 01  WORKSPACE HERO  (v2 redesign — replaces the marketing scroll up top)
# ══════════════════════════════════════════════════════════════════════════════
# Authenticated user lands here. We give them a *workspace* greeting +
# their flywheel stats + 4 quick actions, NOT a marketing pitch. The
# original luxury hero is preserved for unauthenticated visitors at the
# bottom of this file (search '01_LEGACY_HERO').

# Personal flywheel data (uses tracker history if available)
_uid_for_hero = "anonymous"
try:
    from src.auth import get_current_user as _gcu_hero
    _u = _gcu_hero()
    _uid_for_hero = (_u or {}).get("username", "anonymous")
    _display_name = (_u or {}).get("name", "Investor")
except Exception:
    _display_name = "Investor"

try:
    from src.tracker import load_user_analysis_history as _hist_load
    _flywheel = _hist_load(_uid_for_hero, limit=200)
except Exception:
    _flywheel = []

# Compute the three flywheel stats
import datetime as _dt
_now = _dt.datetime.now()
_30d_ago = _now - _dt.timedelta(days=30)
_recent_count = sum(
    1 for r in _flywheel
    if r.get("timestamp") and _dt.datetime.fromisoformat(str(r["timestamp"])[:19]) > _30d_ago
)
_avg_grade_score = (
    round(sum(r.get("score_total", 0) for r in _flywheel) / len(_flywheel), 1)
    if _flywheel else 0.0
)
_unique_stocks = len({(r.get("market"), r.get("symbol")) for r in _flywheel if r.get("symbol")})

# Greeting based on local time
_h = _now.hour
_greet = ("Good morning" if 5 <= _h < 12 else
          "Good afternoon" if _h < 18 else
          "Good evening")

_html(f"""
<div style="position:relative;padding:48px 52px 36px;background:linear-gradient(135deg,#0A0A0F 0%,#0F0F18 100%);">

  <!-- subtle gold accent line -->
  <div style="position:absolute;left:0;top:0;width:2px;height:100%;
    background:linear-gradient(180deg,transparent 0%,#C9A962 30%,#C9A962 70%,transparent 100%);"></div>

  <!-- top-right v2 build mark for confirmation -->
  <div style="position:absolute;top:24px;right:36px;
    font-family:'JetBrains Mono',monospace;font-size:0.62rem;color:#C9A962;
    background:rgba(201,169,98,0.08);border:1px solid rgba(201,169,98,0.3);
    padding:3px 10px;border-radius:3px;letter-spacing:0.5px;">
    workspace · v2
  </div>

  <div style="max-width:1100px;margin:0 auto;">

    <!-- greeting line — workspace, not marketing -->
    <div class="fu d1" style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
      <div style="width:6px;height:6px;background:#C9A962;border-radius:50%;"></div>
      <span style="font-size:0.7rem;letter-spacing:1.5px;color:#9A9AA8;text-transform:uppercase;font-weight:500;">
        {_now.strftime('%A · %Y.%m.%d')}
      </span>
    </div>

    <h1 class="fu d2 serif" style="font-size:clamp(2rem,4vw,2.8rem);font-weight:600;
      color:#F2F2F5;line-height:1.15;letter-spacing:-0.01em;margin-bottom:6px;">
      {_greet},
      <span style="color:#C9A962;font-style:italic;">{_display_name}</span>.
    </h1>

    <p class="fu d2" style="font-size:0.95rem;color:#9A9AA8;line-height:1.55;font-weight:400;
      max-width:620px;margin-bottom:32px;">
      Your value-investing workspace. Pick up where you left off, or browse the
      philosophy below.
    </p>

    <!-- 3-stat flywheel row (your work, not marketing claims) -->
    <div class="fu d3" style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:24px;">

      <div style="background:#101018;border:1px solid #2A2A33;border-radius:6px;padding:18px 20px;">
        <div style="font-size:0.6rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;font-weight:500;margin-bottom:6px;">
          Analyses · last 30 d
        </div>
        <div class="serif" style="font-family:'JetBrains Mono',monospace;font-size:1.9rem;font-weight:600;color:#F2F2F5;line-height:1;">
          {_recent_count}
        </div>
        <div style="font-size:0.66rem;color:#5A5A66;margin-top:6px;">
          {_unique_stocks} unique tickers tracked
        </div>
      </div>

      <div style="background:#101018;border:1px solid #2A2A33;border-radius:6px;padding:18px 20px;">
        <div style="font-size:0.6rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;font-weight:500;margin-bottom:6px;">
          Avg MOAT score
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:1.9rem;font-weight:600;color:{'#3ECF8E' if _avg_grade_score >= 65 else '#C9A962' if _avg_grade_score >= 50 else '#9A9AA8'};line-height:1;">
          {_avg_grade_score:.0f}<span style="font-size:0.85rem;color:#5A5A66;font-weight:400;"> /100</span>
        </div>
        <div style="font-size:0.66rem;color:#5A5A66;margin-top:6px;">
          {'core thesis quality' if _flywheel else 'no analyses yet'}
        </div>
      </div>

      <div style="background:#101018;border:1px solid #2A2A33;border-radius:6px;padding:18px 20px;">
        <div style="font-size:0.6rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;font-weight:500;margin-bottom:6px;">
          Markets enabled
        </div>
        <div class="serif" style="font-size:1.9rem;font-weight:600;color:#F2F2F5;line-height:1;">
          US · HK · A
        </div>
        <div style="font-size:0.66rem;color:#5A5A66;margin-top:6px;">
          unified value lens
        </div>
      </div>

    </div>

    <!-- quick action chips — direct entry to the 4 main loops -->
    <div class="fu d4" style="display:flex;gap:8px;flex-wrap:wrap;">
      <div style="background:#101018;border:1px solid #C9A962;color:#C9A962;border-radius:4px;padding:10px 16px;font-size:0.78rem;font-weight:500;cursor:pointer;">
        → Analyze a stock
      </div>
      <div style="background:#101018;border:1px solid #2A2A33;color:#9A9AA8;border-radius:4px;padding:10px 16px;font-size:0.78rem;font-weight:500;cursor:pointer;">
        → Hedge fund (13 analysts)
      </div>
      <div style="background:#101018;border:1px solid #2A2A33;color:#9A9AA8;border-radius:4px;padding:10px 16px;font-size:0.78rem;font-weight:500;cursor:pointer;">
        → AI advisor chat
      </div>
      <div style="background:#101018;border:1px solid #2A2A33;color:#9A9AA8;border-radius:4px;padding:10px 16px;font-size:0.78rem;font-weight:500;cursor:pointer;">
        → Track record
      </div>
    </div>

  </div>
</div>
""", height=460)


# ══════════════════════════════════════════════════════════════════════════════
# 01_LEGACY_HERO  (preserved — original "Invest with the Wisdom of Masters"
# block; kept as a section divider before the philosophy/marquee content
# below so users with that emotional attachment still see it.)
# ══════════════════════════════════════════════════════════════════════════════
_html("""
<div style="position:relative;overflow:hidden;padding:48px 52px 40px;min-height:100%;background:#0A0A0F;border-top:1px solid #2A2A33;">

  <!-- grid texture -->
  <div style="position:absolute;inset:0;pointer-events:none;opacity:0.028;
    background-image:linear-gradient(#C9A962 1px,transparent 1px),
                     linear-gradient(90deg,#C9A962 1px,transparent 1px);
    background-size:80px 80px;"></div>

  <!-- gold left accent -->
  <div style="position:absolute;left:0;top:0;width:3px;height:100%;
    background:linear-gradient(180deg,transparent 0%,#C9A962 20%,#C9A962 80%,transparent 100%);"></div>

  <!-- top-right year tag -->
  <div class="fu d1" style="position:absolute;top:32px;right:52px;
    font-size:0.62rem;letter-spacing:1.5px;color:#5A5A66;text-transform:uppercase;">Our Philosophy</div>

  <div style="position:relative;max-width:920px;">

    <div class="fu d1" style="display:flex;align-items:center;gap:14px;margin-bottom:32px;">
      <div style="width:6px;height:6px;background:#C9A962;border-radius:50%;"></div>
      <span style="font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;text-transform:uppercase;font-weight:500;">
        AI-Powered Value Intelligence Platform
      </span>
    </div>

    <div class="fu d2">
      <h1 class="serif" style="font-size:clamp(2.8rem,5.5vw,4.8rem);font-weight:300;
        color:#F0EEE8;line-height:1.05;letter-spacing:-0.5px;">
        Invest with the
      </h1>
      <h1 class="serif" style="font-size:clamp(2.8rem,5.5vw,4.8rem);font-weight:700;
        color:#C9A962;line-height:1.05;letter-spacing:-0.5px;margin-bottom:32px;">
        Wisdom of Masters.
      </h1>
    </div>

    <div class="fu d2" style="width:52px;height:2px;background:#C9A962;margin-bottom:28px;"></div>

    <p class="fu d3" style="font-size:1rem;color:#9A9AA8;line-height:1.9;font-weight:300;
      max-width:580px;margin-bottom:52px;">
      A professional-grade investment intelligence platform built on the enduring
      principles of Warren Buffett and Duan Yongping&nbsp;&mdash;&nbsp;powered by AI to deliver
      institutional-quality analysis across US, HK, and A-share markets.
    </p>

    <!-- stat row -->
    <div class="fu d4" style="display:flex;border:1px solid #1A1A22;">
      <div style="flex:1;padding:18px 20px;border-right:1px solid #1A1A22;text-align:center;">
        <div class="serif" style="font-size:2.1rem;font-weight:600;color:#C9A962;line-height:1;">3</div>
        <div style="font-size:0.62rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;margin-top:6px;">Global Markets</div>
      </div>
      <div style="flex:1;padding:18px 20px;border-right:1px solid #1A1A22;text-align:center;">
        <div class="serif" style="font-size:2.1rem;font-weight:600;color:#C9A962;line-height:1;">35+</div>
        <div style="font-size:0.62rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;margin-top:6px;">Stocks Covered</div>
      </div>
      <div style="flex:1;padding:18px 20px;border-right:1px solid #1A1A22;text-align:center;">
        <div class="serif" style="font-size:2.1rem;font-weight:600;color:#C9A962;line-height:1;">5</div>
        <div style="font-size:0.62rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;margin-top:6px;">MOAT Dimensions</div>
      </div>
      <div style="flex:1;padding:18px 20px;border-right:1px solid #1A1A22;text-align:center;">
        <div class="serif" style="font-size:2.1rem;font-weight:600;color:#C9A962;line-height:1;">100</div>
        <div style="font-size:0.62rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;margin-top:6px;">Point Scoring</div>
      </div>
      <div style="flex:1;padding:18px 20px;text-align:center;">
        <div class="serif" style="font-size:2.1rem;font-weight:600;color:#C9A962;line-height:1;">AI</div>
        <div style="font-size:0.62rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;margin-top:6px;">Deep Research</div>
      </div>
    </div>

  </div>
</div>
""", height=560)


# ══════════════════════════════════════════════════════════════════════════════
# 02  BUFFETT INDICATOR
# ══════════════════════════════════════════════════════════════════════════════
def _gauge(ratio):
    if ratio <= 70:    pos = ratio / 70 * 35
    elif ratio <= 90:  pos = 35 + (ratio - 70) / 20 * 10
    elif ratio <= 120: pos = 45 + (ratio - 90) / 30 * 15
    elif ratio <= 150: pos = 60 + (ratio - 120) / 30 * 15
    else:              pos = min(75 + (ratio - 150) / 50 * 25, 100)
    return (
        '<div style="height:4px;background:#1A1A22;border-radius:2px;margin:14px 0 6px;'
        'position:relative;display:flex;overflow:hidden;">'
        '<div style="width:35%;height:100%;background:#3ECF8E;"></div>'
        '<div style="width:10%;height:100%;background:#60A5FA;"></div>'
        '<div style="width:15%;height:100%;background:#C9A962;"></div>'
        '<div style="width:15%;height:100%;background:#F5A623;"></div>'
        '<div style="width:25%;height:100%;background:#EF4444;"></div>'
        '<div style="position:absolute;top:-3px;left:' + str(round(pos, 1)) + '%;'
        'width:2px;height:10px;background:#FFF;border-radius:1px;transform:translateX(-50%);"></div>'
        '</div>'
        '<div style="display:flex;justify-content:space-between;font-size:0.62rem;color:#5A5A66;">'
        '<span>0</span><span>70%</span><span>90%</span><span>120%</span><span>150%</span><span>200%+</span>'
        '</div>'
    )

def _bi_card(d):
    c = d.get("color", "#C9A962")
    live = d.get("is_live", False)
    bb = "#3ECF8E18" if live else "#1A1A22"
    bc = "#3ECF8E"   if live else "#3A3A4A"
    bt = "LIVE"      if live else "REF"
    return (
        '<div style="background:#0A0A0F;border:1px solid #1A1A22;padding:24px;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">'
        '<span style="font-size:0.9rem;font-weight:600;color:#E8E8F0;letter-spacing:0.3px;">' + d["name"] + '</span>'
        '<span style="font-size:0.62rem;padding:2px 8px;letter-spacing:2px;text-transform:uppercase;'
        'background:' + bb + ';color:' + bc + ';">' + bt + '</span>'
        '</div>'
        '<div class="serif" style="font-size:2.8rem;font-weight:700;line-height:1;'
        'color:' + c + ';margin-bottom:4px;">' + str(d["ratio"]) + '%</div>'
        '<div style="font-size:0.56rem;color:#5A5A66;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;">Market Cap / GDP</div>'
        + _gauge(d["ratio"])
        + '<div style="display:inline-block;font-size:0.68rem;font-weight:600;padding:3px 10px;'
        'background:' + c + '14;color:' + c + ';letter-spacing:1px;margin:10px 0 8px;">' + d.get("label", "") + '</div>'
        '<div style="font-size:0.76rem;color:#9A9AA8;line-height:1.75;">' + d.get("advice", "") + '</div>'
        '</div>'
    )

if bi and all(k in bi for k in ("cn", "us", "hk")):
    _cards = (
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:20px;">'
        + _bi_card(bi["cn"]) + _bi_card(bi["us"]) + _bi_card(bi["hk"])
        + '</div>'
    )
else:
    _cards = '<div style="color:#5A5A66;font-size:0.85rem;padding:20px 0;">Market data loading…</div>'

_html("""
<div style="padding:56px 52px 52px;border-top:1px solid #1A1A22;background:#0A0A0F;">
  <div style="font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;text-transform:uppercase;
    font-weight:500;margin-bottom:10px;">Buffett Indicator</div>
  <h2 class="serif" style="font-size:2.2rem;font-weight:300;color:#E8E8F0;
    margin-bottom:10px;letter-spacing:-0.3px;">Global Market Valuation</h2>
  <p style="font-size:0.85rem;color:#4A4A5A;line-height:1.85;max-width:620px;">
    Buffett Indicator = Total Market Cap ÷ GDP.&nbsp;
    &lt;70% deeply undervalued &middot; 70–90% fair &middot; 90–120% neutral &middot; 120–150% overvalued &middot; &gt;150% danger zone.
  </p>
""" + _cards + "</div>", height=500)


# ══════════════════════════════════════════════════════════════════════════════
# 03  十五五投资主线
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div style="font-size:0.6rem;letter-spacing:1.2px;color:#C9A962;'
    'text-transform:uppercase;font-weight:500;margin:40px 0 20px;'
    'padding-bottom:8px;border-bottom:1px solid #1E1E26;">十五五投资主线</div>',
    unsafe_allow_html=True,
)

_THEMES = [
    {
        "icon": "🤖", "title": "人工智能+",
        "desc": "大模型、算力基础设施、AI应用赋能各行业",
        "stocks": "寒武纪・科大讯飞・中科曙光",
        "policy": "十五五核心战略", "color": "#C9A962",
    },
    {
        "icon": "⚡", "title": "新能源体系",
        "desc": "光伏、储能、新能源汽车，2030年装机占比50%+目标",
        "stocks": "宁德时代・隆基绿能・比亚迪",
        "policy": "十五五核心战略", "color": "#3ECF8E",
    },
    {
        "icon": "🦾", "title": "机器人产业",
        "desc": "工业机器人、人形机器人，\"机器人+\"应用全面扩展",
        "stocks": "汇川技术・埃斯顿・海天精工",
        "policy": "十五五核心战略", "color": "#C9A962",
    },
    {
        "icon": "💊", "title": "生物医药",
        "desc": "创新药、精准医疗、CXO，国家战略性新兴产业",
        "stocks": "百济神州・恒瑞医药・迈瑞医疗",
        "policy": "十五五核心战略", "color": "#7B9E87",
    },
    {
        "icon": "🔬", "title": "半导体国产替代",
        "desc": "芯片设计、制造、设备全链条自主可控",
        "stocks": "中芯国际・北方华创・兆易创新",
        "policy": "十五五核心战略", "color": "#8A6FE8",
    },
    {
        "icon": "✈️", "title": "低空经济",
        "desc": "eVTOL、无人机物流、低空基础设施建设",
        "stocks": "中航西飞・澜起科技",
        "policy": "新兴产业布局", "color": "#5BA4CF",
    },
]

def _theme_card(t):
    return (
        '<div style="background:#0D0D14;border:1px solid #1E1E2A;border-top:2px solid {color};'
        'border-radius:4px;padding:20px;height:180px;position:relative;">'
        '<div style="font-size:1.5rem;margin-bottom:8px;">{icon}</div>'
        '<div style="font-size:0.85rem;font-weight:600;color:#E8E8F0;margin-bottom:6px;">{title}</div>'
        '<div style="font-size:0.65rem;color:#5A5A66;line-height:1.5;margin-bottom:8px;">{desc}</div>'
        '<div style="font-size:0.6rem;color:#C9A962;margin-bottom:4px;">{stocks}</div>'
        '<div style="font-size:0.55rem;color:#5A5A66;letter-spacing:1px;position:absolute;'
        'bottom:12px;left:20px;">{policy}</div>'
        '</div>'
    ).format(**t)

_row1 = st.columns(3)
_row2 = st.columns(3)
for _i, _col in enumerate(_row1):
    with _col:
        st.markdown(_theme_card(_THEMES[_i]), unsafe_allow_html=True)
for _i, _col in enumerate(_row2):
    with _col:
        st.markdown(_theme_card(_THEMES[_i + 3]), unsafe_allow_html=True)

st.markdown(
    '<div style="font-size:0.68rem;color:#5A5A66;text-align:center;margin:16px 0 32px;">'
    '以上主题基于十五五规划（2026-2030）核心方向 · 点击左侧「分析」页深度研究个股'
    '</div>',
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# 04  THE MASTERS
# ══════════════════════════════════════════════════════════════════════════════
_html(f"""
<style>
.master{{flex:1;padding:44px 40px;border:1px solid #1A1A22;position:relative;overflow:hidden;background:#0A0A0F;}}
.master::before{{content:'';position:absolute;top:0;left:0;width:3px;height:100%;
  background:linear-gradient(180deg,transparent,var(--a) 25%,var(--a) 75%,transparent);}}
.master-tag{{font-size:0.62rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--a);margin-bottom:20px;font-weight:500;}}
.master-name{{font-family:'Cormorant Garamond',serif;font-size:2.4rem;font-weight:300;
  color:#F0EEE8;line-height:1.1;margin-bottom:4px;}}
.master-title{{font-size:0.6rem;letter-spacing:1px;color:#4A4A5A;text-transform:uppercase;margin-bottom:24px;}}
.master-rule{{width:40px;height:1px;background:var(--a);margin-bottom:24px;opacity:0.6;}}
.master-meta{{display:flex;gap:24px;margin-bottom:28px;}}
.meta-item{{}}
.meta-val{{font-family:'Cormorant Garamond',serif;font-size:1.5rem;font-weight:600;color:var(--a);line-height:1;}}
.meta-lbl{{font-size:0.62rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;margin-top:4px;}}
.principles{{margin-bottom:28px;}}
.p-item{{display:flex;align-items:flex-start;gap:10px;margin-bottom:12px;}}
.p-dot{{width:5px;height:5px;background:var(--a);border-radius:50%;margin-top:6px;flex-shrink:0;opacity:0.7;}}
.p-text{{font-size:0.8rem;color:#7A7A88;line-height:1.6;}}
.sig-quote{{border-left:2px solid var(--a);padding-left:20px;margin-top:4px;}}
.sig-text{{font-family:'Cormorant Garamond',serif;font-size:1.1rem;font-weight:300;
  font-style:italic;color:#D0D0DC;line-height:1.75;}}
.sig-attr{{font-size:0.5rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;margin-top:10px;}}
</style>

<div style="padding:60px 52px;border-top:1px solid #1A1A22;">
  <div style="font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;text-transform:uppercase;
    font-weight:500;margin-bottom:10px;">The Masters</div>
  <h2 class="serif" style="font-size:2.2rem;font-weight:300;color:#E8E8F0;
    margin-bottom:44px;letter-spacing:-0.3px;">
    The Minds Behind the Method
  </h2>

  <div style="display:flex;gap:12px;">

    <!-- Buffett -->
    <div class="master" style="--a:#C9A962;">
      <div class="master-tag">Oracle of Omaha</div>
      <div class="master-name">Warren Buffett</div>
      <div class="master-title">Chairman &amp; CEO · Berkshire Hathaway</div>
      <div class="master-rule"></div>
      <div class="master-meta">
        <div class="meta-item">
          <div class="meta-val">~20%</div>
          <div class="meta-lbl">Annual Return</div>
        </div>
        <div class="meta-item">
          <div class="meta-val">58yr</div>
          <div class="meta-lbl">Track Record</div>
        </div>
        <div class="meta-item">
          <div class="meta-val">$1T+</div>
          <div class="meta-lbl">Berkshire AUM</div>
        </div>
      </div>
      <div class="principles">
        <div class="p-item"><div class="p-dot"></div><div class="p-text">护城河优先 — 只买具有持久竞争优势的公司</div></div>
        <div class="p-item"><div class="p-dot"></div><div class="p-text">安全边际 — 以显著低于内在价值的价格买入</div></div>
        <div class="p-item"><div class="p-dot"></div><div class="p-text">能力圈 — 只投资自己真正理解的生意</div></div>
        <div class="p-item"><div class="p-dot"></div><div class="p-text">长期持有 — 最好的持有期是永远</div></div>
      </div>
      <div class="sig-quote">
        <div class="sig-text">&ldquo;{buffett_q}&rdquo;</div>
        <div class="sig-attr">— Warren Buffett</div>
      </div>
    </div>

    <!-- 段永平 -->
    <div class="master" style="--a:#9A9AAA;">
      <div class="master-tag">步步高创始人</div>
      <div class="master-name">段永平</div>
      <div class="master-title">Founder · 步步高 / OPPO / vivo</div>
      <div class="master-rule"></div>
      <div class="master-meta">
        <div class="meta-item">
          <div class="meta-val" style="color:#9A9AAA;">本分</div>
          <div class="meta-lbl">Core Philosophy</div>
        </div>
        <div class="meta-item">
          <div class="meta-val" style="color:#9A9AAA;">AAPL</div>
          <div class="meta-lbl">Top Holding</div>
        </div>
        <div class="meta-item">
          <div class="meta-val" style="color:#9A9AAA;">价值</div>
          <div class="meta-lbl">Investment Style</div>
        </div>
      </div>
      <div class="principles">
        <div class="p-item"><div class="p-dot" style="background:#9A9AAA;"></div><div class="p-text">本分 — 做对的事情，而不仅仅是把事情做对</div></div>
        <div class="p-item"><div class="p-dot" style="background:#9A9AAA;"></div><div class="p-text">Stop Doing List — 知道什么不该做，比知道做什么更重要</div></div>
        <div class="p-item"><div class="p-dot" style="background:#9A9AAA;"></div><div class="p-text">不懂不做 — 这四个字价值万亿，是护城河的护城河</div></div>
        <div class="p-item"><div class="p-dot" style="background:#9A9AAA;"></div><div class="p-text">企业文化 — 是最难被复制、最持久的竞争优势</div></div>
      </div>
      <div class="sig-quote" style="border-color:#4A4A5A;">
        <div class="sig-text">&ldquo;{duan_q}&rdquo;</div>
        <div class="sig-attr">— 段永平 · Duan Yongping</div>
      </div>
    </div>

  </div>
</div>
""", height=560)


# ══════════════════════════════════════════════════════════════════════════════
# 04  PHILOSOPHY WALL — auto-scrolling quote marquee
# ══════════════════════════════════════════════════════════════════════════════

# Build quote cards HTML (gold for Buffett, silver for 段永平)
def _qcard(text, author, attr, gold=True):
    acc = "#C9A962" if gold else "#7A7A8A"
    return (
        f'<div class="qcard" style="--acc:{acc};">'
        f'<div class="qmark">&ldquo;</div>'
        f'<div class="qtext">{text}</div>'
        f'<div class="qby">&#8212; {author}<span class="qattr"> / {attr}</span></div>'
        f'</div>'
    )

_cards_a = ""
for b, d in zip(_bq4, _dq4):
    _cards_a += _qcard(b, "Warren Buffett",     "Berkshire Hathaway", gold=True)
    _cards_a += _qcard(d, "段永平 · Duan Yongping", "步步高创始人",     gold=False)

_cards_ab = _cards_a + _cards_a  # duplicate for seamless loop

_html(f"""
<style>
.wall{{padding:48px 52px;border-top:1px solid #1A1A22;background:#0A0A0F;overflow:hidden;}}
.wall-hdr{{font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;text-transform:uppercase;
  font-weight:500;margin-bottom:32px;}}
.mq-outer{{overflow:hidden;
  -webkit-mask-image:linear-gradient(90deg,transparent 0%,#08080E 5%,#08080E 95%,transparent 100%);
  mask-image:linear-gradient(90deg,transparent 0%,#08080E 5%,#08080E 95%,transparent 100%);}}
.mq-track{{display:inline-flex;gap:2px;
  animation:march 55s linear infinite;}}
.mq-track:hover{{animation-play-state:paused;}}
@keyframes march{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}
.qcard{{
  width:320px;flex-shrink:0;
  padding:28px 28px 24px;
  border:1px solid #1A1A22;
  border-top:2px solid var(--acc);
  background:#0A0A0F;
  margin-right:10px;
}}
.qmark{{font-family:'Cormorant Garamond',serif;font-size:2.8rem;font-weight:700;
  color:var(--acc);line-height:1;margin-bottom:10px;opacity:0.5;}}
.qtext{{font-family:'Cormorant Garamond',serif;font-size:1rem;font-weight:300;
  font-style:italic;color:#C8C8D8;line-height:1.7;margin-bottom:14px;}}
.qby{{font-size:0.5rem;letter-spacing:1px;color:#5A5A66;text-transform:uppercase;}}
.qattr{{color:#5A5A66;}}
</style>

<div class="wall">
  <div class="wall-hdr">The Philosophy</div>
  <div class="mq-outer">
    <div class="mq-track">{_cards_ab}</div>
  </div>
</div>
""", height=270)


# ══════════════════════════════════════════════════════════════════════════════
# 05  THE FIVE LAWS
# ══════════════════════════════════════════════════════════════════════════════
_html("""
<style>
.laws-wrap{padding:64px 52px;border-top:1px solid #1A1A22;background:#0A0A0F;}
.laws-title-sec{font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;text-transform:uppercase;
  font-weight:500;margin-bottom:10px;}
.laws-h{font-family:'Cormorant Garamond',serif;font-size:2.2rem;font-weight:300;
  color:#E8E8F0;letter-spacing:-0.3px;margin-bottom:48px;}

.law{display:grid;grid-template-columns:72px 1fr 2fr;gap:20px 32px;
  align-items:start;padding:28px 0;border-bottom:1px solid #111118;
  cursor:default;transition:background 0.3s ease,padding-left 0.3s ease;}
.law:first-of-type{border-top:1px solid #111118;}
.law:hover{background:rgba(201,169,98,0.03);padding-left:12px;}

.law-num{font-family:'Cormorant Garamond',serif;font-size:3rem;font-weight:300;
  color:#1A1A22;line-height:1;transition:color 0.35s ease;}
.law:hover .law-num{color:#C9A962;}

.law-head{padding-top:6px;}
.law-name{font-size:0.95rem;font-weight:600;color:#E8E8F0;letter-spacing:0.3px;margin-bottom:6px;}
.law-sub{font-size:0.7rem;letter-spacing:2px;color:#C9A962;text-transform:uppercase;opacity:0.6;}

.law-body{padding-top:6px;}
.law-desc{font-size:0.82rem;color:#5A5A66;line-height:1.8;margin-bottom:8px;}
.law-expand{font-size:0.78rem;color:#3A3A48;line-height:1.75;
  max-height:0;overflow:hidden;transition:max-height 0.4s ease,color 0.3s ease;}
.law:hover .law-expand{max-height:80px;color:#9A9AA8;}
</style>

<div class="laws-wrap">
  <div class="laws-title-sec">Value Investing</div>
  <div class="laws-h">The Five Laws of the Masters</div>

  <div class="law">
    <div class="law-num">I</div>
    <div class="law-head">
      <div class="law-name">护城河至上</div>
      <div class="law-sub">Moat First</div>
    </div>
    <div class="law-body">
      <div class="law-desc">只买有城堡的公司——没有持久竞争优势的企业，价格再便宜也不值得持有。</div>
      <div class="law-expand">护城河的五种形式：品牌定价权、转换成本、网络效应、成本优势、规模经济。护城河不是静态的，需要每年重新评估其是否还在加宽。检验标准：十年后这家公司还在行业顶端吗？</div>
    </div>
  </div>

  <div class="law">
    <div class="law-num">II</div>
    <div class="law-head">
      <div class="law-name">安全边际</div>
      <div class="law-sub">Margin of Safety</div>
    </div>
    <div class="law-body">
      <div class="law-desc">永远用七折的价格买价值一元的东西。内在价值不是精确的数字，是一种谦逊的估算。</div>
      <div class="law-expand">安全边际不只是财务概念——它是对人类判断力局限性的承认。巴菲特要求至少25%的折扣，以应对对未来的错误预判。买入价格就是你最终的安全网。</div>
    </div>
  </div>

  <div class="law">
    <div class="law-num">III</div>
    <div class="law-head">
      <div class="law-name">能力圈即边界</div>
      <div class="law-sub">Circle of Competence</div>
    </div>
    <div class="law-body">
      <div class="law-desc">不懂的不碰，无论多便宜、多诱人。段永平说：这四个字价值万亿。</div>
      <div class="law-expand">能力圈的大小不重要，重要的是你知道自己圈子的边界在哪里。大多数投资者的失败，都源于在不理解的领域自作聪明。能力圈的扩大需要时间，而不是勇气。</div>
    </div>
  </div>

  <div class="law">
    <div class="law-num">IV</div>
    <div class="law-head">
      <div class="law-name">时间是朋友</div>
      <div class="law-sub">Time in Market</div>
    </div>
    <div class="law-body">
      <div class="law-desc">优秀企业的最佳持有期是永远。复利是世界第八大奇迹，时间是它唯一的必要条件。</div>
      <div class="law-expand">一个每年稳定产生15% ROE的企业，持有30年会带来66倍回报。频繁交易是复利最大的敌人。巴菲特买入可口可乐后持有超过35年，期间无数人劝他卖掉。</div>
    </div>
  </div>

  <div class="law">
    <div class="law-num">V</div>
    <div class="law-head">
      <div class="law-name">市场是仆人</div>
      <div class="law-sub">Mr. Market</div>
    </div>
    <div class="law-body">
      <div class="law-desc">利用市场先生的情绪，而不是服从它。别人恐惧时贪婪，别人贪婪时恐惧。</div>
      <div class="law-expand">市场短期是投票机，长期是称重机。价格的波动与公司的内在价值完全无关。真正的投资者把市场的极端情绪视为礼物：熊市是打折出售优质资产的时机，牛市是以好价格出售的时机。</div>
    </div>
  </div>

</div>
""", height=620)


# ══════════════════════════════════════════════════════════════════════════════
# 06  CAPABILITIES — big card + 2×2 grid
# ══════════════════════════════════════════════════════════════════════════════
_html("""
<style>
.caps-wrap{padding:64px 52px;border-top:1px solid #1A1A22;background:#0A0A0F;}
.caps-label{font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;text-transform:uppercase;
  font-weight:500;margin-bottom:10px;}
.caps-h{font-family:'Cormorant Garamond',serif;font-size:2.2rem;font-weight:300;
  color:#E8E8F0;letter-spacing:-0.3px;margin-bottom:40px;}
.caps-grid{display:grid;grid-template-columns:2fr 1fr 1fr;grid-template-rows:auto auto;
  gap:1px;background:#1A1A22;}
.cap{background:#0A0A0F;padding:28px 26px;position:relative;overflow:hidden;
  transition:background 0.3s ease;}
.cap:hover{background:#07070D;}
.cap::after{content:'';position:absolute;bottom:0;left:0;width:0;height:1px;
  background:linear-gradient(90deg,#C9A962,transparent);
  transition:width 0.4s ease;}
.cap:hover::after{width:60%;}
.cap-big{grid-row:1/3;border-right:none;}
.cap-num{font-size:0.62rem;letter-spacing:1px;color:#C9A962;text-transform:uppercase;
  margin-bottom:14px;font-weight:600;}
.cap-title{font-size:0.95rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;letter-spacing:0.3px;}
.cap-desc{font-size:0.78rem;color:#5A5A66;line-height:1.8;}
.cap-big .cap-title{font-size:1.2rem;margin-bottom:14px;}
.cap-big .cap-desc{font-size:0.85rem;}
.cap-big .cap-icon{font-family:'Cormorant Garamond',serif;font-size:4rem;font-weight:300;
  color:#1A1A22;line-height:1;margin-bottom:20px;}
</style>

<div class="caps-wrap">
  <div class="caps-label">Our Capabilities</div>
  <div class="caps-h">Institutional-Grade Analytics, <em style="font-family:'Cormorant Garamond',serif;font-weight:300;">Reimagined</em></div>

  <div class="caps-grid">

    <!-- Big card: MOAT -->
    <div class="cap cap-big">
      <div class="cap-num">01 — Flagship</div>
      <div class="cap-icon">M</div>
      <div class="cap-title">MOAT Scoring Engine</div>
      <div class="cap-desc">
        五维度护城河评分：盈利质量、护城河深度、财务堡垒、成长确定性、市场先生机会。
        每维度0–20分，合计0–100分，一键输出投资建议。
        <br><br>
        基于巴菲特年度股东信核心标准构建，结合段永平"本分"理念校准决策边界。
        不仅给出数字，还给出你能理解的理由。
      </div>
    </div>

    <!-- Small cards -->
    <div class="cap">
      <div class="cap-num">02</div>
      <div class="cap-title">Valuation Intelligence</div>
      <div class="cap-desc">PE · PB · FCF Yield 交叉验证，25% 安全边际原则驱动 Buy / Hold / Avoid 三级评级。</div>
    </div>

    <div class="cap">
      <div class="cap-num">03</div>
      <div class="cap-title">AI Research Reports</div>
      <div class="cap-desc">一键生成巴菲特风格深度研报，含多空理由、AI 置信度评分及明确投资结论。</div>
    </div>

    <div class="cap">
      <div class="cap-num">04</div>
      <div class="cap-title">Technical Context</div>
      <div class="cap-desc">MA · RSI · 布林带不作为交易信号，而作为价值投资者识别买入时机的辅助工具。</div>
    </div>

    <div class="cap">
      <div class="cap-num">05</div>
      <div class="cap-title">AI Investment Advisor</div>
      <div class="cap-desc">具备完整投资哲学上下文的对话 AI，可解答估值、宏观及个股任何问题。</div>
    </div>

  </div>
</div>
""", height=580)


# ══════════════════════════════════════════════════════════════════════════════
# 07  WISDOM IN NUMBERS
# ══════════════════════════════════════════════════════════════════════════════
_html("""
<div style="padding:52px;border-top:1px solid #1A1A22;background:#0A0A0F;">
  <div style="font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;
    text-transform:uppercase;font-weight:500;margin-bottom:36px;">Wisdom in Numbers</div>

  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#1A1A22;">

    <div style="background:#0A0A0F;padding:28px 26px;">
      <div class="serif" style="font-size:2.8rem;font-weight:300;color:#C9A962;line-height:1;margin-bottom:10px;">10yr</div>
      <div style="font-size:0.75rem;color:#D0D0D8;font-weight:500;margin-bottom:8px;">持有门槛</div>
      <div style="font-size:0.72rem;color:#4A4A5A;line-height:1.75;">
        "如果你不愿意持有一只股票十年，那就连十分钟也不要持有。"
      </div>
    </div>

    <div style="background:#0A0A0F;padding:28px 26px;">
      <div class="serif" style="font-size:2.8rem;font-weight:300;color:#C9A962;line-height:1;margin-bottom:10px;">≥25%</div>
      <div style="font-size:0.75rem;color:#D0D0D8;font-weight:500;margin-bottom:8px;">安全边际</div>
      <div style="font-size:0.72rem;color:#4A4A5A;line-height:1.75;">
        买入价须至少低于内在价值25%，为判断失误和不确定性留下缓冲空间。
      </div>
    </div>

    <div style="background:#0A0A0F;padding:28px 26px;">
      <div class="serif" style="font-size:2.8rem;font-weight:300;color:#C9A962;line-height:1;margin-bottom:10px;">15%+</div>
      <div style="font-size:0.75rem;color:#D0D0D8;font-weight:500;margin-bottom:8px;">ROE 基准</div>
      <div style="font-size:0.72rem;color:#4A4A5A;line-height:1.75;">
        连续十年 ROE&gt;15% 是护城河真实存在的最有力证据，不可替代。
      </div>
    </div>

    <div style="background:#0A0A0F;padding:28px 26px;">
      <div class="serif" style="font-size:2.8rem;font-weight:300;color:#C9A962;line-height:1;margin-bottom:10px;">#1</div>
      <div style="font-size:0.75rem;color:#D0D0D8;font-weight:500;margin-bottom:8px;">第一法则</div>
      <div style="font-size:0.72rem;color:#4A4A5A;line-height:1.75;">
        投资第一条规则：永远不要亏钱。第二条规则：永远不要忘记第一条。
      </div>
    </div>

  </div>
</div>
""", height=240)


# ══════════════════════════════════════════════════════════════════════════════
# 08  HOW IT WORKS
# ══════════════════════════════════════════════════════════════════════════════
_html("""
<div style="padding:64px 52px;border-top:1px solid #1A1A22;background:#0A0A0F;">
  <div style="font-size:0.66rem;letter-spacing:1.5px;color:#C9A962;text-transform:uppercase;
    font-weight:500;margin-bottom:10px;">Process</div>
  <h2 class="serif" style="font-size:2.2rem;font-weight:300;color:#E8E8F0;
    margin-bottom:52px;letter-spacing:-0.3px;">Three Steps to Conviction</h2>

  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:40px;position:relative;">

    <!-- connecting line -->
    <div style="position:absolute;top:28px;left:calc(33.33% - 16px);right:calc(33.33% - 16px);
      height:1px;background:linear-gradient(90deg,#1A1A22,#C9A96240,#1A1A22);"></div>

    <div>
      <div class="serif" style="font-size:4rem;font-weight:700;color:#1A1A22;line-height:1;margin-bottom:16px;">01</div>
      <div style="width:32px;height:1px;background:#C9A962;margin-bottom:16px;opacity:0.7;"></div>
      <div style="font-size:0.9rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;letter-spacing:0.3px;">
        Select a Stock
      </div>
      <div style="font-size:0.78rem;color:#5A5A66;line-height:1.8;">
        从美股、港股、A股三大市场中选择标的。支持自定义关注列表，可添加任意 Ticker。
        系统会自动识别市场来源并拉取实时数据。
      </div>
    </div>

    <div>
      <div class="serif" style="font-size:4rem;font-weight:700;color:#1A1A22;line-height:1;margin-bottom:16px;">02</div>
      <div style="width:32px;height:1px;background:#C9A962;margin-bottom:16px;opacity:0.7;"></div>
      <div style="font-size:0.9rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;letter-spacing:0.3px;">
        Run the Analysis
      </div>
      <div style="font-size:0.78rem;color:#5A5A66;line-height:1.8;">
        系统实时抓取财务数据，运行五维度护城河评分引擎，输出 ROE · 利润率 · 负债率
        等核心指标，以及完整的技术分析图表。
      </div>
    </div>

    <div>
      <div class="serif" style="font-size:4rem;font-weight:700;color:#1A1A22;line-height:1;margin-bottom:16px;">03</div>
      <div style="width:32px;height:1px;background:#C9A962;margin-bottom:16px;opacity:0.7;"></div>
      <div style="font-size:0.9rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;letter-spacing:0.3px;">
        Get AI Conviction
      </div>
      <div style="font-size:0.78rem;color:#5A5A66;line-height:1.8;">
        一键生成巴菲特视角深度研报：多空理由 · 护城河评估 · AI 置信度评分，
        给出明确的 Buy / Hold / Avoid 投资结论。
      </div>
    </div>

  </div>
</div>
""", height=400)


# ══════════════════════════════════════════════════════════════════════════════
# 09  CLOSING QUOTE — full-width dark feature
# ══════════════════════════════════════════════════════════════════════════════
_html("""
<div style="padding:72px 52px;border-top:1px solid #1A1A22;background:#0A0A0F;
  position:relative;overflow:hidden;">

  <!-- faint grid -->
  <div style="position:absolute;inset:0;pointer-events:none;opacity:0.018;
    background-image:linear-gradient(#C9A962 1px,transparent 1px),
                     linear-gradient(90deg,#C9A962 1px,transparent 1px);
    background-size:64px 64px;"></div>

  <!-- gold left bar -->
  <div style="position:absolute;left:0;top:0;width:3px;height:100%;
    background:linear-gradient(180deg,transparent,#C9A962 30%,#C9A962 70%,transparent);"></div>

  <div style="position:relative;max-width:800px;margin:0 auto;text-align:center;">
    <div style="font-size:0.62rem;letter-spacing:1.5px;color:#C9A962;text-transform:uppercase;
      font-weight:500;margin-bottom:32px;">A Final Thought</div>

    <div class="serif" style="font-size:clamp(1.5rem,3vw,2.2rem);font-weight:300;
      color:#E8E8F0;line-height:1.6;font-style:italic;margin-bottom:28px;">
      &ldquo;投资很简单，但并不容易。<br>
      它需要的不是天赋，而是正确的思维框架；<br>
      不是信息优势，而是情绪的自律。&rdquo;
    </div>

    <div style="width:40px;height:1px;background:#C9A96260;margin:0 auto 20px;"></div>

    <div style="font-size:0.66rem;letter-spacing:1.2px;color:#5A5A66;text-transform:uppercase;">
      The Philosophy of AI Buffett
    </div>
  </div>
</div>
""", height=340)


# ══════════════════════════════════════════════════════════════════════════════
# 10  FOOTER
# ══════════════════════════════════════════════════════════════════════════════
_html("""
<div style="padding:28px 52px;border-top:1px solid #1A1A22;background:#04040A;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div class="serif" style="font-size:0.95rem;font-weight:600;
      color:#C9A962;letter-spacing:1.2px;text-transform:uppercase;">
      AI &middot; BUFFETT
    </div>
    <div style="font-size:0.62rem;color:#1E1E26;letter-spacing:2px;
      text-transform:uppercase;text-align:right;line-height:1.9;">
      For Research &amp; Educational Purposes Only<br>
      Not Financial Advice &middot; Authorized Access Only
    </div>
  </div>
</div>
""", height=88)
