"""Settings — API / Notifications / Strategy"""

import streamlit as st
from src.config import ApiProvider, save_config, get_active_provider
from src.output.notify import send_notification, format_daily_push
from src.ui_theme import get_global_css, COLORS

from src.config import load_config
if "config" not in st.session_state:
    st.session_state.config = load_config()
config = st.session_state.config

st.markdown(get_global_css(), unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; padding:1.5rem 0 1.2rem 0; border-bottom:1px solid {border}; margin-bottom:1rem;">
    <h2 style="color:{text}; font-weight:300; letter-spacing:4px; margin:0;">SETTINGS</h2>
    <p style="color:{muted}; font-size:0.8rem; letter-spacing:2px; margin-top:0.4rem;">API · NOTIFICATIONS · STRATEGY</p>
</div>
""".format(text=COLORS["text"], muted=COLORS["text_muted"], border=COLORS["border"]), unsafe_allow_html=True)

tab_api, tab_notify, tab_alerts, tab_strategy, tab_watchlist = st.tabs(
    ["API", "NOTIFICATIONS", "PRICE ALERTS", "STRATEGY", "WATCHLIST"]
)

# ===== Tab 1: API =====
with tab_api:
    st.markdown('<div style="color:{}; font-size:0.75rem; letter-spacing:1px; margin-bottom:0.8rem;">AI MODEL CONFIGURATION</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)
    st.caption("Supports Anthropic, DeepSeek, OpenRouter, and any OpenAI-compatible API.")

    providers = config.api.providers

    for i, p in enumerate(providers):
        with st.expander(
            "{} {} {}".format(
                "●" if p.is_active else "○",
                p.name or "Provider {}".format(i+1),
                "({})".format(p.model[:30]) if p.model else ""
            ),
            expanded=p.is_active,
        ):
            col1, col2 = st.columns(2)
            with col1:
                p.name = st.text_input("Name", value=p.name, key="api_name_{}".format(i))
                p.provider = st.selectbox(
                    "Type", ["anthropic", "openai_compatible"],
                    index=0 if p.provider == "anthropic" else 1,
                    format_func=lambda x: {"anthropic": "Anthropic Claude", "openai_compatible": "OpenAI Compatible"}[x],
                    key="api_type_{}".format(i),
                )
            with col2:
                p.model = st.text_input("Model", value=p.model, key="api_model_{}".format(i),
                                        help="OpenRouter: deepseek/deepseek-chat, anthropic/claude-3-haiku | Anthropic直连: claude-haiku-4-5-20251001")
                if p.provider == "openai_compatible":
                    p.base_url = st.text_input("Base URL", value=p.base_url,
                                               key="api_url_{}".format(i),
                                               help="e.g. https://openrouter.ai/api/v1")

            p.api_key = st.text_input(
                "API Key", value=p.api_key, type="password",
                key="api_key_{}".format(i),
                help="Key is session-only unless saved to config",
            )

            col_act, col_test, col_del = st.columns(3)
            with col_act:
                if st.button(
                    "ACTIVE" if p.is_active else "Activate",
                    key="activate_{}".format(i),
                    type="primary" if not p.is_active else "secondary",
                    disabled=p.is_active,
                ):
                    for j, pp in enumerate(providers):
                        pp.is_active = (j == i)
                    st.rerun()
            with col_test:
                if st.button("Test", key="test_{}".format(i)):
                    if not p.api_key:
                        st.error("Please enter API key first")
                    else:
                        with st.spinner("Testing..."):
                            try:
                                from src.ai.summarizer import _call_llm
                                reply = _call_llm(p, [{"role": "user", "content": "Reply in one sentence: who are you?"}], max_tokens=100)
                                st.success("Connected: {}".format(reply[:100]))
                            except Exception as e:
                                st.error("Failed: {}".format(e))
            with col_del:
                if len(providers) > 1 and not p.is_active:
                    if st.button("Delete", key="del_{}".format(i)):
                        providers.pop(i)
                        st.rerun()

    st.divider()

    if st.button("+ Add Provider"):
        providers.append(ApiProvider(
            name="New Provider",
            provider="openai_compatible",
            model="",
        ))
        st.rerun()

    active = get_active_provider(config)
    if active:
        st.markdown('<div style="color:{}; font-size:0.85rem; padding:0.5rem 0;">Active: <strong>{}</strong> ({})</div>'.format(
            COLORS["success"], active.name, active.model), unsafe_allow_html=True)
    else:
        st.warning("No active API — configure a key and activate above.")


# ===== Tab 2: Notifications =====
with tab_notify:
    st.markdown('<div style="color:{}; font-size:0.75rem; letter-spacing:1px; margin-bottom:0.8rem;">SCHEDULED PUSH</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)

    notify = config.notify
    notify.enabled = st.toggle("Enable notifications", value=notify.enabled)

    if notify.enabled:
        col1, col2 = st.columns(2)
        with col1:
            notify.method = st.radio("Method", ["email", "webhook"],
                                     format_func=lambda x: {"email": "Email (SMTP)", "webhook": "Webhook"}[x],
                                     index=0 if notify.method == "email" else 1)
        with col2:
            notify.schedule_time = st.time_input(
                "Daily push time",
                value=__import__("datetime").time(8, 0),
                help="Recommended: before market open",
            ).strftime("%H:%M")
            notify.schedule_days = st.selectbox(
                "Push days",
                ["mon-fri", "everyday"],
                format_func=lambda x: {"mon-fri": "Weekdays", "everyday": "Every day"}[x],
            )

        st.divider()

        if notify.method == "email":
            col1, col2 = st.columns(2)
            with col1:
                notify.smtp_server = st.text_input("SMTP Server", value=notify.smtp_server,
                                                   help="QQ: smtp.qq.com, Gmail: smtp.gmail.com")
                notify.smtp_port = st.number_input("Port", value=notify.smtp_port, min_value=1, max_value=65535,
                                                   help="SSL: 465, STARTTLS: 587")
            with col2:
                notify.smtp_user = st.text_input("Sender Email", value=notify.smtp_user)
                notify.smtp_password = st.text_input("Auth Code", value=notify.smtp_password, type="password")
            notify.email_to = st.text_input("Recipient(s)", value=notify.email_to,
                                            help="Separate multiple with commas")
        else:
            notify.webhook_url = st.text_input(
                "Webhook URL", value=notify.webhook_url,
                help="DingTalk / Feishu / WeCom robot webhook",
            )

        st.divider()

        st.markdown('<div style="color:{}; font-size:0.75rem; letter-spacing:1px; margin-bottom:0.5rem;">PUSH CONTENT</div>'.format(
            COLORS["text_muted"]), unsafe_allow_html=True)
        notify.push_daily_summary = st.checkbox("Daily analysis summary", value=notify.push_daily_summary)
        notify.push_grade_change = st.checkbox("Grade change alerts", value=notify.push_grade_change)
        notify.push_alert_threshold = st.slider(
            "High score alert threshold", 50, 100, int(notify.push_alert_threshold))

        st.divider()

        col_test, col_push = st.columns(2)
        with col_test:
            if st.button("Send Test Push", type="secondary"):
                test_title = "Buffett Research — Test"
                test_content = "Test notification. Time: {}".format(
                    __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                success = send_notification(test_title, test_content, notify)
                if success:
                    st.success("Test push sent successfully")
                else:
                    st.error("Send failed — check configuration")

        with col_push:
            if st.button("▶ Push Now (Full Analysis)", type="primary"):
                with st.spinner("Analyzing watchlist and pushing..."):
                    try:
                        from src.scheduler import run_and_push
                        run_and_push()
                        st.success("Analysis complete, push sent!")
                    except Exception as e:
                        st.error("Push failed: {}".format(e))

        st.divider()
        st.caption("""
**Automated daily push:** run the scheduler as a background process on your server or local machine:
```bash
cd ~/stock-analyst && .venv/bin/python -m src.scheduler
```
""")
    else:
        st.markdown('<div style="color:{}; font-size:0.88rem; padding:1rem 0;">Enable to auto-analyze and push reports on schedule.</div>'.format(
            COLORS["text_muted"]), unsafe_allow_html=True)


# ===== Tab 3: Price Alerts =====
with tab_alerts:
    st.markdown('<div style="color:{}; font-size:0.75rem; letter-spacing:1px; margin-bottom:0.8rem;">PRICE ALERT RULES</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)
    st.caption("Set target prices for your watchlist stocks. Alerts are sent via your configured notification channel when triggered.")

    alerts = config.notify.price_alerts

    # ── Existing alerts ──
    if alerts:
        for idx, alert in enumerate(alerts):
            dir_icon = "↓" if alert.direction == "below" else "↑"
            dir_label = "≤" if alert.direction == "below" else "≥"
            col_sym, col_price, col_tog, col_del = st.columns([2, 2, 1, 1])
            with col_sym:
                st.markdown(
                    f'<span style="font-weight:600;color:{COLORS["text"]}">{alert.symbol}</span>'
                    f'<span style="color:{COLORS["text_muted"]};font-size:0.8rem"> [{alert.market}]</span>'
                    + (f'<br><span style="color:{COLORS["text_muted"]};font-size:0.75rem">{alert.note}</span>' if alert.note else ""),
                    unsafe_allow_html=True,
                )
            with col_price:
                st.markdown(
                    f'<span style="color:{COLORS["gold"]}">{dir_icon} {dir_label} {alert.target_price:.2f}</span>',
                    unsafe_allow_html=True,
                )
            with col_tog:
                new_enabled = st.toggle("On", value=alert.enabled, key=f"alert_tog_{idx}", label_visibility="collapsed")
                if new_enabled != alert.enabled:
                    alert.enabled = new_enabled
            with col_del:
                if st.button("✕", key=f"alert_del_{idx}"):
                    alerts.pop(idx)
                    st.rerun()
        st.divider()
    else:
        st.markdown(f'<div style="color:{COLORS["text_muted"]};font-size:0.85rem;padding:0.5rem 0;">No alerts set.</div>',
                    unsafe_allow_html=True)

    # ── Add new alert ──
    with st.expander("＋ Add New Alert", expanded=len(alerts) == 0):
        # Build options from watchlist
        all_stocks = (
            [(s.symbol, s.name, "us") for s in config.watchlist.us]
            + [(s.symbol, s.name, "hk") for s in config.watchlist.hk]
            + [(s.symbol, s.name, "a_share") for s in config.watchlist.a_share]
        )
        if all_stocks:
            options = [f"{sym} — {name} [{mkt}]" for sym, name, mkt in all_stocks]
            selected = st.selectbox("Stock (from watchlist)", options, key="alert_stock_sel")
            sel_idx = options.index(selected)
            sel_sym, sel_name, sel_mkt = all_stocks[sel_idx]
        else:
            sel_sym = st.text_input("Symbol", placeholder="e.g. AAPL", key="alert_sym_manual")
            sel_name = ""
            sel_mkt = st.selectbox("Market", ["us", "hk", "a_share"], key="alert_mkt_manual")

        col_dir, col_price = st.columns(2)
        with col_dir:
            direction = st.selectbox(
                "Direction",
                ["below", "above"],
                format_func=lambda x: "↓ Alert when price ≤ target" if x == "below" else "↑ Alert when price ≥ target",
                key="alert_dir",
            )
        with col_price:
            target = st.number_input("Target Price", min_value=0.01, value=100.0, step=0.5, key="alert_target")

        note = st.text_input("Note (optional)", placeholder="e.g. Buy zone, stop-loss level", key="alert_note")

        if st.button("Add Alert", key="alert_add_btn", type="primary"):
            if sel_sym:
                from src.config import PriceAlert
                alerts.append(PriceAlert(
                    symbol=sel_sym.strip().upper(),
                    name=sel_name,
                    market=sel_mkt,
                    target_price=float(target),
                    direction=direction,
                    enabled=True,
                    note=note,
                ))
                st.success(f"Alert added for {sel_sym}")
                st.rerun()

    st.divider()

    # ── Manual check ──
    col_check, col_info = st.columns([1, 2])
    with col_check:
        if st.button("🔔 Check Alerts Now", type="secondary", use_container_width=True):
            if not config.notify.enabled:
                st.warning("Enable notifications first (Notifications tab).")
            elif not alerts:
                st.info("No alerts configured.")
            else:
                with st.spinner("Checking prices…"):
                    try:
                        from src.scheduler import check_price_alerts_now
                        triggered = check_price_alerts_now()
                        if triggered:
                            st.success(f"🚨 {len(triggered)} alert(s) triggered and sent!")
                            for t in triggered:
                                st.markdown(f"- **{t['symbol']}**: {t['price']:.2f} (target {t['target']:.2f})")
                        else:
                            st.info("No alerts triggered at current prices.")
                    except Exception as e:
                        st.error(f"Check failed: {e}")
    with col_info:
        from src.scheduler import get_last_run_time
        st.caption(f"Last scheduled run: **{get_last_run_time()}**")
        st.caption("Alerts are also checked automatically during each scheduled daily push.")


# ===== Tab 4: Strategy =====
with tab_strategy:
    st.markdown('<div style="color:{}; font-size:0.75rem; letter-spacing:1px; margin-bottom:0.8rem;">BUFFETT VALUE INVESTING PARAMETERS</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)

    bs = config.buffett_strategy

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**MOAT (30pts)**")
        bs.min_roe = float(st.number_input("Min ROE (%)", value=bs.min_roe, min_value=0.0, max_value=50.0, step=1.0))
        bs.roe_consistency_years = st.number_input("ROE years required", value=bs.roe_consistency_years, min_value=1, max_value=10)

    with col2:
        st.markdown("**FINANCIAL HEALTH (20pts)**")
        bs.max_debt_to_equity = float(st.number_input("Max D/E ratio", value=bs.max_debt_to_equity,
                                                       min_value=0.0, max_value=5.0, step=0.1))
        bs.min_current_ratio = float(st.number_input("Min current ratio", value=bs.min_current_ratio,
                                                      min_value=0.0, max_value=5.0, step=0.1))

    with col3:
        st.markdown("**VALUATION (25pts)**")
        bs.max_pe = float(st.number_input("Max PE", value=bs.max_pe, min_value=5.0, max_value=100.0, step=1.0))
        bs.max_pb = float(st.number_input("Max PB", value=bs.max_pb, min_value=0.5, max_value=20.0, step=0.5))
        bs.margin_of_safety = float(st.slider("Margin of safety (%)", 5, 50,
                                               int(bs.margin_of_safety * 100))) / 100

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**GROWTH (20pts)**")
        bs.min_revenue_growth = float(st.number_input("Min revenue growth (%)", value=bs.min_revenue_growth,
                                                       min_value=0.0, step=1.0))
        bs.min_earnings_growth = float(st.number_input("Min earnings growth (%)", value=bs.min_earnings_growth,
                                                        min_value=0.0, step=1.0))
    with col2:
        st.markdown("**MANAGEMENT (5pts)**")
        bs.min_payout_ratio = float(st.number_input("Min payout ratio", value=bs.min_payout_ratio,
                                                     min_value=0.0, max_value=1.0, step=0.05))

    st.divider()

    st.markdown('<div style="color:{}; font-size:0.75rem; letter-spacing:1px; margin-bottom:0.5rem;">TECHNICAL PARAMETERS</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)
    tc = config.technical
    col1, col2 = st.columns(2)
    with col1:
        tc.rsi_period = st.number_input("RSI Period", value=tc.rsi_period, min_value=5, max_value=30)
    with col2:
        tc.lookback_days = st.number_input("Lookback Days", value=tc.lookback_days, min_value=30, max_value=500)


# ===== Tab 4: Watchlist =====
with tab_watchlist:
    st.markdown('<div style="color:{}; font-size:0.75rem; letter-spacing:1px; margin-bottom:0.8rem;">WATCHLIST MANAGEMENT</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)

    for market_key, market_name in [("us", "US MARKET"), ("hk", "HK MARKET"), ("a_share", "A-SHARE")]:
        st.markdown("### {}".format(market_name))
        stocks = getattr(config.watchlist, market_key, [])

        if stocks:
            for j, stock in enumerate(stocks):
                col1, col2, col3 = st.columns([3, 3, 1])
                with col1:
                    st.markdown('<span style="font-weight:600; color:{};">{}</span>'.format(
                        COLORS["text"], stock.symbol), unsafe_allow_html=True)
                with col2:
                    st.markdown('<span style="color:{};">{}</span>'.format(
                        COLORS["text_secondary"], stock.name), unsafe_allow_html=True)
                with col3:
                    if st.button("×", key="del_stock_{}_{}".format(market_key, j)):
                        stocks.pop(j)
                        st.rerun()
        else:
            st.markdown('<div style="color:{}; font-size:0.85rem; padding:0.5rem 0;">No stocks</div>'.format(
                COLORS["text_muted"]), unsafe_allow_html=True)

        with st.expander("Batch add {}".format(market_name)):
            bulk = st.text_area(
                "One per line: SYMBOL,NAME",
                key="bulk_{}".format(market_key),
                placeholder="AAPL,Apple\nMSFT,Microsoft" if market_key == "us" else
                           "0700.HK,Tencent" if market_key == "hk" else
                           "sh600519,Kweichow Moutai",
                height=100,
            )
            if st.button("Add", key="bulk_btn_{}".format(market_key)):
                added = 0
                for line in bulk.strip().split("\n"):
                    line = line.strip()
                    if "," in line:
                        parts = line.split(",", 1)
                        sym, name = parts[0].strip(), parts[1].strip()
                        if sym and name and not any(s.symbol == sym for s in stocks):
                            from src.config import StockItem
                            stocks.append(StockItem(symbol=sym, name=name))
                            added += 1
                if added:
                    st.success("Added {} stocks".format(added))
                    st.rerun()

        st.divider()

# ===== 全局保存按钮（固定在页面底部）=====
st.markdown("---")
col_save, col_info = st.columns([1, 3])
with col_save:
    if st.button("💾 Save All Settings", type="primary", use_container_width=True):
        try:
            save_config(config)
            st.success("Settings saved to config.yaml")
        except Exception as e:
            st.error("Save failed: {}".format(e))
with col_info:
    st.caption("Settings are stored in `config.yaml`. API keys are session-only by default (not written to file) — use environment variables for persistent key storage.")
