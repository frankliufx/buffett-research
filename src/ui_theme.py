"""高端金融风 UI 主题 — 极简黑底白字 + 巴菲特投研"""

import random
from datetime import datetime

# 高端金融色系 — Blackstone 风格
COLORS = {
    "primary": "#C9A962",       # 金色点缀
    "primary_light": "#D4BC7C",
    "primary_dark": "#A88B3D",
    "bg": "#0B0B0F",            # 深黑底
    "bg_card": "#141419",       # 卡片底
    "bg_sidebar": "#101015",    # 侧边栏
    "bg_elevated": "#1A1A21",   # 悬浮层
    "text": "#F0F0F2",          # 主文字白
    "text_secondary": "#A8A8B0",
    "text_muted": "#6B6B75",
    "border": "#2A2A33",
    "border_light": "#1E1E26",
    "success": "#3ECF8E",
    "warning": "#F5A623",
    "danger": "#EF4444",
    "info": "#60A5FA",
    "gold": "#C9A962",
    # 评级色
    "grade_S": "#C9A962",
    "grade_A": "#3ECF8E",
    "grade_B": "#60A5FA",
    "grade_C": "#F5A623",
    "grade_D": "#EF4444",
}


def get_global_css():
    return """
<style>
    /* ===== 高端金融风 — 极简黑底 ===== */

    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400&family=Inter:wght@300;400;500;600;700;800&display=swap');

    .stApp {
        background-color: %(bg)s;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        letter-spacing: 0.01em;
        color: %(text)s;
    }

    /* 全局文字颜色覆盖 */
    .stApp p, .stApp span, .stApp label, .stApp div {
        color: %(text)s;
    }
    .stApp .stMarkdown p {
        color: %(text_secondary)s;
        line-height: 1.7;
    }

    /* ===== 侧边栏 ===== */
    [data-testid="stSidebar"] {
        background-color: %(bg_sidebar)s;
        border-right: 1px solid %(border)s;
    }
    [data-testid="stSidebar"] .stMarkdown p {
        font-size: 0.88rem;
        color: %(text_secondary)s;
    }

    /* ===== Hero 头部 ===== */
    .hero-header {
        text-align: center;
        padding: 3rem 2rem 2.5rem;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid %(border)s;
    }
    .hero-header h1 {
        color: %(text)s;
        font-size: 2rem;
        font-weight: 300;
        margin: 0;
        letter-spacing: 8px;
        text-transform: uppercase;
    }
    .hero-header .hero-divider {
        width: 40px;
        height: 1px;
        background: %(primary)s;
        margin: 1rem auto;
    }
    .hero-header p {
        color: %(text_muted)s;
        font-size: 0.85rem;
        margin: 0;
        letter-spacing: 4px;
        font-weight: 300;
    }
    .hero-header .hero-date {
        color: %(text_muted)s;
        font-size: 0.75rem;
        margin-top: 1rem;
        letter-spacing: 2px;
        font-weight: 400;
    }

    /* ===== 巴菲特语录 ===== */
    .buffett-quote {
        border-left: 2px solid %(primary)s;
        padding: 0.8rem 1.2rem;
        margin: 0.5rem 0 1.5rem 0;
        color: %(text_muted)s;
        font-size: 0.88rem;
        font-style: italic;
        line-height: 1.7;
    }
    .buffett-quote .author {
        display: block;
        text-align: right;
        margin-top: 0.4rem;
        font-style: normal;
        font-weight: 500;
        color: %(primary)s;
        font-size: 0.8rem;
        letter-spacing: 1px;
    }

    /* ===== 卡片系统 ===== */
    .metric-card {
        background: %(bg_card)s;
        border: 1px solid %(border)s;
        border-radius: 8px;
        padding: 1.2rem;
        transition: border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: %(primary)s;
    }

    /* 股票头部 */
    .stock-header-card {
        background: %(bg_card)s;
        border: 1px solid %(border)s;
        border-radius: 8px;
        padding: 1.5rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .stock-header-left .stock-name {
        font-size: 1.2rem;
        font-weight: 600;
        color: %(text)s;
        letter-spacing: 1px;
    }
    .stock-header-left .stock-name span {
        color: %(text_muted)s;
        font-weight: 400;
        font-size: 0.95rem;
        margin-left: 10px;
    }
    .stock-header-left .stock-price {
        font-size: 2.4rem;
        font-weight: 700;
        color: %(text)s;
        margin: 6px 0;
        letter-spacing: -0.5px;
        font-variant-numeric: tabular-nums;
    }
    .stock-header-left .stock-change {
        font-weight: 500;
        font-size: 0.95rem;
        font-variant-numeric: tabular-nums;
    }
    .stock-header-right {
        text-align: center;
    }
    .stock-header-right .moat-label-text {
        font-size: 0.8rem;
        font-weight: 500;
        margin-top: 8px;
        letter-spacing: 1px;
    }
    .stock-header-right .moat-score-text {
        font-size: 0.72rem;
        color: %(text_muted)s;
        margin-top: 3px;
        letter-spacing: 0.5px;
    }

    /* ===== KPI 指标卡片 ===== */
    .kpi-card {
        background: %(bg_card)s;
        border: 1px solid %(border)s;
        border-radius: 6px;
        padding: 0.9rem 1rem;
        text-align: center;
        transition: border-color 0.2s;
    }
    .kpi-card:hover {
        border-color: %(primary)s;
    }
    .kpi-card .kpi-label {
        font-size: 0.7rem;
        color: %(text_muted)s;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 6px;
    }
    .kpi-card .kpi-value {
        font-size: 1.2rem;
        font-weight: 600;
        color: %(text)s;
        font-variant-numeric: tabular-nums;
    }
    .kpi-card .kpi-value.positive { color: %(success)s; }
    .kpi-card .kpi-value.negative { color: %(danger)s; }
    .kpi-card .kpi-value.warning { color: %(warning)s; }

    /* ===== 评级徽章 ===== */
    .grade-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 56px;
        height: 56px;
        border-radius: 8px;
        font-size: 1.8rem;
        font-weight: 700;
        color: %(bg)s;
        letter-spacing: -1px;
    }
    .grade-badge-sm {
        width: 32px;
        height: 32px;
        border-radius: 6px;
        font-size: 0.9rem;
        font-weight: 700;
        color: %(bg)s;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }
    .grade-S, .grade-sm-S { background: %(grade_S)s; }
    .grade-A, .grade-sm-A { background: %(grade_A)s; }
    .grade-B, .grade-sm-B { background: %(grade_B)s; }
    .grade-C, .grade-sm-C { background: %(grade_C)s; }
    .grade-D, .grade-sm-D { background: %(grade_D)s; }

    /* ===== 护城河标签 ===== */
    .moat-label {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 500;
        letter-spacing: 0.5px;
    }

    /* ===== 进度条 ===== */
    .moat-bar-container {
        background: %(bg_elevated)s;
        border-radius: 2px;
        height: 4px;
        overflow: hidden;
        margin: 4px 0 10px 0;
    }
    .moat-bar-fill {
        height: 100%%;
        border-radius: 2px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ===== 护城河维度卡 ===== */
    .moat-dim-card {
        border-bottom: 1px solid %(border_light)s;
        padding: 0.8rem 0;
    }
    .moat-dim-card:last-child {
        border-bottom: none;
    }
    .moat-dim-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }
    .moat-dim-header .dim-name {
        font-weight: 500;
        font-size: 0.88rem;
        color: %(text_secondary)s;
    }
    .moat-dim-header .dim-score {
        font-weight: 600;
        font-size: 0.85rem;
        font-variant-numeric: tabular-nums;
    }

    /* ===== Tab 样式 ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid %(border)s;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 0;
        padding: 10px 20px;
        font-weight: 400;
        color: %(text_muted)s;
        border-bottom: 2px solid transparent;
        font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] {
        color: %(text)s !important;
        font-weight: 600;
        border-bottom: 2px solid %(primary)s !important;
        background: transparent !important;
    }

    /* ===== 细节项 ===== */
    .detail-item {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 7px 0;
        border-bottom: 1px solid %(border_light)s;
    }
    .detail-item:last-child {
        border-bottom: none;
    }
    .detail-icon {
        font-size: 0.9rem;
        min-width: 20px;
        text-align: center;
    }
    .detail-text {
        font-size: 0.88rem;
        color: %(text_secondary)s;
        line-height: 1.5;
    }
    .detail-high { color: %(success)s; }
    .detail-medium { color: %(primary)s; }
    .detail-low { color: %(warning)s; }
    .detail-negative { color: %(danger)s; }

    /* ===== 侧边栏状态 ===== */
    .sidebar-status-card {
        background: %(bg_card)s;
        border: 1px solid %(border)s;
        border-radius: 6px;
        padding: 0.7rem 0.9rem;
        margin-bottom: 0.6rem;
    }
    .sidebar-status-card .status-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%%;
        margin-right: 6px;
    }

    /* ===== 空状态 ===== */
    .empty-state {
        text-align: center;
        padding: 3rem 2rem;
        color: %(text_muted)s;
    }
    .empty-state .empty-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        opacity: 0.4;
    }

    /* ===== Streamlit 组件覆盖 ===== */
    .stSelectbox label, .stTextInput label, .stNumberInput label {
        color: %(text_secondary)s !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }

    /* metric 组件 */
    [data-testid="stMetric"] {
        background: %(bg_card)s;
        border: 1px solid %(border)s;
        border-radius: 6px;
        padding: 0.8rem 1rem;
    }
    [data-testid="stMetric"] label {
        color: %(text_muted)s !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: %(text)s;
        font-variant-numeric: tabular-nums;
    }

    /* expander */
    .streamlit-expanderHeader {
        background: %(bg_card)s !important;
        border: 1px solid %(border)s !important;
        border-radius: 6px !important;
        color: %(text_secondary)s !important;
    }

    /* dataframe */
    .stDataFrame {
        border: 1px solid %(border)s;
        border-radius: 6px;
    }

    /* 分隔线 */
    hr {
        border: none;
        border-top: 1px solid %(border)s;
        margin: 1.2rem 0;
    }

    /* 隐藏默认 footer */
    footer { visibility: hidden; }

    /* ===== 滚动条 ===== */
    ::-webkit-scrollbar {
        width: 5px;
        height: 5px;
    }
    ::-webkit-scrollbar-track {
        background: %(bg)s;
    }
    ::-webkit-scrollbar-thumb {
        background: %(border)s;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: %(text_muted)s;
    }

    /* ===== 新闻信息流 ===== */
    .news-section-title {
        font-size: 0.7rem;
        color: %(text_muted)s;
        letter-spacing: 1.5px;
        font-weight: 600;
        margin-bottom: 8px;
        padding-bottom: 6px;
        border-bottom: 1px solid %(border_light)s;
    }
    .news-item {
        padding: 8px 0;
        border-bottom: 1px solid %(border_light)s;
        transition: opacity 0.15s;
    }
    .news-item:last-child {
        border-bottom: none;
    }
    .news-item:hover {
        opacity: 0.85;
    }
    .news-item .news-title {
        font-size: 0.82rem;
        color: %(text)s;
        line-height: 1.45;
        font-weight: 400;
        display: block;
        text-decoration: none;
    }
    .news-item .news-title:hover {
        color: %(primary)s;
    }
    .news-item .news-meta {
        font-size: 0.68rem;
        color: %(text_muted)s;
        margin-top: 3px;
        letter-spacing: 0.3px;
    }
    .news-item .news-source {
        color: %(primary)s;
        font-weight: 500;
    }

    /* 财报日历卡 */
    .calendar-card {
        background: %(bg_card)s;
        border: 1px solid %(border)s;
        border-radius: 6px;
        padding: 0.7rem 0.9rem;
        margin-bottom: 6px;
    }
    .calendar-card .cal-label {
        font-size: 0.68rem;
        color: %(text_muted)s;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    .calendar-card .cal-value {
        font-size: 0.88rem;
        color: %(text)s;
        font-weight: 600;
        margin-top: 2px;
        font-variant-numeric: tabular-nums;
    }
    .calendar-card .cal-sub {
        font-size: 0.72rem;
        color: %(text_muted)s;
        margin-top: 1px;
    }

    /* 侧边栏新闻区分隔 */
    .sidebar-section {
        margin-bottom: 1rem;
    }

    /* ===== 免责声明 ===== */
    .disclaimer {
        text-align: center;
        color: %(text_muted)s;
        font-size: 0.72rem;
        letter-spacing: 1px;
        padding: 1.5rem 0;
        border-top: 1px solid %(border_light)s;
        margin-top: 2rem;
    }

    /* ===== AI 投资结论横幅 ===== */
    .verdict-banner {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 14px 20px;
        border-radius: 4px;
        border: 1px solid;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
    .verdict-buy    { background: rgba(62,207,142,0.07); border-color: rgba(62,207,142,0.5); }
    .verdict-accumulate { background: rgba(62,207,142,0.04); border-color: rgba(62,207,142,0.3); }
    .verdict-hold   { background: rgba(96,165,250,0.07); border-color: rgba(96,165,250,0.4); }
    .verdict-reduce { background: rgba(245,166,35,0.07); border-color: rgba(245,166,35,0.4); }
    .verdict-avoid  { background: rgba(239,68,68,0.07); border-color: rgba(239,68,68,0.4); }

    .verdict-action {
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 2px;
        padding: 5px 14px;
        border-radius: 3px;
        white-space: nowrap;
    }
    .verdict-buy    .verdict-action { color: %(success)s; background: rgba(62,207,142,0.12); }
    .verdict-accumulate .verdict-action { color: %(success)s; background: rgba(62,207,142,0.08); }
    .verdict-hold   .verdict-action { color: %(info)s; background: rgba(96,165,250,0.12); }
    .verdict-reduce .verdict-action { color: %(warning)s; background: rgba(245,166,35,0.12); }
    .verdict-avoid  .verdict-action { color: %(danger)s; background: rgba(239,68,68,0.12); }

    .verdict-confidence {
        font-size: 0.68rem;
        letter-spacing: 1.5px;
        color: %(text_muted)s;
        white-space: nowrap;
        text-transform: uppercase;
    }
    .verdict-reason {
        font-size: 0.88rem;
        color: %(text_secondary)s;
        line-height: 1.5;
        flex: 1;
        min-width: 160px;
    }
    .verdict-label {
        font-size: 0.65rem;
        letter-spacing: 3px;
        color: %(text_muted)s;
        text-transform: uppercase;
        margin-right: 8px;
    }

    /* ===== 维度卡片 V2 ===== */
    .dim-card-v2 {
        background: %(bg_card)s;
        border: 1px solid %(border_light)s;
        padding: 12px 14px;
        margin-bottom: 7px;
        transition: border-color 0.2s;
    }
    .dim-card-v2:hover { border-color: %(border)s; }
    .dim-header-v2 {
        display: flex;
        align-items: center;
        gap: 7px;
        margin-bottom: 7px;
    }
    .dim-icon-v2 { font-size: 0.88rem; flex-shrink: 0; }
    .dim-name-v2 {
        font-size: 0.78rem;
        font-weight: 600;
        color: %(text_secondary)s;
        flex: 1;
        letter-spacing: 0.3px;
    }
    .dim-score-v2 {
        font-size: 0.75rem;
        font-weight: 700;
        color: %(primary)s;
        font-variant-numeric: tabular-nums;
    }
    .dim-bar-bg-v2 {
        height: 3px;
        background: %(border_light)s;
        border-radius: 2px;
        margin-bottom: 7px;
        overflow: hidden;
    }
    .dim-bar-fill-v2 {
        height: 100%%;
        border-radius: 2px;
        transition: width 0.7s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .dim-ai-v2 {
        font-size: 0.73rem;
        color: %(text_muted)s;
        line-height: 1.4;
    }
    .dim-ai-v2.has-insight { color: #8A8A9A; }

    /* ===== 左侧评级面板 ===== */
    .grade-panel {
        background: %(bg_card)s;
        border: 1px solid %(border_light)s;
        padding: 20px 16px;
        text-align: center;
        height: 100%%;
    }
    .grade-panel .score-big {
        font-size: 2.2rem;
        font-weight: 700;
        color: %(primary)s;
        letter-spacing: -2px;
        line-height: 1;
        margin: 12px 0 4px;
        font-variant-numeric: tabular-nums;
    }
    .grade-panel .score-label {
        font-size: 0.68rem;
        color: %(text_muted)s;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .grade-panel .grade-stat-row {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid %(border_light)s;
        font-size: 0.78rem;
    }
    .grade-panel .grade-stat-row:last-child { border-bottom: none; }
    .grade-panel .stat-k { color: %(text_muted)s; }
    .grade-panel .stat-v { color: %(text_secondary)s; font-weight: 500; }

    /* ===== 多空理由栏 ===== */
    .bb-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-top: 16px;
    }
    .bb-col {
        padding: 14px 16px;
        border-radius: 3px;
    }
    .bb-bull { background: rgba(62,207,142,0.05); border: 1px solid rgba(62,207,142,0.15); }
    .bb-bear { background: rgba(239,68,68,0.05); border: 1px solid rgba(239,68,68,0.15); }
    .bb-title {
        font-size: 0.68rem;
        letter-spacing: 2px;
        font-weight: 600;
        margin-bottom: 10px;
        text-transform: uppercase;
    }
    .bb-bull .bb-title { color: %(success)s; }
    .bb-bear .bb-title { color: %(danger)s; }
    .bb-item {
        font-size: 0.78rem;
        color: %(text_muted)s;
        padding: 4px 0;
        line-height: 1.4;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .bb-item:last-child { border-bottom: none; }

    /* ===== Mobile Responsive ===== */
    @media (max-width: 768px) {
        /* Sidebar auto-collapse on mobile */
        [data-testid="stSidebar"] { min-width: 0 !important; }

        /* Stack columns vertically */
        .stApp .block-container { padding: 0.5rem 0.8rem !important; max-width: 100% !important; }

        /* Make metric cards full-width */
        .metric-card { padding: 0.6rem !important; }
        .metric-card .value { font-size: 1.1rem !important; }

        /* KPI cards responsive */
        .kpi-card { padding: 8px 10px !important; }
        .kpi-card .kpi-value { font-size: 1rem !important; }

        /* Hero header compact */
        .hero-header { padding: 1.5rem 1rem !important; }
        .hero-header h1 { font-size: 1.3rem !important; }

        /* Plotly charts responsive */
        .js-plotly-plot { width: 100% !important; }

        /* Tabs - horizontal scroll on mobile */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            -webkit-overflow-scrolling: touch;
        }
        .stTabs [data-baseweb="tab"] {
            white-space: nowrap !important;
            font-size: 0.7rem !important;
            padding: 8px 12px !important;
        }

        /* Tables - smaller font on mobile */
        .stApp table { font-size: 0.7rem !important; }

        /* Chat input fix */
        .stChatInput { max-width: 100% !important; }

        /* Expander text */
        .stApp details summary span { font-size: 0.8rem !important; }
    }

    /* Small phones */
    @media (max-width: 480px) {
        .stApp .block-container { padding: 0.3rem 0.5rem !important; }
        .hero-header { padding: 1rem 0.5rem !important; }
        .hero-header h1 { font-size: 1.1rem !important; }
    }

</style>
""" % COLORS


BUFFETT_AVATAR_SVG = """
<svg width="80" height="80" viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg_grad" x1="0%%" y1="0%%" x2="100%%" y2="100%%">
      <stop offset="0%%" style="stop-color:#A88B3D"/>
      <stop offset="100%%" style="stop-color:#C9A962"/>
    </linearGradient>
  </defs>
  <rect width="80" height="80" rx="12" fill="url(#bg_grad)"/>
  <circle cx="30" cy="34" r="9" fill="none" stroke="#0B0B0F" stroke-width="2.5"/>
  <circle cx="52" cy="34" r="9" fill="none" stroke="#0B0B0F" stroke-width="2.5"/>
  <line x1="39" y1="34" x2="43" y2="34" stroke="#0B0B0F" stroke-width="2"/>
  <line x1="21" y1="32" x2="18" y2="30" stroke="#0B0B0F" stroke-width="2"/>
  <line x1="61" y1="32" x2="64" y2="30" stroke="#0B0B0F" stroke-width="2"/>
  <circle cx="30" cy="35" r="2.5" fill="#0B0B0F"/>
  <circle cx="52" cy="35" r="2.5" fill="#0B0B0F"/>
  <path d="M 30 48 Q 41 56 52 48" fill="none" stroke="#0B0B0F" stroke-width="2.5" stroke-linecap="round"/>
  <polygon points="41,60 37,70 41,67 45,70" fill="#0B0B0F" opacity="0.8"/>
</svg>
"""


def render_buffett_quote():
    from src.ai.knowledge_base import BUFFETT_QUOTES
    quote = random.choice(BUFFETT_QUOTES)
    return """
<div class="buffett-quote">
    "{}"
    <span class="author">-- Warren Buffett</span>
</div>
""".format(quote)


def render_hero_header():
    now = datetime.now()
    date_str = now.strftime("%Y.%m.%d")
    weekdays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    weekday = weekdays[now.weekday()]
    return """
<div class="hero-header">
    <h1>BUFFETT RESEARCH</h1>
    <div class="hero-divider"></div>
    <p>VALUE INVESTING · MOAT ANALYSIS · AI ADVISORY</p>
    <div class="hero-date">{} · {}</div>
</div>
""".format(date_str, weekday)


def render_grade_badge(grade, size="normal"):
    if size == "sm":
        return '<div class="grade-badge-sm grade-sm-{}">{}</div>'.format(grade, grade)
    return '<div class="grade-badge grade-{}">{}</div>'.format(grade, grade)


def render_moat_bar(score, max_score, color="#C9A962"):
    pct = (score / max_score * 100) if max_score > 0 else 0
    return """
<div class="moat-bar-container">
    <div class="moat-bar-fill" style="width: {:.0f}%; background: {};"></div>
</div>
""".format(pct, color)


def render_detail_item(icon, text, level="medium"):
    icon_map = {"✓": "✅", "✗": "❌", "△": "⚠️", "-": "ℹ️"}
    emoji = icon_map.get(icon, icon)
    return """
<div class="detail-item">
    <span class="detail-icon">{}</span>
    <span class="detail-text detail-{}">{}</span>
</div>
""".format(emoji, level, text)


def render_kpi_card(label, value, color_class=""):
    return """
<div class="kpi-card">
    <div class="kpi-label">{}</div>
    <div class="kpi-value {}">{}</div>
</div>
""".format(label, color_class, value)


def render_moat_dimension(icon, name, score, max_score, color):
    pct = score / max_score * 100 if max_score > 0 else 0
    score_color = COLORS["success"] if pct >= 60 else (COLORS["warning"] if pct >= 40 else COLORS["danger"])
    return """
<div class="moat-dim-card">
    <div class="moat-dim-header">
        <span class="dim-name">{icon} {name}</span>
        <span class="dim-score" style="color:{score_color};">{score}/{max_s}</span>
    </div>
    <div class="moat-bar-container">
        <div class="moat-bar-fill" style="width: {pct:.0f}%; background: {color};"></div>
    </div>
</div>
""".format(icon=icon, name=name, score=score, max_s=max_score,
           score_color=score_color, pct=pct, color=color)


def render_stock_header(symbol, name, price, change, grade, moat_label, moat_color, moat_pct):
    change_color = COLORS["success"] if change >= 0 else COLORS["danger"]
    price_str = "{:.2f}".format(price) if price else "--"
    change_str = "{:+.2f}".format(change) if change else "0.00"
    badge = render_grade_badge(grade)

    return """
<div class="stock-header-card">
    <div class="stock-header-left">
        <div class="stock-name">{sym}<span>{name}</span></div>
        <div class="stock-price">{price}</div>
        <div class="stock-change" style="color:{chg_color};">{chg}%%</div>
    </div>
    <div class="stock-header-right">
        {badge}
        <div class="moat-label-text" style="color:{moat_color};">{moat_label}</div>
        <div class="moat-score-text">{moat_pct:.0f} / 100</div>
    </div>
</div>
""".format(sym=symbol, name=name, price=price_str, chg=change_str,
           chg_color=change_color, badge=badge,
           moat_label=moat_label, moat_color=moat_color, moat_pct=moat_pct)


def render_sidebar_status(provider_name, model_name, is_connected=True):
    dot_color = COLORS["success"] if is_connected else COLORS["danger"]
    status_text = "ACTIVE" if is_connected else "INACTIVE"
    return """
<div class="sidebar-status-card">
    <div style="font-size:0.7rem; color:{muted}; letter-spacing:1px; margin-bottom:3px;">AI MODEL</div>
    <div style="font-weight:600; color:{text}; font-size:0.9rem;">
        <span class="status-dot" style="background:{dot};"></span>
        {name}
    </div>
    <div style="font-size:0.72rem; color:{muted}; margin-top:2px;">{model} · {status}</div>
</div>
""".format(name=provider_name, model=model_name[:28],
           dot=dot_color, status=status_text,
           text=COLORS["text"], muted=COLORS["text_muted"])


def render_news_item(title, source="", time_str="", url=""):
    if url:
        title_html = '<a href="{}" target="_blank" class="news-title">{}</a>'.format(url, title)
    else:
        title_html = '<span class="news-title">{}</span>'.format(title)
    meta_parts = []
    if source:
        meta_parts.append('<span class="news-source">{}</span>'.format(source))
    if time_str:
        meta_parts.append(time_str)
    meta_html = ' · '.join(meta_parts)
    return """
<div class="news-item">
    {title}
    <div class="news-meta">{meta}</div>
</div>
""".format(title=title_html, meta=meta_html)


def render_calendar_card(label, value, sub=""):
    sub_html = '<div class="cal-sub">{}</div>'.format(sub) if sub else ""
    return """
<div class="calendar-card">
    <div class="cal-label">{}</div>
    <div class="cal-value">{}</div>
    {}
</div>
""".format(label, value, sub_html)


def render_empty_state(icon, title, description=""):
    desc_html = "<p style='font-size:0.85rem;'>{}</p>".format(description) if description else ""
    return """
<div class="empty-state">
    <div class="empty-icon">{}</div>
    <div style="font-weight:500; font-size:0.95rem; color:{}; margin-bottom:0.3rem;">{}</div>
    {}
</div>
""".format(icon, COLORS["text_secondary"], title, desc_html)
