"""投资委员会 — 统一视觉渲染

单一 HTML 页面输出，包含所有 4 个区块。
避免多 iframe 割裂，保证视觉连贯性。
"""


def _sc(signal: str) -> str:
    return {"bullish": "#00C853", "bearish": "#F44336", "neutral": "#C9A962"}.get(signal, "#5A5A6A")


def _sl(signal: str) -> str:
    return {"bullish": "BULLISH", "bearish": "BEARISH", "neutral": "NEUTRAL"}.get(signal, "--")


def render_committee_page(ensemble: dict = None, multi_val: dict = None,
                          price: float = 0, volatility: dict = None,
                          position: dict = None, risk_report: dict = None,
                          committee: dict = None) -> str:
    """渲染完整的投资委员会页面 — 单一 HTML

    四大区块：
    1. 五策略集成
    2. 四模型估值
    3. 风险管理
    4. 投资委员会投票（如果有结果）
    """
    sections = []

    # ── 1. 五策略集成 ────────────────────────────────────────
    if ensemble and ensemble.get("strategies"):
        sig = ensemble["ensemble_signal"]
        verdict = ensemble["ensemble_verdict"]
        hurst = ensemble.get("hurst")
        sc = "#00C853" if sig > 0.15 else ("#F44336" if sig < -0.15 else "#C9A962")

        bars = ""
        for s in ensemble["strategies"]:
            s_sig = s["signal"]
            s_color = "#00C853" if s_sig > 0 else ("#F44336" if s_sig < 0 else "#5A5A6A")
            bar_w = abs(s_sig) * 46
            if s_sig >= 0:
                bar_css = "left:50%;width:{:.1f}%".format(bar_w)
            else:
                left_pos = 50 - bar_w
                bar_css = "left:{:.1f}%;width:{:.1f}%".format(left_pos, bar_w)
            h_tag = ""
            if s.get("hurst") is not None:
                h_tag = '<span class="strat-extra">H={:.2f}</span>'.format(s["hurst"])
            bars += (
                '<div class="strat-row">'
                '<div class="strat-name">{}</div>'
                '<div class="strat-track"><div class="strat-mid"></div>'
                '<div class="strat-fill" style="{}; background:{}"></div></div>'
                '<div class="strat-val" style="color:{}">{:+.2f}</div>'
                '<div class="strat-conf">{:.0%}</div>{}</div>'
            ).format(s["name"], bar_css, s_color, s_color, s_sig, s["confidence"], h_tag)

        hurst_html = ""
        if hurst is not None:
            h_regime = "Mean Revert" if hurst < 0.4 else ("Trending" if hurst > 0.6 else "Random")
            h_color = "#60A5FA" if hurst < 0.4 else ("#00C853" if hurst > 0.6 else "#C9A962")
            hurst_html = (
                '<div class="ens-meta-item">'
                '<div class="ens-meta-label">HURST</div>'
                '<div class="ens-meta-val" style="color:{}">{:.3f}</div>'
                '<div class="ens-meta-sub" style="color:{}">{}</div></div>'
            ).format(h_color, hurst, h_color, h_regime)

        sections.append('''
        <div class="section">
            <div class="sec-label">Technical Ensemble &middot; 5 Strategies</div>
            <div class="ens-header">
                <div><div class="ens-sig" style="color:{sc}">{sig:+.3f}</div>
                <div class="ens-verdict" style="color:{sc}">{verdict}</div></div>
                <div class="ens-meta">{hurst}</div>
            </div>
            <div class="strat-list">{bars}</div>
        </div>'''.format(sc=sc, sig=sig, verdict=verdict, hurst=hurst_html, bars=bars))

    # ── 2. 四模型估值 ────────────────────────────────────────
    if multi_val:
        wiv = multi_val["weighted_intrinsic_value"]
        wsm = multi_val["weighted_safety_margin_pct"]
        sm_color = "#00C853" if wsm > 10 else ("#F44336" if wsm < -10 else "#C9A962")

        models_html = ""
        for mn, md in multi_val["models"].items():
            iv = md.get("intrinsic_value", 0)
            sm = md.get("safety_margin_pct", 0)
            mc = "#00C853" if sm > 10 else ("#F44336" if sm < -10 else "#9A9AA8")
            wt = multi_val["weights_used"].get(mn, 0)
            models_html += (
                '<div class="mod-card">'
                '<div class="mod-top"><span class="mod-name">{}</span><span class="mod-wt">{:.0f}%</span></div>'
                '<div class="mod-mid"><span class="mod-iv">{:.2f}</span>'
                '<span class="mod-sm" style="color:{}">{:+.1f}%</span></div></div>'
            ).format(mn, wt, iv, mc, sm)

        # 价格对比条
        if price > 0 and wiv > 0:
            ratio = price / wiv
            price_pos = min(max(ratio * 50, 5), 95)
        else:
            price_pos = 50

        sections.append('''
        <div class="section">
            <div class="sec-label">Multi-Model Valuation &middot; {count} Models</div>
            <div class="val-main">
                <div class="val-col">
                    <div class="val-tiny">WEIGHTED FAIR VALUE</div>
                    <div class="val-big">{wiv:.2f}</div>
                </div>
                <div class="val-col right">
                    <div class="val-tiny">SAFETY MARGIN</div>
                    <div class="val-big" style="color:{smc}">{wsm:+.1f}%</div>
                </div>
            </div>
            <div class="val-bar-wrap">
                <div class="val-bar-track"></div>
                <div class="val-marker" style="left:{pp:.1f}%"><div class="val-marker-dot"></div>
                <div class="val-marker-label">{price:.2f}</div></div>
                <div class="val-fair-mark" style="left:50%"><div class="val-fair-dot"></div>
                <div class="val-fair-label">{wiv:.2f}</div></div>
            </div>
            <div class="val-verdict" style="color:{smc}">{verdict}</div>
            <div class="models-grid">{models}</div>
        </div>'''.format(
            count=multi_val["model_count"], wiv=wiv, smc=sm_color, wsm=wsm,
            pp=price_pos, price=price, verdict=multi_val["verdict"], models=models_html,
        ))

    # ── 3. 风险管理 ────────────────────────────────────────
    if risk_report:
        vol = volatility or {}
        pos = position or {}
        annual_vol = vol.get("annual_vol_pct", 0)
        regime = vol.get("regime", "unknown")
        regime_map = {"low": ("Low", "#00C853"), "normal": ("Normal", "#C9A962"),
                      "high": ("High", "#FF9800"), "extreme": ("Extreme", "#F44336"),
                      "unknown": ("N/A", "#5A5A6A")}
        r_label, r_color = regime_map.get(regime, ("N/A", "#5A5A6A"))
        max_pos = pos.get("max_position_pct", 10)
        risk_score = risk_report.get("risk_score", 0)
        risk_color = "#00C853" if risk_score < 30 else ("#F44336" if risk_score >= 60 else "#C9A962")

        recs_html = ""
        for rec in risk_report.get("recommendations", []):
            recs_html += '<div class="rec-item">{}</div>'.format(rec)

        # 风险条
        risk_w = min(risk_score, 100)

        sections.append('''
        <div class="section">
            <div class="sec-label">Risk Management</div>
            <div class="risk-grid">
                <div class="risk-cell">
                    <div class="rc-label">VOLATILITY</div>
                    <div class="rc-val" style="color:{r_color}">{vol:.1f}%</div>
                    <div class="rc-sub" style="color:{r_color}">{r_label}</div>
                </div>
                <div class="risk-cell">
                    <div class="rc-label">MAX POSITION</div>
                    <div class="rc-val">{max_pos:.0f}%</div>
                    <div class="rc-sub" style="color:#6A6A78">{risk_level}</div>
                </div>
                <div class="risk-cell">
                    <div class="rc-label">RISK SCORE</div>
                    <div class="rc-val" style="color:{risk_color}">{risk_score}</div>
                    <div class="risk-bar-mini"><div class="risk-bar-fill" style="width:{risk_w}%;background:{risk_color}"></div></div>
                </div>
            </div>
            <div class="recs">{recs}</div>
        </div>'''.format(
            r_color=r_color, vol=annual_vol, r_label=r_label,
            max_pos=max_pos, risk_level=pos.get("risk_level", ""),
            risk_color=risk_color, risk_score=risk_score, risk_w=risk_w, recs=recs_html,
        ))

    # ── 4. 委员会投票 ────────────────────────────────────────
    if committee:
        cons = committee["consensus"]
        ws = committee["weighted_score"]
        sc = _sc(cons["signal"])
        bull = committee["bullish_count"]
        bear = committee["bearish_count"]
        neut = committee["neutral_count"]
        total = bull + bear + neut or 1

        members_html = ""
        for m in committee["members"]:
            mc = _sc(m["signal"])
            ml = _sl(m["signal"])

            evidence_html = ""
            if m.get("key_evidence"):
                evidence_html = '<div class="m-evidence" data-ev="">{}</div>'.format(m["key_evidence"])

            concern_html = ""
            if m.get("main_concern"):
                concern_html = (
                    '<div class="m-concern" data-warn="">'
                    '<span class="m-concern-icon" data-warn-icon="">&#9888;</span>'
                    '<span>{}</span>'
                    '</div>'
                ).format(m["main_concern"])

            members_html += (
                '<div class="m-card" style="border-left-color:{mc}">'
                '<div class="m-row1">'
                '<div class="m-who"><span class="m-icon">{icon}</span>'
                '<div><div class="m-name">{name}</div><div class="m-style">{style}</div></div></div>'
                '<div class="m-sig" style="color:{mc};border-color:{mc}">{label}</div></div>'
                '<div class="m-reason">{reason}</div>'
                '{evidence_html}'
                '{concern_html}'
                '<div class="m-bar-row"><div class="m-bar-track">'
                '<div class="m-bar-fill" style="width:{conf}%;background:{mc}"></div></div>'
                '<span class="m-conf">{conf}%</span></div></div>'
            ).format(
                mc=mc, icon=m["icon"], name=m["name_cn"], style=m["style"],
                label=ml, reason=m["reasoning"], conf=m["confidence"],
                evidence_html=evidence_html, concern_html=concern_html,
            )

        # 仪表位置
        gauge_pos = (ws + 100) / 200 * 100

        sections.append('''
        <div class="section">
            <div class="sec-label">Investment Committee &middot; Consensus</div>
            <div class="cons-card" style="border-top-color:{sc}">
                <div class="cons-header">
                    <div>
                        <div class="cons-unanimity">{unanimity}</div>
                        <div class="cons-verdict" style="color:{sc}">{verdict}</div>
                        <div class="cons-sub">{bull} Bullish &middot; {neut} Neutral &middot; {bear} Bearish</div>
                    </div>
                    <div class="cons-score-box">
                        <div class="cons-score-label">SCORE</div>
                        <div class="cons-score" style="color:{sc}">{ws:+.0f}</div>
                    </div>
                </div>
                <div class="cons-gauge">
                    <div class="cons-gauge-track"></div>
                    <div class="cons-gauge-dot" style="left:{gp:.1f}%;background:{sc}"></div>
                </div>
                <div class="cons-gauge-labels">
                    <span>Bearish</span><span>Neutral</span><span>Bullish</span>
                </div>
                <div class="vote-bar">
                    <div style="width:{bw:.0f}%;background:#00C853"></div>
                    <div style="width:{nw:.0f}%;background:#C9A962"></div>
                    <div style="width:{ew:.0f}%;background:#F44336"></div>
                </div>
            </div>
            <div class="members-list">{members}</div>
        </div>'''.format(
            sc=sc, unanimity=cons["unanimity"], verdict=cons["verdict"],
            bull=bull, neut=neut, bear=bear, ws=ws, gp=gauge_pos,
            bw=bull/total*100, nw=neut/total*100, ew=bear/total*100,
            members=members_html,
        ))

    if not sections:
        sections.append('''
        <div class="section empty-section">
            <div class="empty-icon">🏛</div>
            <div class="empty-title">Investment Committee</div>
            <div class="empty-desc">五策略集成 · 四模型估值 · 风险管理<br>点击上方按钮召集投资委员会</div>
        </div>''')

    body = "\n".join(sections)

    return '''<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;color:#E8E8F0;padding:8px 0}}

/* ── Section ── */
.section{{margin-bottom:28px}}
.sec-label{{
    font-size:0.48rem;letter-spacing:6px;color:rgba(201,169,98,0.5);
    text-transform:uppercase;margin-bottom:14px;
    padding-bottom:8px;border-bottom:1px solid rgba(201,169,98,0.06);
}}

/* ── Ensemble ── */
.ens-header{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:16px}}
.ens-sig{{font-family:'Cormorant Garamond',serif;font-size:2.2rem;font-weight:300;line-height:1}}
.ens-verdict{{font-size:0.62rem;letter-spacing:3px;text-transform:uppercase;margin-top:2px}}
.ens-meta{{display:flex;gap:20px}}
.ens-meta-item{{text-align:right}}
.ens-meta-label{{font-size:0.4rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase}}
.ens-meta-val{{font-family:'Cormorant Garamond',serif;font-size:1.3rem;font-weight:400}}
.ens-meta-sub{{font-size:0.5rem;letter-spacing:1px}}
.strat-list{{display:flex;flex-direction:column;gap:6px}}
.strat-row{{display:flex;align-items:center;gap:8px}}
.strat-name{{width:72px;font-size:0.62rem;color:#8A8A98;white-space:nowrap}}
.strat-track{{flex:1;height:5px;background:#141419;border-radius:3px;position:relative}}
.strat-mid{{position:absolute;left:50%;top:0;width:1px;height:100%;background:#2A2A33}}
.strat-fill{{position:absolute;top:0;height:100%;border-radius:3px;transition:width 0.5s}}
.strat-val{{width:40px;text-align:right;font-size:0.62rem;font-weight:600;font-variant-numeric:tabular-nums}}
.strat-conf{{width:28px;text-align:right;font-size:0.5rem;color:#5A5A6A}}
.strat-extra{{font-size:0.48rem;color:#5A5A6A;margin-left:4px}}

/* ── Valuation ── */
.val-main{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px}}
.val-col.right{{text-align:right}}
.val-tiny{{font-size:0.4rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-bottom:2px}}
.val-big{{font-family:'Cormorant Garamond',serif;font-size:2rem;font-weight:400;line-height:1}}
.val-bar-wrap{{position:relative;height:24px;margin-bottom:6px}}
.val-bar-track{{position:absolute;top:10px;left:0;right:0;height:3px;
    background:linear-gradient(90deg,#F44336 0%,#FF9800 30%,#C9A962 50%,#69F0AE 70%,#00C853 100%);
    border-radius:2px;opacity:0.4}}
.val-marker,.val-fair-mark{{position:absolute;top:0;transform:translateX(-50%)}}
.val-marker-dot,.val-fair-dot{{width:10px;height:10px;border-radius:50%;border:2px solid #08080C;margin:0 auto}}
.val-marker-dot{{background:#E8E8F0}}
.val-fair-dot{{background:#C9A962}}
.val-marker-label,.val-fair-label{{font-size:0.48rem;color:#8A8A98;text-align:center;margin-top:2px;white-space:nowrap}}
.val-fair-label{{color:#C9A962}}
.val-verdict{{font-size:0.68rem;font-weight:500;text-align:center;letter-spacing:1px;margin-bottom:14px}}
.models-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px}}
.mod-card{{background:#0D0D14;border:1px solid #1A1A24;border-radius:3px;padding:12px 14px;transition:border-color 0.2s}}
.mod-card:hover{{border-color:rgba(201,169,98,0.2)}}
.mod-top{{display:flex;justify-content:space-between;margin-bottom:6px}}
.mod-name{{font-size:0.6rem;color:#C9A962;letter-spacing:1px;font-weight:500}}
.mod-wt{{font-size:0.48rem;color:#5A5A6A}}
.mod-mid{{display:flex;align-items:baseline;gap:8px}}
.mod-iv{{font-family:'Cormorant Garamond',serif;font-size:1.3rem;font-weight:400;color:#E8E8F0}}
.mod-sm{{font-size:0.62rem;font-weight:600}}

/* ── Risk ── */
.risk-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:12px}}
.risk-cell{{text-align:center;padding:14px 10px;background:#0D0D14;border:1px solid #1A1A24;border-radius:3px}}
.rc-label{{font-size:0.4rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:4px}}
.rc-val{{font-family:'Cormorant Garamond',serif;font-size:1.6rem;font-weight:400;line-height:1.1}}
.rc-sub{{font-size:0.5rem;margin-top:3px;letter-spacing:1px}}
.risk-bar-mini{{height:3px;background:#1A1A24;border-radius:2px;margin-top:6px;overflow:hidden}}
.risk-bar-fill{{height:100%;border-radius:2px;transition:width 0.5s}}
.recs{{display:flex;flex-direction:column;gap:4px}}
.rec-item{{font-size:0.66rem;color:#8A8A98;padding:6px 10px;background:#0D0D14;border:1px solid #1A1A24;
    border-radius:2px;line-height:1.5}}

/* ── Committee ── */
.cons-card{{background:#0D0D14;border:1px solid #1E1E2A;border-top:2px solid;border-radius:4px;
    padding:24px 28px;margin-bottom:16px}}
.cons-header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px}}
.cons-unanimity{{font-size:0.42rem;letter-spacing:4px;color:#C9A962;text-transform:uppercase;
    border:1px solid rgba(201,169,98,0.15);display:inline-block;padding:3px 10px;margin-bottom:6px}}
.cons-verdict{{font-family:'Cormorant Garamond',serif;font-size:2rem;font-weight:600;line-height:1.1;letter-spacing:2px}}
.cons-sub{{font-size:0.62rem;color:#6A6A78;margin-top:4px;letter-spacing:0.5px}}
.cons-score-box{{text-align:right}}
.cons-score-label{{font-size:0.4rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase}}
.cons-score{{font-family:'Cormorant Garamond',serif;font-size:2.4rem;font-weight:300;line-height:1}}
.cons-gauge{{position:relative;height:12px;margin-bottom:4px}}
.cons-gauge-track{{position:absolute;top:4px;left:0;right:0;height:3px;
    background:linear-gradient(90deg,#F44336,#FF9800,#C9A962,#69F0AE,#00C853);border-radius:2px}}
.cons-gauge-dot{{position:absolute;top:0;width:12px;height:12px;border-radius:50%;
    border:2px solid #0D0D14;transform:translateX(-50%);box-shadow:0 0 6px rgba(201,169,98,0.3)}}
.cons-gauge-labels{{display:flex;justify-content:space-between;font-size:0.44rem;color:#5A5A6A;
    letter-spacing:1px;margin-bottom:12px}}
.vote-bar{{display:flex;height:6px;border-radius:3px;overflow:hidden;background:#1A1A24}}
.vote-bar>div{{transition:width 0.5s}}

.members-list{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}}
.m-card{{background:#0D0D14;border:1px solid #1A1A24;border-left:3px solid;border-radius:3px;
    padding:14px 16px;display:flex;flex-direction:column;gap:10px;transition:border-color 0.2s}}
.m-card:hover{{border-color:rgba(201,169,98,0.15)}}
.m-row1{{display:flex;justify-content:space-between;align-items:flex-start}}
.m-who{{display:flex;gap:8px;align-items:center}}
.m-icon{{font-size:1.3rem}}
.m-name{{font-size:0.78rem;font-weight:600;color:#E8E8F0}}
.m-style{{font-size:0.5rem;color:#6A6A78;letter-spacing:2px;text-transform:uppercase;margin-top:1px}}
.m-sig{{font-size:0.48rem;font-weight:700;letter-spacing:3px;padding:3px 8px;
    border:1px solid;border-radius:2px;white-space:nowrap}}
.m-reason{{font-size:0.68rem;color:#8A8A98;line-height:1.6;border-left:2px solid #1E1E2A;padding-left:10px}}
[data-ev]{{font-size:0.75rem;color:#A8A8B0;margin-top:6px;padding:5px 8px;border-left:2px solid #2A2A33;line-height:1.5}}
[data-warn]{{font-size:0.75rem;color:#F5A623;margin-top:5px;padding:4px 8px;display:flex;align-items:flex-start;gap:4px;line-height:1.5}}
[data-warn-icon]{{flex-shrink:0;margin-top:1px}}
.m-bar-row{{display:flex;align-items:center;gap:6px}}
.m-bar-track{{flex:1;height:3px;background:#1A1A24;border-radius:2px;overflow:hidden}}
.m-bar-fill{{height:100%;border-radius:2px;transition:width 0.5s}}
.m-conf{{font-size:0.56rem;color:#8A8A98;width:28px;text-align:right}}

/* ── Empty ── */
.empty-section{{text-align:center;padding:40px 20px}}
.empty-icon{{font-size:2.2rem;opacity:0.35;margin-bottom:12px}}
.empty-title{{font-family:'Cormorant Garamond',serif;font-size:1.3rem;color:#6A6A78;letter-spacing:2px;margin-bottom:6px}}
.empty-desc{{font-size:0.66rem;color:#5A5A6A;line-height:1.7}}
</style></head><body>{body}</body></html>'''.format(body=body)
