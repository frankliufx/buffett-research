"""技术面 fragment — candlestick chart + AI-narrated trend report."""

import logging

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.ai.summarizer import _call_llm
from src.ui_components import with_status
from src.ui_theme import COLORS
from src.fragments._shared import PLOT_LAYOUT

logger = logging.getLogger(__name__)


def plot_candlestick(df, symbol, name):
    """Returns a plotly figure — caller renders with `st.plotly_chart`."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=[0.75, 0.25],
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="K",
        increasing_line_color=COLORS["success"],
        decreasing_line_color=COLORS["danger"],
        increasing_fillcolor=COLORS["success"],
        decreasing_fillcolor=COLORS["danger"],
    ), row=1, col=1)

    sma_colors = {"SMA_20": COLORS["primary"], "SMA_50": COLORS["info"], "SMA_200": "#A78BFA"}
    for col_name, color in sma_colors.items():
        if col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_name], name=col_name.replace("_", " "),
                line=dict(color=color, width=1),
            ), row=1, col=1)

    if "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"], name="BB",
            line=dict(color="rgba(201,169,98,0.3)", dash="dash"),
            showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"], name="BB",
            line=dict(color="rgba(201,169,98,0.3)", dash="dash"),
            fill="tonexty", fillcolor="rgba(201,169,98,0.04)",
            showlegend=False,
        ), row=1, col=1)

    if "Volume" in df.columns:
        colors_vol = [COLORS["success"] if c >= o else COLORS["danger"]
                      for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"], name="VOL",
            marker_color=colors_vol, opacity=0.35,
        ), row=2, col=1)

    fig.update_layout(
        title=dict(text="{} {}".format(symbol, name), font=dict(color=COLORS["text"], size=14)),
        height=520, xaxis_rangeslider_visible=False,
        **PLOT_LAYOUT,
    )
    fig.update_xaxes(gridcolor=COLORS["border"], row=2, col=1)
    fig.update_yaxes(gridcolor=COLORS["border"], row=1, col=1)
    fig.update_yaxes(gridcolor=COLORS["border"], row=2, col=1)
    return fig


@st.fragment
def render_trend_analysis(symbol, name, market, price, change, df, normalized, moat, result, provider):
    """Stage-level price-action analysis through a value-investing lens."""
    trend_key = "ai_trend_{}".format(symbol)
    tech = result.tech_signal

    pct_5d, pct_20d, pct_60d = None, None, None

    if not df.empty and len(df) > 5:
        pct_5d = round((df["Close"].iloc[-1] / df["Close"].iloc[-5] - 1) * 100, 2) if len(df) > 5 else None
        pct_20d = round((df["Close"].iloc[-1] / df["Close"].iloc[-20] - 1) * 100, 2) if len(df) > 20 else None
        pct_60d = round((df["Close"].iloc[-1] / df["Close"].iloc[-60] - 1) * 100, 2) if len(df) > 60 else None

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        if change is not None:
            delta_str = ("+" if change >= 0 else "") + str(round(change, 2)) + "%"
            st.metric("今日", str(price), delta_str)
        else:
            st.metric("今日", str(price), "N/A")
    with m2:
        if pct_5d is not None:
            st.metric("近5日", ("+" if pct_5d >= 0 else "") + str(pct_5d) + "%", "短期动量")
        else:
            st.metric("近5日", "--", "")
    with m3:
        if pct_20d is not None:
            st.metric("近20日", ("+" if pct_20d >= 0 else "") + str(pct_20d) + "%", "月度趋势")
        else:
            st.metric("近20日", "--", "")
    with m4:
        if pct_60d is not None:
            st.metric("近60日", ("+" if pct_60d >= 0 else "") + str(pct_60d) + "%", "季度走势")
        else:
            st.metric("近60日", "--", "")

    st.markdown("---")

    if trend_key not in st.session_state:
        if provider:
            with with_status("AI 撰写阶段性行情分析中...", complete_label="AI 行情分析已就绪"):
                st.session_state[trend_key] = _generate_trend_report(
                    symbol, name, market, price, change, pct_5d, pct_20d, pct_60d,
                    normalized, moat, tech, provider,
                )
        else:
            st.session_state[trend_key] = None

    report = st.session_state.get(trend_key)
    if report:
        st.markdown(report)
    else:
        st.info("配置 API Key 后可生成 AI 阶段性行情分析")

    if st.button("刷新行情分析", key="refresh_trend_{}".format(symbol)):
        st.session_state.pop(trend_key, None)
        st.rerun()


def _generate_trend_report(symbol, name, market, price, change, pct_5d, pct_20d, pct_60d,
                           normalized, moat, tech, provider):
    """Call the LLM for the trend narrative; returns markdown or None on failure."""
    pe = normalized.get("pe_trailing")
    roe = normalized.get("roe")
    gm = normalized.get("gross_margin")
    rg = normalized.get("revenue_growth")
    eg = normalized.get("earnings_growth")
    rsi = tech.get("rsi")
    trend = tech.get("trend", "unknown")
    signals = tech.get("signals", [])

    def _v(val, suffix=""):
        if val is None:
            return "N/A"
        return str(round(val, 2)) + suffix

    market_label = {"us": "美股", "hk": "港股", "a_share": "A股"}.get(market, market)

    prompt = (
        "你是一位融合巴菲特价值投资与段永平本分哲学的资深行情分析师，拥有20年A股、港股、美股实战经验。\n"
        "请为以下股票撰写一份**阶段性行情分析报告**，风格要求：专业、深刻、有洞察力，像给机构投资者写的晨会纪要。\n\n"
        "## 股票信息\n"
        + name + "（" + symbol + "），" + market_label + "，当前价 " + str(price) + "\n\n"
        "## 近期走势\n"
        "- 今日涨跌: " + _v(change, "%") + "\n"
        "- 近5日: " + _v(pct_5d, "%") + "\n"
        "- 近20日: " + _v(pct_20d, "%") + "\n"
        "- 近60日: " + _v(pct_60d, "%") + "\n\n"
        "## 基本面概况\n"
        "- 护城河评分: " + str(moat["percentage"]) + "/100 (" + moat["grade"] + "级)\n"
        "- PE: " + _v(pe) + " | ROE: " + _v(roe, "%") + " | 毛利率: " + _v(gm, "%") + "\n"
        "- 营收增长: " + _v(rg, "%") + " | 利润增长: " + _v(eg, "%") + "\n\n"
        "## 技术面\n"
        "- 趋势: " + trend + " | RSI: " + _v(rsi) + "\n"
        "- 信号: " + ("; ".join(signals) if signals else "无明显信号") + "\n\n"
        "---\n"
        "请用以下结构输出（直接用 Markdown 格式，不要 JSON）：\n\n"
        "### 行情复盘\n"
        "用2-3句话描述近期股价走势的阶段性特征（趋势、波动、量能），引用具体涨跌幅数据。\n\n"
        "### 驱动因素分析\n"
        "分析导致近期涨跌的核心因素（可能包括：行业政策、财报预期、资金面、宏观环境、"
        "竞争格局变化、管理层动作等），每个因素1-2句话，至少分析2-3个因素。"
        "如果数据不足，可基于该公司所处行业的一般性分析。\n\n"
        "### 价值投资视角\n"
        "站在巴菲特的角度，当前价格相对于公司内在价值是便宜了还是贵了？"
        "结合PE、ROE、护城河评分给出判断。"
        "如果股价下跌，判断是\"市场先生的恐慌\"还是\"基本面确实恶化\"。"
        "如果股价上涨，判断是\"合理价值回归\"还是\"市场先生过度乐观\"。\n\n"
        "### 段永平视角\n"
        "用1-2句话，从段永平\"本分\"和\"Stop Doing List\"角度点评：这家公司的生意模式是否经得起考验？"
        "管理层是否在做对的事？\n\n"
        "### 阶段性结论\n"
        "用1句话给出明确的阶段性判断（如：\"短期承压但长期逻辑未变，回调即是布局机会\"），不能模棱两可。\n\n"
        "要求：\n"
        "1. 语气专业但平易近人，像一位值得信赖的投资顾问在跟你聊天\n"
        "2. 每个观点都要有数据支撑，不说空话\n"
        "3. 不要出现\"仅供参考\"\"投资有风险\"等套话\n"
        "4. 总长度控制在300-500字"
    )

    try:
        return _call_llm(provider, [{"role": "user", "content": prompt}], max_tokens=1500)
    except Exception as e:
        logger.warning("Trend report failed for %s: %s", symbol, e)
        return None
