"""Settings — API / Notifications / Strategy"""

import streamlit as st
from src.config import ApiProvider, save_config, get_active_provider
from src.output.notify import send_notification, format_daily_push
from src.ui_theme import get_global_css, COLORS
from pages._model_presets import MODEL_PRESETS

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

from src.auth import get_current_user
from src.user_data import (get_user_plan, get_monthly_usage, set_user_plan, FREE_MONTHLY_LIMIT,
                            load_price_alerts, add_price_alert, delete_price_alert)

_user = get_current_user()
_uid = (_user or {}).get("username", "anonymous")
_role = (_user or {}).get("role", "viewer")

tab_api, tab_notify, tab_alerts, tab_strategy, tab_watchlist, tab_plan = st.tabs(
    ["API", "NOTIFICATIONS", "PRICE ALERTS", "STRATEGY", "WATCHLIST", "PLAN"]
)

# ===== Tab 1: API =====
with tab_api:
    st.markdown('<div style="color:{}; font-size:0.75rem; letter-spacing:1px; margin-bottom:0.8rem;">AI MODEL CONFIGURATION</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)
    st.caption("Supports Anthropic, DeepSeek, OpenRouter, and any OpenAI-compatible API.")

    # ── 快速切换模型 ──────────────────────────────────────────────
    st.markdown(
        '<div style="color:{c}; font-size:0.7rem; letter-spacing:2px; margin:1rem 0 0.5rem;">快速切换模型 · QUICK SWITCH</div>'.format(
            c=COLORS["gold"]
        ),
        unsafe_allow_html=True,
    )
    _active_provider = None
    for _p in config.api.providers:
        if _p.is_active:
            _active_provider = _p
            break

    _cols = st.columns(len(MODEL_PRESETS))
    for _ci, _preset in enumerate(MODEL_PRESETS):
        with _cols[_ci]:
            _is_current = _active_provider and _active_provider.model == _preset["model"]
            if st.button(
                "{} {}".format(_preset["icon"], _preset["label"]),
                key="preset_{}".format(_ci),
                type="primary" if _is_current else "secondary",
                use_container_width=True,
                help="切换到 {}".format(_preset["model"]),
            ):
                if _active_provider:
                    _active_provider.model = _preset["model"]
                    _active_provider.base_url = _preset["base_url"]
                    _active_provider.provider = "openai_compatible"
                    save_config(config)
                    st.success("已切换到 {}".format(_preset["label"]))
                    st.rerun()
                else:
                    st.warning("请先激活一个 OpenRouter provider")
    st.divider()
    # ─────────────────────────────────────────────────────────────

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
                        with st.spinner("Testing (≤20s)..."):
                            try:
                                from src.ai.summarizer import _call_llm
                                reply = _call_llm(
                                    p,
                                    [{"role": "user", "content": "Reply in one sentence: who are you?"}],
                                    max_tokens=100,
                                    timeout=20.0,
                                )
                                st.success("Connected: {}".format(reply[:100]))
                            except Exception as e:
                                msg = str(e)
                                if "timeout" in msg.lower() or "timed out" in msg.lower():
                                    st.error("Timeout after 20s. Check network / base_url / model.")
                                else:
                                    st.error("Failed: {}".format(msg[:200]))
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
                test_title = "AI Buffett — Test"
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
    st.markdown(
        '<div style="color:{c}; font-size:0.75rem; letter-spacing:1px; '
        'margin-bottom:4px;">MY PRICE ALERTS</div>'.format(c=COLORS["text_muted"]),
        unsafe_allow_html=True,
    )
    st.caption("设置目标价提醒。当关注股票价格到达目标位时，Dashboard 会自动弹出通知。数据跨设备同步保存。")

    # Load user's alerts from Supabase / local fallback
    _user_alerts = load_price_alerts(_uid)
    _active_alerts = [a for a in _user_alerts if not a.get("triggered")]
    _done_alerts   = [a for a in _user_alerts if a.get("triggered")]

    # ── Active alerts ──────────────────────────────────────────────────
    if _active_alerts:
        st.markdown(
            '<div style="font-size:0.5rem;letter-spacing:3px;color:#3A3A4A;'
            'text-transform:uppercase;margin-bottom:8px;">活跃提醒</div>',
            unsafe_allow_html=True,
        )
        for _al in _active_alerts:
            _al_id  = _al.get("id", "")
            _al_dir = "↓ 跌至" if _al.get("alert_type") == "below" else "↑ 涨至"
            _al_col1, _al_col2, _al_col3 = st.columns([3, 2, 1])
            with _al_col1:
                st.markdown(
                    '<span style="font-weight:600;color:#E8E8F0;">{sym}</span>'
                    '&nbsp;<span style="font-size:0.65rem;color:#5A5A6A;">{name} [{mkt}]</span>'.format(
                        sym=_al["symbol"], name=_al.get("name", ""), mkt=_al["market"],
                    ), unsafe_allow_html=True,
                )
            with _al_col2:
                st.markdown(
                    '<span style="color:#C9A962;font-weight:600;">{dir} {tp:.2f}</span>'.format(
                        dir=_al_dir, tp=_al.get("target_price", 0),
                    ), unsafe_allow_html=True,
                )
            with _al_col3:
                if st.button("删除", key="aldel_{}".format(_al_id)):
                    delete_price_alert(_uid, _al_id)
                    st.rerun()
        st.divider()
    else:
        st.markdown(
            '<div style="color:#3A3A4A;font-size:0.85rem;padding:8px 0 16px;">暂无活跃提醒。</div>',
            unsafe_allow_html=True,
        )

    # ── Add new alert ──────────────────────────────────────────────────
    with st.expander("＋ 新增提醒", expanded=len(_active_alerts) == 0):
        _al_c1, _al_c2, _al_c3 = st.columns([2, 1, 2])
        with _al_c1:
            _new_sym  = st.text_input("股票代码", placeholder="AAPL / 0700.HK / sh600519", key="nal_sym")
            _new_name = st.text_input("股票名称（选填）", placeholder="Apple", key="nal_name")
        with _al_c2:
            _new_mkt = st.selectbox("市场", ["us", "hk", "a_share"], key="nal_mkt")
            _new_dir = st.selectbox(
                "方向", ["below", "above"],
                format_func=lambda x: "↓ 跌至（买入提醒）" if x == "below" else "↑ 涨至（止盈提醒）",
                key="nal_dir",
            )
        with _al_c3:
            _new_tp = st.number_input("目标价", min_value=0.01, value=100.0, step=0.5, key="nal_tp")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("确认添加", key="nal_add", type="primary"):
                if _new_sym.strip():
                    ok = add_price_alert(
                        uid=_uid,
                        symbol=_new_sym.strip().upper(),
                        market=_new_mkt,
                        name=_new_name.strip() or _new_sym.strip().upper(),
                        alert_type=_new_dir,
                        target_price=float(_new_tp),
                    )
                    if ok:
                        st.success("提醒已保存 ✓")
                        st.rerun()
                    else:
                        st.error("保存失败，请重试。")
                else:
                    st.warning("请输入股票代码。")

    # ── Triggered history ──────────────────────────────────────────────
    if _done_alerts:
        with st.expander("已触发记录（{}条）".format(len(_done_alerts))):
            for _da in _done_alerts[:20]:
                _da_dir = "跌至" if _da.get("alert_type") == "below" else "涨至"
                _da_time = (_da.get("triggered_at") or "")[:10]
                st.caption("{sym} — {dir} {tp:.2f}  |  触发时间：{t}".format(
                    sym=_da["symbol"], dir=_da_dir,
                    tp=_da.get("target_price", 0), t=_da_time,
                ))

    st.info("💡 提示：提醒会在你打开 Dashboard 时自动检查当前价格。每次访问 Dashboard 即触发检测。")


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

# ===== Tab 6: Plan =====
with tab_plan:
    plan = get_user_plan(_uid)
    used = get_monthly_usage(_uid)
    remaining = max(0, FREE_MONTHLY_LIMIT - used)

    st.markdown('<div style="color:{}; font-size:0.75rem; letter-spacing:1px; margin-bottom:0.8rem;">SUBSCRIPTION PLAN</div>'.format(
        COLORS["text_muted"]), unsafe_allow_html=True)

    plan_color = "#C9A962" if plan == "premium" else "#5A5A6A"
    plan_label = "PREMIUM" if plan == "premium" else "FREE"

    st.markdown(
        '<div style="background:#0D0D14;border:1px solid #1E1E2A;border-left:3px solid {};'
        'border-radius:4px;padding:16px 20px;margin-bottom:16px">'
        '<div style="font-size:0.5rem;letter-spacing:3px;color:{};text-transform:uppercase;margin-bottom:6px">Current Plan</div>'
        '<div style="font-size:1.5rem;font-weight:700;color:{};letter-spacing:2px">{}</div>'
        '</div>'.format(plan_color, plan_color, plan_color, plan_label),
        unsafe_allow_html=True)

    if plan == "free":
        st.markdown(
            '<div style="background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:16px 20px">'
            '<div style="font-size:0.6rem;color:#5A5A6A;letter-spacing:2px;margin-bottom:8px">MONTHLY USAGE</div>'
            '<div style="font-size:1.2rem;color:#E8E8F0">{used}/{limit} analyses used</div>'
            '<div style="font-size:0.7rem;color:#C9A962;margin-top:4px">{rem} remaining this month</div>'
            '</div>'.format(used=used, limit=FREE_MONTHLY_LIMIT, rem=remaining),
            unsafe_allow_html=True)

        st.markdown("")
        st.markdown("**Free Plan includes:**")
        st.markdown("- {} stock analyses per month".format(FREE_MONTHLY_LIMIT))
        st.markdown("- Basic DCF valuation")
        st.markdown("- Market sentiment data")
        st.markdown("")
        st.markdown("**Premium Plan includes:**")
        st.markdown("- Unlimited stock analyses")
        st.markdown("- AI-powered insight cards")
        st.markdown("- Weekly AI market report")
        st.markdown("- Portfolio tracking")
        st.markdown("- Priority support")
        st.markdown("")
        st.info("Contact admin to upgrade to Premium.")
    else:
        st.success("You have unlimited access to all features.")

    # Admin: manage user plans
    if _role == "admin":
        st.markdown("---")
        st.markdown("**Admin: Manage User Plans**")
        admin_uid = st.text_input("Username", key="admin_uid_plan")
        admin_plan = st.selectbox("Plan", ["free", "premium"], key="admin_plan_sel")
        if st.button("Update Plan", key="admin_plan_btn"):
            if admin_uid.strip():
                set_user_plan(admin_uid.strip().lower(), admin_plan)
                st.success("Plan updated for {}".format(admin_uid))


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
