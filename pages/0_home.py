"""Home — Buffett Research · AI-Powered Value Intelligence"""

import random
import streamlit as st
import streamlit.components.v1 as components
from src.ui_theme import get_global_css, COLORS
from src.ai.knowledge_base import BUFFETT_QUOTES, DUAN_YONGPING_QUOTES
from src.data.macro import get_buffett_indicator

st.markdown(get_global_css(), unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def _load_bi():
    try:
        return get_buffett_indicator()
    except Exception:
        return {}


bi = _load_bi()
buffett_q = random.choice(BUFFETT_QUOTES)
duan_q    = random.choice(DUAN_YONGPING_QUOTES)

# ── helpers ──────────────────────────────────────────────────────────────────
def _html(body, height=400):
    page = """<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;0,700;1,300;1,400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{background:#06060A;font-family:'Inter',-apple-system,sans-serif;color:#E8E8F0;-webkit-font-smoothing:antialiased;}
.serif{font-family:'Cormorant Garamond','Georgia',serif;}
</style></head><body>""" + body + "</body></html>"
    components.html(page, height=height, scrolling=False)


# ═════════════════════════════════════════════════════════════════════════════
# 01 HERO
# ═════════════════════════════════════════════════════════════════════════════
_html("""
<div style="position:relative;overflow:hidden;padding:80px 48px 72px;background:#06060A;">

  <!-- geometric accent grid -->
  <div style="position:absolute;inset:0;opacity:0.03;
    background-image:linear-gradient(#C9A962 1px,transparent 1px),
                     linear-gradient(90deg,#C9A962 1px,transparent 1px);
    background-size:80px 80px;"></div>

  <!-- gold vertical bar -->
  <div style="position:absolute;left:0;top:0;width:3px;height:100%;
    background:linear-gradient(180deg,transparent,#C9A962 30%,#C9A962 70%,transparent);"></div>

  <div style="position:relative;max-width:860px;">

    <div style="font-size:0.6rem;letter-spacing:6px;color:#C9A962;
      text-transform:uppercase;font-weight:500;margin-bottom:32px;
      font-family:'Inter',sans-serif;">
      AI-Powered Value Intelligence Platform
    </div>

    <h1 class="serif" style="font-size:clamp(3rem,6vw,5rem);font-weight:300;
      color:#F0EEE8;line-height:1.05;letter-spacing:-0.5px;margin-bottom:8px;">
      Invest with the
    </h1>
    <h1 class="serif" style="font-size:clamp(3rem,6vw,5rem);font-weight:700;
      color:#C9A962;line-height:1.05;letter-spacing:-0.5px;margin-bottom:36px;">
      Wisdom of Masters.
    </h1>

    <div style="width:56px;height:2px;background:#C9A962;margin-bottom:36px;"></div>

    <p style="font-size:1.05rem;color:#8A8A96;line-height:1.85;font-weight:300;
      max-width:600px;margin-bottom:48px;">
      A professional-grade investment intelligence platform built on the enduring
      principles of Warren Buffett and Duan Yongping — powered by AI to deliver
      institutional-quality analysis across US, HK, and A-share markets.
    </p>

    <!-- stat row -->
    <div style="display:flex;gap:0;border:1px solid #1E1E26;">
      <div style="flex:1;padding:20px 24px;border-right:1px solid #1E1E26;">
        <div class="serif" style="font-size:2rem;font-weight:600;color:#C9A962;line-height:1;">3</div>
        <div style="font-size:0.58rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-top:6px;">Global Markets</div>
      </div>
      <div style="flex:1;padding:20px 24px;border-right:1px solid #1E1E26;">
        <div class="serif" style="font-size:2rem;font-weight:600;color:#C9A962;line-height:1;">35+</div>
        <div style="font-size:0.58rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-top:6px;">Covered Stocks</div>
      </div>
      <div style="flex:1;padding:20px 24px;border-right:1px solid #1E1E26;">
        <div class="serif" style="font-size:2rem;font-weight:600;color:#C9A962;line-height:1;">5</div>
        <div style="font-size:0.58rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-top:6px;">MOAT Dimensions</div>
      </div>
      <div style="flex:1;padding:20px 24px;">
        <div class="serif" style="font-size:2rem;font-weight:600;color:#C9A962;line-height:1;">AI</div>
        <div style="font-size:0.58rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-top:6px;">Deep Analysis</div>
      </div>
    </div>

  </div>
</div>
""", height=520)


# ═════════════════════════════════════════════════════════════════════════════
# 02 BUFFETT INDICATOR — live market valuation
# ═════════════════════════════════════════════════════════════════════════════
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
        '<div style="position:absolute;top:-3px;left:' + str(round(pos,1)) + '%;'
        'width:2px;height:10px;background:#FFF;border-radius:1px;transform:translateX(-50%);"></div>'
        '</div>'
        '<div style="display:flex;justify-content:space-between;'
        'font-size:0.5rem;color:#2A2A36;font-family:Inter,sans-serif;">'
        '<span>0</span><span>70%</span><span>90%</span><span>120%</span><span>150%</span><span>200%+</span>'
        '</div>'
    )

def _bi_card(d):
    c    = d.get("color", "#C9A962")
    live = d.get("is_live", False)
    badge_bg = "#3ECF8E18" if live else "#2A2A36"
    badge_c  = "#3ECF8E"   if live else "#5A5A6A"
    badge_t  = "LIVE"      if live else "REF"
    return (
        '<div style="background:#0C0C12;border:1px solid #1E1E26;padding:24px;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">'
        '<span style="font-size:0.9rem;font-weight:600;color:#E8E8F0;letter-spacing:0.5px;">' + d["name"] + '</span>'
        '<span style="font-size:0.52rem;padding:2px 8px;letter-spacing:2px;text-transform:uppercase;'
        'background:' + badge_bg + ';color:' + badge_c + ';">' + badge_t + '</span>'
        '</div>'
        '<div style="font-family:\'Cormorant Garamond\',serif;font-size:2.8rem;font-weight:700;'
        'line-height:1;color:' + c + ';margin-bottom:4px;">' + str(d["ratio"]) + '%</div>'
        '<div style="font-size:0.62rem;color:#3A3A4A;letter-spacing:2px;text-transform:uppercase;margin-bottom:14px;">Market Cap / GDP</div>'
        + _gauge(d["ratio"])
        + '<div style="display:inline-block;font-size:0.72rem;font-weight:600;padding:3px 10px;'
        'background:' + c + '16;color:' + c + ';letter-spacing:1px;margin:10px 0 8px;">' + d.get("label","") + '</div>'
        '<div style="font-size:0.78rem;color:#7A7A88;line-height:1.7;">' + d.get("advice","") + '</div>'
        '</div>'
    )

if bi and all(k in bi for k in ("cn","us","hk")):
    cards_html = (
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:20px;">'
        + _bi_card(bi["cn"]) + _bi_card(bi["us"]) + _bi_card(bi["hk"])
        + '</div>'
    )
else:
    cards_html = '<div style="color:#5A5A6A;font-size:0.85rem;padding:20px 0;">Market data loading…</div>'

_html("""
<div style="padding:56px 48px 48px;border-top:1px solid #1E1E26;">
  <div style="font-size:0.58rem;letter-spacing:5px;color:#C9A962;text-transform:uppercase;
    font-weight:500;margin-bottom:12px;font-family:'Inter',sans-serif;">Buffett Indicator</div>
  <h2 class="serif" style="font-size:2.2rem;font-weight:300;color:#E8E8F0;
    margin-bottom:12px;letter-spacing:-0.3px;">Global Market Valuation</h2>
  <p style="font-size:0.88rem;color:#5A5A6A;line-height:1.8;max-width:640px;margin-bottom:0;">
    Buffett Indicator = Total Market Cap ÷ GDP. &nbsp;
    &lt;70% deeply undervalued · 70–90% fair · 90–120% neutral · 120–150% overvalued · &gt;150% danger zone.
  </p>
""" + cards_html + "</div>", height=480)


# ═════════════════════════════════════════════════════════════════════════════
# 03 CAPABILITIES
# ═════════════════════════════════════════════════════════════════════════════
_html("""
<div style="padding:56px 48px;background:#08080E;border-top:1px solid #1E1E26;">
  <div style="font-size:0.58rem;letter-spacing:5px;color:#C9A962;text-transform:uppercase;
    font-weight:500;margin-bottom:12px;">Our Capabilities</div>
  <h2 class="serif" style="font-size:2.2rem;font-weight:300;color:#E8E8F0;
    margin-bottom:48px;letter-spacing:-0.3px;">Institutional-Grade Analytics, <em>Reimagined</em></h2>

  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#1E1E26;">

    <div style="background:#06060A;padding:28px 24px;">
      <div style="font-size:0.52rem;letter-spacing:3px;color:#C9A962;text-transform:uppercase;
        margin-bottom:12px;font-weight:600;">01</div>
      <div style="font-size:0.95rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;letter-spacing:0.3px;">MOAT Scoring</div>
      <div style="font-size:0.8rem;color:#6A6A78;line-height:1.75;">
        Five-dimension competitive advantage analysis: ROE consistency, profit margins,
        financial health, growth trajectory, and management quality. Scored 0–100.
      </div>
    </div>

    <div style="background:#06060A;padding:28px 24px;">
      <div style="font-size:0.52rem;letter-spacing:3px;color:#C9A962;text-transform:uppercase;
        margin-bottom:12px;font-weight:600;">02</div>
      <div style="font-size:0.95rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;letter-spacing:0.3px;">Valuation Intelligence</div>
      <div style="font-size:0.8rem;color:#6A6A78;line-height:1.75;">
        PE, PB, free cashflow yield cross-validated against Buffett's 25% margin-of-safety
        principle. Buy, Hold, or Avoid — grounded in numbers.
      </div>
    </div>

    <div style="background:#06060A;padding:28px 24px;">
      <div style="font-size:0.52rem;letter-spacing:3px;color:#C9A962;text-transform:uppercase;
        margin-bottom:12px;font-weight:600;">03</div>
      <div style="font-size:0.95rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;letter-spacing:0.3px;">AI Research Reports</div>
      <div style="font-size:0.8rem;color:#6A6A78;line-height:1.75;">
        One-click AI-generated deep-dive report in the voice of Warren Buffett —
        bull thesis, bear risks, conviction score, and actionable verdict.
      </div>
    </div>

    <div style="background:#06060A;padding:28px 24px;">
      <div style="font-size:0.52rem;letter-spacing:3px;color:#C9A962;text-transform:uppercase;
        margin-bottom:12px;font-weight:600;">04</div>
      <div style="font-size:0.95rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;letter-spacing:0.3px;">Market Sentiment</div>
      <div style="font-size:0.8rem;color:#6A6A78;line-height:1.75;">
        Real-time Fear & Greed index, capital flow heatmaps, and news-driven
        sentiment aggregation across all three markets.
      </div>
    </div>

    <div style="background:#06060A;padding:28px 24px;">
      <div style="font-size:0.52rem;letter-spacing:3px;color:#C9A962;text-transform:uppercase;
        margin-bottom:12px;font-weight:600;">05</div>
      <div style="font-size:0.95rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;letter-spacing:0.3px;">Technical Analysis</div>
      <div style="font-size:0.8rem;color:#6A6A78;line-height:1.75;">
        MA, RSI, Bollinger Bands — presented not as signals but as context for the
        long-term investor to identify entry opportunities with precision.
      </div>
    </div>

    <div style="background:#06060A;padding:28px 24px;">
      <div style="font-size:0.52rem;letter-spacing:3px;color:#C9A962;text-transform:uppercase;
        margin-bottom:12px;font-weight:600;">06</div>
      <div style="font-size:0.95rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;letter-spacing:0.3px;">AI Investment Advisor</div>
      <div style="font-size:0.8rem;color:#6A6A78;line-height:1.75;">
        Conversational AI advisor that understands your portfolio context.
        Ask anything — from valuation questions to macro interpretation.
      </div>
    </div>

  </div>
</div>
""", height=560)


# ═════════════════════════════════════════════════════════════════════════════
# 04 PHILOSOPHY QUOTES
# ═════════════════════════════════════════════════════════════════════════════
_html(f"""
<div style="padding:64px 48px;background:#06060A;border-top:1px solid #1E1E26;">
  <div style="font-size:0.58rem;letter-spacing:5px;color:#C9A962;text-transform:uppercase;
    font-weight:500;margin-bottom:48px;">The Philosophy</div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:48px;">

    <div style="border-left:2px solid #C9A962;padding-left:28px;">
      <div class="serif" style="font-size:1.25rem;font-weight:300;color:#D8D8E8;
        line-height:1.8;font-style:italic;margin-bottom:20px;">
        &ldquo;{buffett_q}&rdquo;
      </div>
      <div style="font-size:0.6rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;
        font-weight:500;">Warren Buffett
        <span style="color:#2A2A36;margin:0 8px;">/</span>
        <span style="color:#3A3A4A;">Berkshire Hathaway</span>
      </div>
    </div>

    <div style="border-left:2px solid #3A3A4A;padding-left:28px;">
      <div class="serif" style="font-size:1.25rem;font-weight:300;color:#D8D8E8;
        line-height:1.8;font-style:italic;margin-bottom:20px;">
        &ldquo;{duan_q}&rdquo;
      </div>
      <div style="font-size:0.6rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;
        font-weight:500;">段永平 · Duan Yongping
        <span style="color:#2A2A36;margin:0 8px;">/</span>
        <span style="color:#3A3A4A;">步步高创始人</span>
      </div>
    </div>

  </div>
</div>
""", height=320)


# ═════════════════════════════════════════════════════════════════════════════
# 05 HOW IT WORKS
# ═════════════════════════════════════════════════════════════════════════════
_html("""
<div style="padding:56px 48px;background:#08080E;border-top:1px solid #1E1E26;">
  <div style="font-size:0.58rem;letter-spacing:5px;color:#C9A962;text-transform:uppercase;
    font-weight:500;margin-bottom:12px;">Process</div>
  <h2 class="serif" style="font-size:2.2rem;font-weight:300;color:#E8E8F0;
    margin-bottom:48px;letter-spacing:-0.3px;">Three Steps to Professional Analysis</h2>

  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:32px;">

    <div>
      <div style="font-family:'Cormorant Garamond',serif;font-size:3.5rem;font-weight:700;
        color:#1E1E26;line-height:1;margin-bottom:20px;">01</div>
      <div style="width:32px;height:1px;background:#C9A962;margin-bottom:16px;"></div>
      <div style="font-size:0.88rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;
        letter-spacing:0.5px;">Select a Stock</div>
      <div style="font-size:0.8rem;color:#5A5A6A;line-height:1.75;">
        Choose from your watchlist across US, HK, and A-share markets. Add any ticker globally.
      </div>
    </div>

    <div>
      <div style="font-family:'Cormorant Garamond',serif;font-size:3.5rem;font-weight:700;
        color:#1E1E26;line-height:1;margin-bottom:20px;">02</div>
      <div style="width:32px;height:1px;background:#C9A962;margin-bottom:16px;"></div>
      <div style="font-size:0.88rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;
        letter-spacing:0.5px;">Run the Analysis</div>
      <div style="font-size:0.8rem;color:#5A5A6A;line-height:1.75;">
        The system fetches live data and runs the full MOAT scoring engine instantly.
      </div>
    </div>

    <div>
      <div style="font-family:'Cormorant Garamond',serif;font-size:3.5rem;font-weight:700;
        color:#1E1E26;line-height:1;margin-bottom:20px;">03</div>
      <div style="width:32px;height:1px;background:#C9A962;margin-bottom:16px;"></div>
      <div style="font-size:0.88rem;font-weight:600;color:#E8E8F0;margin-bottom:10px;
        letter-spacing:0.5px;">Get the AI Report</div>
      <div style="font-size:0.8rem;color:#5A5A6A;line-height:1.75;">
        One click generates a Buffett-style deep research report with a clear Buy/Hold/Avoid verdict.
      </div>
    </div>

  </div>
</div>
""", height=360)


# ═════════════════════════════════════════════════════════════════════════════
# 06 FOOTER / DISCLAIMER
# ═════════════════════════════════════════════════════════════════════════════
_html("""
<div style="padding:32px 48px;border-top:1px solid #1E1E26;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="font-family:'Cormorant Garamond',serif;font-size:1rem;font-weight:600;
      color:#C9A962;letter-spacing:4px;text-transform:uppercase;">
      BUFFETT · RESEARCH
    </div>
    <div style="font-size:0.52rem;color:#2A2A36;letter-spacing:2px;text-transform:uppercase;text-align:right;">
      For Research &amp; Educational Purposes Only<br>
      Not Financial Advice · Authorized Access Only
    </div>
  </div>
</div>
""", height=80)
