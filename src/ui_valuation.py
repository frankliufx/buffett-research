"""估值决策中枢 — 视觉呈现组件

黑金风格，Blackstone 品质，用户一眼得出结论。
所有渲染函数返回完整 HTML 字符串，配合 streamlit.components.v1.html() 使用。
"""


def _fmt_price(val, currency="$"):
    """格式化价格显示"""
    if val is None:
        return "--"
    if abs(val) >= 10000:
        return "{}{:,.0f}".format(currency, val)
    if abs(val) >= 100:
        return "{}{:,.1f}".format(currency, val)
    return "{}{:,.2f}".format(currency, val)


def _verdict_color(verdict: str) -> str:
    mapping = {
        "强烈买入": "#00C853",
        "买入": "#69F0AE",
        "持有观望": "#C9A962",
        "谨慎持有": "#FF9800",
        "考虑减持": "#FF5722",
        "回避": "#F44336",
        "数据不足": "#5A5A6A",
    }
    return mapping.get(verdict, "#C9A962")


def _confidence_dots(confidence: str) -> str:
    mapping = {"高": 3, "中": 2, "低": 1}
    n = mapping.get(confidence, 1)
    on = '<span class="conf-dot on"></span>' * n
    off = '<span class="conf-dot"></span>' * (3 - n)
    return on + off


def render_valuation_verdict(dcf: dict, symbol: str, name: str, currency: str = "$") -> str:
    """决策横幅 — 最顶部、最显眼"""
    if not dcf or dcf.get("method") == "insufficient":
        missing = ", ".join(dcf.get("missing_fields", [])) if dcf else "全部"
        return _render_insufficient(symbol, name, missing)

    verdict = dcf["verdict"]
    confidence = dcf["confidence"]
    iv = dcf["intrinsic_value"]
    sm = dcf["safety_margin_pct"]
    price = dcf["current_price"]
    stop = dcf["stop_loss"]
    method = dcf["method"]
    vc = _verdict_color(verdict)

    sm_label = "+{:.1f}%".format(sm) if sm >= 0 else "{:.1f}%".format(sm)
    sm_color = "#00C853" if sm >= 15 else ("#C9A962" if sm >= 0 else "#F44336")

    return '''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:0}}

.verdict-card{{
    background:linear-gradient(135deg,#0D0D14 0%,#12121C 100%);
    border:1px solid #1E1E2A;
    border-left:3px solid {vc};
    border-radius:4px;
    padding:28px 32px;
    position:relative;
    overflow:hidden;
}}
.verdict-card::before{{
    content:'';position:absolute;top:0;right:0;width:180px;height:100%;
    background:linear-gradient(90deg,transparent,rgba({vc_rgb},0.03));
    pointer-events:none;
}}

.verdict-top{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px}}

.verdict-main{{}}
.verdict-label{{font-size:0.55rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-bottom:8px}}
.verdict-text{{
    font-family:'Cormorant Garamond',Georgia,serif;
    font-size:2rem;font-weight:700;color:{vc};
    letter-spacing:2px;line-height:1;
}}
.verdict-conf{{display:flex;align-items:center;gap:6px;margin-top:8px}}
.verdict-conf-label{{font-size:0.6rem;letter-spacing:2px;color:#5A5A6A;text-transform:uppercase}}
.conf-dot{{width:8px;height:8px;border-radius:50%;background:#1E1E2A;border:1px solid #2A2A36}}
.conf-dot.on{{background:{vc};border-color:{vc}}}

.verdict-method{{
    font-size:0.5rem;letter-spacing:3px;color:#3A3A4A;
    text-transform:uppercase;padding:4px 10px;
    border:1px solid #1E1E2A;border-radius:2px;
    align-self:flex-start;
}}

.verdict-metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}}
.vm{{}}
.vm-label{{font-size:0.5rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:4px}}
.vm-value{{font-size:1.2rem;font-weight:600;color:#E8E8F0;letter-spacing:0.5px}}
.vm-value.accent{{color:{vc}}}
.vm-value.sm{{color:{sm_color}}}
.vm-sub{{font-size:0.55rem;color:#3A3A4A;margin-top:2px;letter-spacing:1px}}
</style></head><body>
<div class="verdict-card">
    <div class="verdict-top">
        <div class="verdict-main">
            <div class="verdict-label">Intrinsic Value Verdict</div>
            <div class="verdict-text">{verdict}</div>
            <div class="verdict-conf">
                <span class="verdict-conf-label">Confidence</span>
                {conf_dots}
            </div>
        </div>
        <div class="verdict-method">{method}</div>
    </div>
    <div class="verdict-metrics">
        <div class="vm">
            <div class="vm-label">Current Price</div>
            <div class="vm-value">{price_fmt}</div>
        </div>
        <div class="vm">
            <div class="vm-label">Intrinsic Value</div>
            <div class="vm-value accent">{iv_fmt}</div>
        </div>
        <div class="vm">
            <div class="vm-label">Safety Margin</div>
            <div class="vm-value sm">{sm_label}</div>
        </div>
        <div class="vm">
            <div class="vm-label">Stop Loss</div>
            <div class="vm-value">{stop_fmt}</div>
            <div class="vm-sub">Bear &times; 0.9</div>
        </div>
    </div>
</div>
</body></html>'''.format(
        vc=vc,
        vc_rgb=_hex_to_rgb(vc),
        verdict=verdict,
        conf_dots=_confidence_dots(confidence),
        method=method,
        price_fmt=_fmt_price(price, currency),
        iv_fmt=_fmt_price(iv, currency),
        sm_label=sm_label,
        sm_color=sm_color,
        stop_fmt=_fmt_price(stop, currency),
    )


def render_price_spectrum(dcf: dict, quote: dict = None, currency: str = "$") -> str:
    """价格定位轴 — 一眼看出当前价在价值谱系中的位置"""
    if not dcf or dcf.get("method") == "insufficient":
        return ""

    price = dcf["current_price"]
    bear = dcf["scenarios"]["bear"]["intrinsic_value"]
    base = dcf["scenarios"]["base"]["intrinsic_value"]
    bull = dcf["scenarios"]["bull"]["intrinsic_value"]
    stop = dcf["stop_loss"]

    w52_high = quote.get("52w_high") if quote else None
    w52_low = quote.get("52w_low") if quote else None

    # 确定轴的范围
    all_values = [v for v in [price, bear, base, bull, stop, w52_high, w52_low] if v and v > 0]
    if not all_values:
        return ""
    axis_min = min(all_values) * 0.88
    axis_max = max(all_values) * 1.12
    axis_range = axis_max - axis_min
    if axis_range <= 0:
        return ""

    def pct(val):
        return max(2, min(98, (val - axis_min) / axis_range * 100))

    price_pct = pct(price)
    bear_pct = pct(bear)
    base_pct = pct(base)
    bull_pct = pct(bull)
    stop_pct = pct(stop) if stop else None

    # 确定当前价在哪个区间
    if price <= bear:
        zone_desc = "深度低估区间"
        zone_color = "#00C853"
    elif price <= base:
        zone_desc = "合理低估区间"
        zone_color = "#69F0AE"
    elif price <= bull:
        zone_desc = "合理区间"
        zone_color = "#C9A962"
    else:
        zone_desc = "高估区间"
        zone_color = "#F44336"

    # 52 周标记
    w52_markers = ""
    if w52_low and w52_low > axis_min:
        w52_markers += '<div class="w52-mark" style="left:{:.1f}%"><div class="w52-line"></div><div class="w52-label">52W Low<br>{}</div></div>'.format(
            pct(w52_low), _fmt_price(w52_low, currency))
    if w52_high and w52_high < axis_max:
        w52_markers += '<div class="w52-mark" style="left:{:.1f}%"><div class="w52-line"></div><div class="w52-label top">52W High<br>{}</div></div>'.format(
            pct(w52_high), _fmt_price(w52_high, currency))

    return '''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:24px 0 8px}}

.spectrum-card{{
    background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;
    padding:24px 32px 32px;
}}
.spectrum-title{{font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-bottom:20px}}

.spectrum-zone{{
    display:flex;align-items:center;gap:8px;margin-bottom:16px;
}}
.zone-dot{{width:8px;height:8px;border-radius:50%;background:{zone_color}}}
.zone-text{{font-size:0.7rem;letter-spacing:2px;color:{zone_color};text-transform:uppercase;font-weight:600}}

.axis-container{{position:relative;height:80px;margin:16px 0 24px}}

.axis-track{{
    position:absolute;top:32px;left:0;right:0;height:6px;
    border-radius:3px;
    background:linear-gradient(90deg,
        #00C853 0%,
        #00C853 {bear_pct:.1f}%,
        #69F0AE {bear_pct:.1f}%,
        #C9A962 {base_pct:.1f}%,
        #FF9800 {bull_pct:.1f}%,
        #F44336 100%
    );
    opacity:0.7;
}}

/* 价值标记 */
.val-mark{{position:absolute;top:0;transform:translateX(-50%)}}
.val-line{{width:1px;height:20px;margin:0 auto 4px}}
.val-label{{font-size:0.5rem;letter-spacing:1px;color:#5A5A6A;text-align:center;white-space:nowrap}}
.val-price{{font-size:0.65rem;font-weight:600;text-align:center;white-space:nowrap;margin-top:1px}}

.val-mark.bear .val-line{{background:#69F0AE}}
.val-mark.bear .val-price{{color:#69F0AE}}
.val-mark.base .val-line{{background:#C9A962}}
.val-mark.base .val-price{{color:#C9A962}}
.val-mark.bull .val-line{{background:#FF9800}}
.val-mark.bull .val-price{{color:#FF9800}}

/* 当前价标记 — 最醒目 */
.price-mark{{
    position:absolute;top:20px;transform:translateX(-50%);
    z-index:10;text-align:center;
}}
.price-needle{{
    width:3px;height:28px;background:#FFFFFF;margin:0 auto;
    border-radius:2px;
    box-shadow:0 0 8px rgba(255,255,255,0.3);
}}
.price-badge{{
    display:inline-block;margin-top:6px;
    background:#FFFFFF;color:#08080C;
    font-size:0.7rem;font-weight:700;
    padding:3px 10px;border-radius:2px;
    letter-spacing:1px;white-space:nowrap;
}}

/* 52 周标记 */
.w52-mark{{position:absolute;top:44px;transform:translateX(-50%)}}
.w52-line{{width:1px;height:10px;background:#2A2A36;margin:0 auto}}
.w52-label{{font-size:0.45rem;color:#3A3A4A;text-align:center;white-space:nowrap;margin-top:2px;letter-spacing:1px}}
.w52-label.top{{position:absolute;bottom:100%;margin-bottom:2px;left:50%;transform:translateX(-50%)}}

/* 止损标记 */
.stop-mark{{position:absolute;top:24px;transform:translateX(-50%)}}
.stop-line{{width:1px;height:16px;background:#F44336;margin:0 auto;opacity:0.5}}
.stop-label{{font-size:0.45rem;color:#F44336;text-align:center;white-space:nowrap;margin-top:2px;letter-spacing:1px;opacity:0.7}}
</style></head><body>
<div class="spectrum-card">
    <div class="spectrum-title">Price Positioning</div>
    <div class="spectrum-zone">
        <div class="zone-dot"></div>
        <div class="zone-text">{zone_desc}</div>
    </div>
    <div class="axis-container">
        <div class="axis-track"></div>

        <div class="val-mark bear" style="left:{bear_pct:.1f}%">
            <div class="val-line"></div>
            <div class="val-label">Bear</div>
            <div class="val-price">{bear_fmt}</div>
        </div>
        <div class="val-mark base" style="left:{base_pct:.1f}%">
            <div class="val-line"></div>
            <div class="val-label">Fair</div>
            <div class="val-price">{base_fmt}</div>
        </div>
        <div class="val-mark bull" style="left:{bull_pct:.1f}%">
            <div class="val-line"></div>
            <div class="val-label">Bull</div>
            <div class="val-price">{bull_fmt}</div>
        </div>

        <div class="price-mark" style="left:{price_pct:.1f}%">
            <div class="price-needle"></div>
            <div class="price-badge">{price_fmt}</div>
        </div>

        {stop_html}
        {w52_markers}
    </div>
</div>
</body></html>'''.format(
        zone_color=zone_color,
        zone_desc=zone_desc,
        bear_pct=bear_pct,
        base_pct=base_pct,
        bull_pct=bull_pct,
        bear_fmt=_fmt_price(bear, currency),
        base_fmt=_fmt_price(base, currency),
        bull_fmt=_fmt_price(bull, currency),
        price_pct=price_pct,
        price_fmt=_fmt_price(price, currency),
        stop_html='<div class="stop-mark" style="left:{:.1f}%"><div class="stop-line"></div><div class="stop-label">Stop {}</div></div>'.format(
            stop_pct, _fmt_price(stop, currency)) if stop_pct else "",
        w52_markers=w52_markers,
    )


def render_scenario_cards(dcf: dict, currency: str = "$") -> str:
    """三情景内在价值卡"""
    if not dcf or dcf.get("method") == "insufficient":
        return ""

    scenarios = dcf["scenarios"]
    price = dcf["current_price"]

    cards_html = ""
    for key, label, icon, desc in [
        ("bear", "BEAR", "&#x25BD;", "Pessimistic"),
        ("base", "BASE", "&#x25C6;", "Most Likely"),
        ("bull", "BULL", "&#x25B3;", "Optimistic"),
    ]:
        sc = scenarios[key]
        iv = sc["intrinsic_value"]
        sm = sc["safety_margin_pct"]
        gr = sc.get("growth_rate")
        dr = sc.get("discount_rate")
        tpe = sc.get("target_pe")

        sm_color = "#00C853" if sm >= 15 else ("#C9A962" if sm >= 0 else "#F44336")
        border_color = "#C9A962" if key == "base" else "#1E1E2A"
        glow = "box-shadow:0 0 16px rgba(201,169,98,0.08);" if key == "base" else ""

        params_html = ""
        if gr is not None:
            params_html += '<div class="sc-param"><span>Growth</span><span>{:.1f}%</span></div>'.format(gr)
        if dr is not None:
            params_html += '<div class="sc-param"><span>Discount</span><span>{:.1f}%</span></div>'.format(dr)
        if tpe is not None:
            params_html += '<div class="sc-param"><span>Target PE</span><span>{:.1f}x</span></div>'.format(tpe)

        cards_html += '''
        <div class="sc-card" style="border-color:{border_color};{glow}">
            <div class="sc-header">
                <span class="sc-icon">{icon}</span>
                <span class="sc-label">{label}</span>
                <span class="sc-desc">{desc}</span>
            </div>
            <div class="sc-iv">{iv_fmt}</div>
            <div class="sc-sm" style="color:{sm_color}">
                {sm_sign}{sm_abs:.1f}% vs current
            </div>
            <div class="sc-params">{params_html}</div>
        </div>'''.format(
            border_color=border_color,
            glow=glow,
            icon=icon,
            label=label,
            desc=desc,
            iv_fmt=_fmt_price(iv, currency),
            sm_color=sm_color,
            sm_sign="+" if sm >= 0 else "",
            sm_abs=abs(sm),
            params_html=params_html,
        )

    return '''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:16px 0 0}}

.sc-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}

.sc-card{{
    background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;
    padding:20px;text-align:center;transition:border-color 0.2s;
}}
.sc-card:hover{{border-color:#C9A962}}

.sc-header{{display:flex;align-items:center;justify-content:center;gap:6px;margin-bottom:16px}}
.sc-icon{{font-size:0.7rem;color:#5A5A6A}}
.sc-label{{font-size:0.55rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;font-weight:600}}
.sc-desc{{font-size:0.5rem;color:#2A2A36;letter-spacing:1px}}

.sc-iv{{
    font-family:'Cormorant Garamond',Georgia,serif;
    font-size:1.8rem;font-weight:700;color:#E8E8F0;
    line-height:1;margin-bottom:6px;
}}

.sc-sm{{font-size:0.7rem;font-weight:600;letter-spacing:1px;margin-bottom:14px}}

.sc-params{{border-top:1px solid #1A1A22;padding-top:10px}}
.sc-param{{
    display:flex;justify-content:space-between;
    font-size:0.6rem;color:#5A5A6A;padding:2px 0;
    letter-spacing:1px;
}}
.sc-param span:last-child{{color:#8888A0;font-weight:500}}
</style></head><body>
<div class="sc-grid">{cards}</div>
</body></html>'''.format(cards=cards_html)


def render_assumptions_panel(dcf: dict) -> str:
    """核心假设面板 — 透明度，让用户知道数字怎么来的"""
    if not dcf or dcf.get("method") == "insufficient":
        return ""

    a = dcf["assumptions"]
    dq = dcf["data_quality"]
    dq_color = {"high": "#00C853", "medium": "#FF9800", "low": "#F44336"}.get(dq, "#5A5A6A")
    dq_label = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}.get(dq, "N/A")

    rows = ""
    if a.get("fcf_per_share"):
        rows += _assumption_row("FCF / Share", "${:.2f}".format(a["fcf_per_share"]))
    if a.get("eps"):
        rows += _assumption_row("EPS (TTM)", "${:.2f}".format(a["eps"]))
    if a.get("base_growth") is not None:
        rows += _assumption_row("Growth Rate", "{:.1f}%".format(a["base_growth"]),
                                note=a.get("growth_source", ""))
    rows += _assumption_row("Discount Rate", "{:.1f}%".format(a["discount_rate"]))
    rows += _assumption_row("Terminal Growth", "{:.1f}%".format(a["terminal_growth"]))
    rows += _assumption_row("Projection", "{} years".format(a["projection_years"]))

    return '''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:16px 0 0}}

.asmp-card{{background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:20px 24px}}
.asmp-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}}
.asmp-title{{font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase}}
.dq-badge{{
    font-size:0.5rem;letter-spacing:2px;font-weight:600;
    color:{dq_color};border:1px solid {dq_color};
    padding:2px 8px;border-radius:2px;
    opacity:0.8;
}}
.asmp-row{{
    display:flex;justify-content:space-between;align-items:center;
    padding:6px 0;border-bottom:1px solid #12121C;
}}
.asmp-row:last-child{{border-bottom:none}}
.asmp-key{{font-size:0.65rem;color:#5A5A6A;letter-spacing:1px}}
.asmp-val{{font-size:0.7rem;color:#E8E8F0;font-weight:500;letter-spacing:0.5px}}
.asmp-note{{font-size:0.5rem;color:#3A3A4A;margin-left:8px;letter-spacing:1px}}

.asmp-disclaimer{{
    font-size:0.5rem;color:#2A2A36;letter-spacing:1px;
    margin-top:12px;line-height:1.6;text-align:center;
}}
</style></head><body>
<div class="asmp-card">
    <div class="asmp-header">
        <span class="asmp-title">Core Assumptions</span>
        <span class="dq-badge">DATA QUALITY: {dq_label}</span>
    </div>
    {rows}
    <div class="asmp-disclaimer">
        Estimates based on historical data and analyst consensus. Not financial advice.
        Past performance does not guarantee future results.
    </div>
</div>
</body></html>'''.format(dq_color=dq_color, dq_label=dq_label, rows=rows)


def _assumption_row(key, value, note=""):
    note_html = '<span class="asmp-note">({})</span>'.format(note) if note else ""
    return '<div class="asmp-row"><span class="asmp-key">{}{}</span><span class="asmp-val">{}</span></div>'.format(
        key, note_html, value)


def _render_insufficient(symbol, name, missing):
    return '''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:0}}
.insuf-card{{
    background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;
    padding:32px;text-align:center;
}}
.insuf-icon{{font-size:2rem;margin-bottom:12px;opacity:0.3}}
.insuf-title{{
    font-family:'Cormorant Garamond',Georgia,serif;
    font-size:1.4rem;font-weight:600;color:#5A5A6A;margin-bottom:8px;
}}
.insuf-desc{{font-size:0.7rem;color:#3A3A4A;line-height:1.6;letter-spacing:0.5px}}
.insuf-missing{{font-size:0.6rem;color:#F44336;margin-top:8px;letter-spacing:1px}}
</style></head><body>
<div class="insuf-card">
    <div class="insuf-icon">&#x26A0;</div>
    <div class="insuf-title">Valuation Unavailable</div>
    <div class="insuf-desc">{symbol} ({name}) lacks sufficient financial data for DCF analysis.</div>
    <div class="insuf-missing">Missing: {missing}</div>
</div>
</body></html>'''.format(symbol=symbol, name=name, missing=missing)


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "{},{},{}".format(r, g, b)
