"""首页 — AI-Powered Buffett Research"""

import random
import streamlit as st
import streamlit.components.v1 as components
from src.ui_theme import get_global_css, COLORS
from src.ai.knowledge_base import BUFFETT_QUOTES, DUAN_YONGPING_QUOTES
from src.data.macro import get_buffett_indicator

st.markdown(get_global_css(), unsafe_allow_html=True)

# ── 数据准备 ─────────────────────────────────────────────────────
bi_data = get_buffett_indicator()
buffett_q = random.choice(BUFFETT_QUOTES)
duan_q = random.choice(DUAN_YONGPING_QUOTES)


# ── 辅助函数 ─────────────────────────────────────────────────────
def _gauge_html(ratio):
    segs = (
        '<div style="width:35%;height:100%;background:#3ECF8E;"></div>'
        '<div style="width:10%;height:100%;background:#60A5FA;"></div>'
        '<div style="width:15%;height:100%;background:#C9A962;"></div>'
        '<div style="width:15%;height:100%;background:#F5A623;"></div>'
        '<div style="width:25%;height:100%;background:#EF4444;"></div>'
    )
    if ratio <= 70:
        pos = ratio / 70 * 35
    elif ratio <= 90:
        pos = 35 + (ratio - 70) / 20 * 10
    elif ratio <= 120:
        pos = 45 + (ratio - 90) / 30 * 15
    elif ratio <= 150:
        pos = 60 + (ratio - 120) / 30 * 15
    else:
        pos = min(75 + (ratio - 150) / 50 * 25, 100)
    return (
        '<div style="height:5px;background:#1E1E26;border-radius:3px;margin:14px 0 6px;position:relative;display:flex;overflow:hidden;">'
        + segs
        + '<div style="position:absolute;top:-4px;left:' + str(round(pos, 1)) + '%;width:3px;height:13px;background:#EAEAEA;border-radius:1px;transform:translateX(-50%);"></div>'
        '</div>'
        '<div style="display:flex;justify-content:space-between;font-size:0.56rem;color:#3A3A46;margin-top:2px;">'
        '<span>0%</span><span>70%</span><span>90%</span><span>120%</span><span>150%</span><span>200%+</span>'
        '</div>'
    )


def _bi_card(d):
    live_color = "#3ECF8E" if d["is_live"] else "#5A5A68"
    live_text = "LIVE" if d["is_live"] else "REF"
    c = d["color"]
    return (
        '<div style="background:#0F0F14;border:1px solid #1E1E26;border-radius:4px;padding:24px;overflow:hidden;">'
        # header
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">'
        '<span style="font-size:0.95rem;font-weight:600;color:#EAEAEA;letter-spacing:1px;">' + d["name"] + '</span>'
        '<span style="font-size:0.58rem;padding:2px 8px;border-radius:2px;letter-spacing:1px;background:' + live_color + '22;color:' + live_color + ';">' + live_text + '</span>'
        '</div>'
        # ratio
        '<div style="font-size:2.4rem;font-weight:700;line-height:1;margin-bottom:4px;color:' + c + ';">' + str(d["ratio"]) + '%</div>'
        '<div style="font-size:0.68rem;color:#5A5A68;margin-bottom:14px;">总市值 / GDP</div>'
        # gauge
        + _gauge_html(d["ratio"])
        # verdict
        + '<div style="display:inline-block;font-size:0.78rem;font-weight:600;padding:3px 12px;border-radius:2px;margin-bottom:10px;background:' + c + '18;color:' + c + ';">' + d["label"] + '</div>'
        '<div style="font-size:0.78rem;color:#8A8A96;line-height:1.6;">' + d["advice"] + '</div>'
        '<div style="font-size:0.68rem;color:#3A3A46;margin-top:14px;line-height:1.5;">'
        '总市值 ' + str(d["market_cap"]) + d["unit"] + ' / GDP ' + str(d["gdp"]) + d["unit"]
        + '（' + str(d["gdp_year"]) + '）'
        ' &middot; 更新: ' + d["updated"]
        + '</div></div>'
    )


def _render_block(html, height=400):
    """用 components.html 渲染独立 HTML 区块，确保样式正确"""
    wrapper = (
        '<html><head><meta charset="utf-8">'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">'
        '<style>*{margin:0;padding:0;box-sizing:border-box;} body{background:#0B0B0F;font-family:Inter,-apple-system,sans-serif;color:#EAEAEA;padding:0 4px;}</style>'
        '</head><body>' + html + '</body></html>'
    )
    components.html(wrapper, height=height, scrolling=False)


# ═══════════════════════════════════════════════════════════════════
# HERO
# ═══════════════════════════════════════════════════════════════════
_render_block("""
<div style="padding:72px 0 56px;text-align:center;">
    <div style="font-size:0.68rem;letter-spacing:5px;color:#C9A962;text-transform:uppercase;margin-bottom:28px;font-weight:500;">AI-Powered Value Intelligence</div>
    <div style="font-size:clamp(2.2rem,5vw,3.6rem);font-weight:700;color:#EAEAEA;line-height:1.15;letter-spacing:-1px;margin-bottom:20px;">
        BUFFETT<br><span style="color:#C9A962;">RESEARCH</span>
    </div>
    <div style="display:inline-block;font-size:0.6rem;letter-spacing:3px;color:#0B0B0F;background:linear-gradient(135deg,#C9A962,#D4BC7C);padding:4px 16px;border-radius:2px;font-weight:700;margin-bottom:24px;">AI DRIVEN</div>
    <div style="font-size:1.05rem;color:#8A8A96;max-width:620px;margin:0 auto 44px;line-height:1.75;font-weight:300;">
        以巴菲特与段永平的价值投资体系为内核，以人工智能为引擎，<br>
        实时分析美股、港股、A股三大市场，为长期主义投资者提供专业级决策支持。
    </div>
    <div style="width:60px;height:2px;background:#C9A962;margin:0 auto;"></div>
</div>
<div style="display:flex;justify-content:center;gap:56px;padding:28px 0;border-top:1px solid #1E1E26;border-bottom:1px solid #1E1E26;">
    <div style="text-align:center;"><div style="font-size:1.8rem;font-weight:700;color:#C9A962;line-height:1;">AI</div><div style="font-size:0.68rem;color:#5A5A68;letter-spacing:2px;margin-top:6px;">深度分析引擎</div></div>
    <div style="text-align:center;"><div style="font-size:1.8rem;font-weight:700;color:#C9A962;line-height:1;">35+</div><div style="font-size:0.68rem;color:#5A5A68;letter-spacing:2px;margin-top:6px;">覆盖股票</div></div>
    <div style="text-align:center;"><div style="font-size:1.8rem;font-weight:700;color:#C9A962;line-height:1;">3</div><div style="font-size:0.68rem;color:#5A5A68;letter-spacing:2px;margin-top:6px;">全球市场</div></div>
    <div style="text-align:center;"><div style="font-size:1.8rem;font-weight:700;color:#C9A962;line-height:1;">5</div><div style="font-size:0.68rem;color:#5A5A68;letter-spacing:2px;margin-top:6px;">护城河维度</div></div>
    <div style="text-align:center;"><div style="font-size:1.8rem;font-weight:700;color:#C9A962;line-height:1;">100</div><div style="font-size:0.68rem;color:#5A5A68;letter-spacing:2px;margin-top:6px;">满分评分体系</div></div>
</div>
""", height=480)


# ═══════════════════════════════════════════════════════════════════
# BUFFETT INDICATOR
# ═══════════════════════════════════════════════════════════════════
_render_block(
    '<div style="padding:36px 0;border-bottom:1px solid #1E1E26;">'
    '<div style="font-size:0.65rem;letter-spacing:4px;color:#C9A962;text-transform:uppercase;margin-bottom:10px;font-weight:500;">Buffett Indicator</div>'
    '<div style="font-size:1.7rem;font-weight:700;color:#EAEAEA;margin-bottom:14px;">市场估值水位</div>'
    '<div style="font-size:0.92rem;color:#6A6A78;line-height:1.8;max-width:680px;">'
    '巴菲特指标 = 股市总市值 / GDP，被誉为判断市场整体估值的万能标尺。<br>'
    '低于 70% 严重低估，70-90% 合理偏低，90-120% 合理区间，120-150% 偏高，超过 150% 严重高估。'
    '</div>'
    '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:28px;">'
    + _bi_card(bi_data["cn"])
    + _bi_card(bi_data["us"])
    + _bi_card(bi_data["hk"])
    + '</div></div>',
    height=420,
)


# ═══════════════════════════════════════════════════════════════════
# FEATURES (用 Streamlit columns，简单结构不会被 sanitize)
# ═══════════════════════════════════════════════════════════════════
st.markdown("---")

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("##### AI 驱动的专业投研体系")
    st.caption("将巴菲特七十年投资智慧与段永平的实战哲学系统化，以 AI 为引擎构建可量化、可执行的价值投资决策框架。")

with col2:
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.markdown("**护城河评估**")
        st.caption("ROE 一致性、净利率五个维度量化企业竞争壁垒")
    with r1c2:
        st.markdown("**安全边际分析**")
        st.caption("PE/PB/股息率三重验证，25% 安全边际标准")
    with r1c3:
        st.markdown("**财务健康诊断**")
        st.caption("负债率、流动比率、自由现金流全面扫描")

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        st.markdown("**技术信号辅助**")
        st.caption("MA/RSI/布林带综合研判，辅助择时决策")
    with r2c2:
        st.markdown("**AI 深度研报**")
        st.caption("AI 引擎生成巴菲特视角的个股深度研究报告")
    with r2c3:
        st.markdown("**AI 投资顾问**")
        st.caption("对话式 AI 投顾，随时解答投资疑问")


# ═══════════════════════════════════════════════════════════════════
# PHILOSOPHY QUOTES
# ═══════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("##### 两位大师的智慧结晶")

col_b, col_d = st.columns(2)
with col_b:
    st.markdown("> *\"" + buffett_q + "\"*")
    st.caption("— Warren Buffett, 伯克希尔哈撒韦董事长")
with col_d:
    st.markdown("> *\"" + duan_q + "\"*")
    st.caption("— 段永平, 步步高创始人")


# ═══════════════════════════════════════════════════════════════════
# MARKET COVERAGE
# ═══════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("##### 三大市场，一站覆盖")

mc1, mc2, mc3 = st.columns(3)
with mc1:
    st.metric("US MARKET", "13 只", "纽交所 + 纳斯达克")
with mc2:
    st.metric("HK MARKET", "9 只", "香港联合交易所")
with mc3:
    st.metric("A-SHARE", "12 只", "沪深两市")


# ═══════════════════════════════════════════════════════════════════
# TOOLBOX
# ═══════════════════════════════════════════════════════════════════
_render_block("""
<div style="padding:36px 0;">
    <div style="font-size:0.65rem;letter-spacing:4px;color:#C9A962;text-transform:uppercase;margin-bottom:10px;font-weight:500;">Investor Toolbox</div>
    <div style="font-size:1.7rem;font-weight:700;color:#EAEAEA;margin-bottom:14px;">实用工具箱</div>
    <div style="font-size:0.92rem;color:#6A6A78;line-height:1.8;max-width:680px;margin-bottom:24px;">
        按 <strong style="color:#BDBDBD;">资讯感知 &middot; 交易执行 &middot; 专业看盘 &middot; 观点交流</strong> 四大场景分类，覆盖投资全流程。
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
        <!-- 01 资讯 -->
        <div style="background:#0F0F14;border:1px solid #1E1E26;padding:22px 20px;display:flex;gap:16px;">
            <div style="font-size:1.6rem;font-weight:700;color:#1E1E26;line-height:1;width:28px;flex-shrink:0;">01</div>
            <div>
                <div style="font-size:0.6rem;color:#C9A962;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;font-weight:500;">资讯 &middot; 市场发生了什么</div>
                <div style="font-size:0.95rem;font-weight:600;color:#EAEAEA;margin-bottom:6px;">财联社</div>
                <div style="font-size:0.78rem;color:#6A6A78;line-height:1.6;">普通投资者首选，实时快讯、行情资讯全覆盖，一个 APP 够用。</div>
                <div style="font-size:0.68rem;color:#4A4A56;line-height:1.5;margin-top:8px;padding-top:8px;border-top:1px solid #1A1A22;">
                    <strong style="color:#7A7A88;">万得金融终端</strong> &mdash; 机构从业者标配，金融牛马必备<br>
                    <strong style="color:#7A7A88;">财经早餐 / 下午茶</strong> &mdash; 官方公众号直达，免下载
                </div>
            </div>
        </div>
        <!-- 02 交易 -->
        <div style="background:#0F0F14;border:1px solid #1E1E26;padding:22px 20px;display:flex;gap:16px;">
            <div style="font-size:1.6rem;font-weight:700;color:#1E1E26;line-height:1;width:28px;flex-shrink:0;">02</div>
            <div>
                <div style="font-size:0.6rem;color:#C9A962;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;font-weight:500;">交易 &middot; 执行买卖操作</div>
                <div style="font-size:0.95rem;font-weight:600;color:#EAEAEA;margin-bottom:6px;">华泰证券</div>
                <div style="font-size:0.78rem;color:#6A6A78;line-height:1.6;">主流券商交易体验大差不差，功能齐全稳定可靠。</div>
                <div style="font-size:0.68rem;color:#4A4A56;line-height:1.5;margin-top:8px;padding-top:8px;border-top:1px solid #1A1A22;">
                    <strong style="color:#C9A962;">券商 AI 辅助</strong> &mdash; 底层数据与交易后台同源，靠谱准确不会乱编，远优于通用 AI
                </div>
            </div>
        </div>
        <!-- 03 工具 -->
        <div style="background:#0F0F14;border:1px solid #1E1E26;padding:22px 20px;display:flex;gap:16px;">
            <div style="font-size:1.6rem;font-weight:700;color:#1E1E26;line-height:1;width:28px;flex-shrink:0;">03</div>
            <div>
                <div style="font-size:0.6rem;color:#C9A962;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;font-weight:500;">工具 &middot; 专业筛选看盘</div>
                <div style="font-size:0.95rem;font-weight:600;color:#EAEAEA;margin-bottom:6px;">开盘</div>
                <div style="font-size:0.78rem;color:#6A6A78;line-height:1.6;">短线选手首选，内置市场情绪、题材库、数据统计等核心功能，值得深入研究。</div>
                <div style="font-size:0.68rem;color:#4A4A56;line-height:1.5;margin-top:8px;padding-top:8px;border-top:1px solid #1A1A22;">
                    <strong style="color:#7A7A88;">同花顺（电脑端）</strong> &mdash; K 线图表可视化效果佳，盘面分析更便捷
                </div>
            </div>
        </div>
        <!-- 04 社群 -->
        <div style="background:#0F0F14;border:1px solid #1E1E26;padding:22px 20px;display:flex;gap:16px;">
            <div style="font-size:1.6rem;font-weight:700;color:#1E1E26;line-height:1;width:28px;flex-shrink:0;">04</div>
            <div>
                <div style="font-size:0.6rem;color:#C9A962;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;font-weight:500;">社群 &middot; 听听其他投资者</div>
                <div style="font-size:0.95rem;font-weight:600;color:#EAEAEA;margin-bottom:6px;">雪球</div>
                <div style="font-size:0.78rem;color:#6A6A78;line-height:1.6;">股民质量相对较高，汇聚各路投资者讨论，可参考观点，偶尔用作反向指标。</div>
            </div>
        </div>
    </div>
</div>
""", height=480)


# ═══════════════════════════════════════════════════════════════════
# HOW IT WORKS
# ═══════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("##### 三步完成专业级分析")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**01 &nbsp; 选择股票**")
    st.caption("在关注列表中选择目标公司，或通过侧边栏快速添加自定义股票。")
with c2:
    st.markdown("**02 &nbsp; 获取分析**")
    st.caption("系统自动抓取实时行情与财务数据，生成护城河五维度量化评分。")
with c3:
    st.markdown("**03 &nbsp; AI 研报**")
    st.caption("一键生成 AI 深度研报，获得巴菲特视角的解读和明确投资建议。")


# ═══════════════════════════════════════════════════════════════════
# CTA + DISCLAIMER
# ═══════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 开始你的价值投资之旅")
st.caption("点击左侧导航栏 Analysis，让 AI 帮你分析关注的股票")
st.markdown("")
st.caption("DISCLAIMER: FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY. NOT FINANCIAL ADVICE.")
