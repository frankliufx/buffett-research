"""A股专属 UI 渲染组件

暗色金融主题（#08080C 背景，#C9A962 金色，Cormorant Garamond + Inter 字体）。
所有渲染函数返回完整 HTML 字符串，配合 streamlit.components.v1.html() 使用。
"""


def _truncate(text: str, max_len: int = 50) -> str:
    if not text:
        return ""
    return text[:max_len] + "…" if len(text) > max_len else text


def _fmt_date(pub_date: str) -> str:
    """从 RFC 822 日期字符串提取可读日期"""
    if not pub_date:
        return ""
    # e.g. "Mon, 01 Apr 2026 10:00:00 +0800"
    parts = pub_date.split()
    if len(parts) >= 4:
        return " ".join(parts[1:4])
    return pub_date[:16]


# ── Google Fonts head snippet ────────────────────────────────────────────────
_FONTS_HEAD = (
    '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond'
    ':wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap" '
    'rel="stylesheet">'
)

_BASE_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:0}
"""


# ── render_policy_hero ───────────────────────────────────────────────────────

def render_policy_hero(
    symbol: str,
    name: str,
    alignment: dict,
    policy_tags: list,
    policy_news: list,
    fundamentals: dict,
    normalized: dict,
) -> str:
    """
    返回完整 <!DOCTYPE html> HTML 字符串，含四个 section：
      1. 政策对齐横幅
      2. 概念标签云
      3. A股估值参考（PEG + PE）
      4. 政策新闻（最多3条）

    参数:
        symbol      — 股票代码，如 "sh600519"
        name        — 股票名称
        alignment   — get_fifteen_five_alignment() 返回值
        policy_tags — get_stock_policy_tags() 返回值
        policy_news — get_policy_news() 返回值
        fundamentals— dict，含 pe, peg, growth_rate 等
        normalized  — dict（预留，暂未使用）
    """
    level = alignment.get("level", "暂无明显政策主题")
    score = alignment.get("score", 0)
    color = alignment.get("color", "#5A5A6A")
    tier1 = alignment.get("tier1", [])
    tier2 = alignment.get("tier2", [])

    # ── Section 1: 政策对齐横幅 ──────────────────────────────────────────
    themes_text = "、".join((tier1 + tier2)[:4]) if (tier1 or tier2) else "暂无匹配主题"

    level_desc_map = {
        "核心主线": "深度受益于十五五规划核心方向，政策催化强劲",
        "受益方向": "与十五五规划存在一定政策关联，具备阶段性受益潜力",
        "暂无明显政策主题": "当前未检测到与十五五规划的显著政策关联",
    }
    level_desc = level_desc_map.get(level, "")

    banner_html = """
<div class="policy-banner" style="border-left-color:{color}">
    <div class="pb-badge" style="color:{color};border-color:{color}">{level}</div>
    <div class="pb-body">
        <div class="pb-left">
            <div class="pb-level" style="color:{color}">{level}</div>
            <div class="pb-themes">{themes_text}</div>
            <div class="pb-desc">{level_desc}</div>
        </div>
        <div class="pb-right">
            <div class="pb-score-label">政策得分</div>
            <div class="pb-score" style="color:{color}">{score}<span class="pb-score-max">/15</span></div>
        </div>
    </div>
</div>""".format(
        color=color,
        level=level,
        themes_text=themes_text,
        level_desc=level_desc,
        score=score,
    )

    # ── Section 2: 概念标签云 ────────────────────────────────────────────
    if policy_tags:
        tags_html_parts = []
        for tag in policy_tags:
            is_t1 = any(kw in tag for kw in [
                "人工智能", "机器人", "新能源汽车", "光伏", "储能",
                "半导体", "创新药", "芯片", "大模型", "量子",
            ])
            tag_color = "#C9A962" if is_t1 else "#5B8DB8"
            tag_bg = "rgba(201,169,98,0.08)" if is_t1 else "rgba(91,141,184,0.08)"
            tag_border = "rgba(201,169,98,0.3)" if is_t1 else "rgba(91,141,184,0.3)"
            tags_html_parts.append(
                '<span class="tag" style="color:{c};background:{bg};border-color:{bc}">{t}</span>'.format(
                    c=tag_color, bg=tag_bg, bc=tag_border, t=tag
                )
            )
        tags_inner = "\n".join(tags_html_parts)
    else:
        tags_inner = '<span class="tag-empty">暂无政策概念匹配</span>'

    tags_section = """
<div class="section">
    <div class="section-title">概念标签</div>
    <div class="tags-cloud">
        {tags_inner}
    </div>
    <div class="tags-legend">
        <span class="legend-dot" style="background:#C9A962"></span><span class="legend-text">一级主线</span>
        <span class="legend-dot" style="background:#5B8DB8;margin-left:12px"></span><span class="legend-text">二级受益</span>
    </div>
</div>""".format(tags_inner=tags_inner)

    # ── Section 3: A股估值参考 ───────────────────────────────────────────
    pe = fundamentals.get("pe", None)
    peg = fundamentals.get("peg", None)
    growth = fundamentals.get("growth_rate", None)

    pe_str = "{:.1f}x".format(pe) if pe else "--"
    peg_str = "{:.2f}".format(peg) if peg else "--"

    if peg:
        if peg < 0.8:
            peg_verdict = "低估"
            peg_color = "#00C853"
        elif peg < 1.5:
            peg_verdict = "合理"
            peg_color = "#C9A962"
        else:
            peg_verdict = "偏高"
            peg_color = "#FF5722"
    else:
        peg_verdict = "N/A"
        peg_color = "#5A5A6A"

    growth_str = "{:.1f}%".format(growth * 100) if growth else "--"

    valuation_section = """
<div class="section">
    <div class="section-title">A股估值参考</div>
    <div class="val-grid">
        <div class="val-item">
            <div class="val-label">PEG</div>
            <div class="val-value" style="color:{peg_color}">{peg_str}</div>
            <div class="val-sub">{peg_verdict}</div>
        </div>
        <div class="val-item">
            <div class="val-label">PE（TTM）</div>
            <div class="val-value">{pe_str}</div>
        </div>
        <div class="val-item">
            <div class="val-label">预期增长率</div>
            <div class="val-value">{growth_str}</div>
        </div>
        <div class="val-item">
            <div class="val-label">政策溢价</div>
            <div class="val-value" style="color:{policy_color}">+{premium}%</div>
            <div class="val-sub">基于政策得分估算</div>
        </div>
    </div>
    <div class="val-note">A股以政策驱动为主，DCF不适用 — 建议结合 PEG &amp; 政策催化综合判断</div>
</div>""".format(
        peg_color=peg_color,
        peg_str=peg_str,
        peg_verdict=peg_verdict,
        pe_str=pe_str,
        growth_str=growth_str,
        policy_color=color,
        premium=round(score * 2),
    )

    # ── Section 4: 政策新闻 ──────────────────────────────────────────────
    news_items_html = ""
    for item in policy_news[:3]:
        title = _truncate(item.get("title", ""), 50)
        date = _fmt_date(item.get("pubDate", ""))
        link = item.get("link", "#")
        source = item.get("source", "人民网")
        news_items_html += """
<a class="news-item" href="{link}" target="_blank" rel="noopener">
    <div class="news-meta"><span class="news-date">{date}</span><span class="news-source">{source}</span></div>
    <div class="news-title">{title}</div>
</a>""".format(link=link, date=date, source=source, title=title)

    if not news_items_html:
        news_items_html = '<div class="news-empty">暂无政策新闻</div>'

    news_section = """
<div class="section">
    <div class="section-title">政策动态</div>
    <div class="news-list">
        {news_items}
    </div>
</div>""".format(news_items=news_items_html)

    # ── 组合完整 HTML ────────────────────────────────────────────────────
    css = _BASE_CSS + """
.container{max-width:900px;margin:0 auto;padding:20px;display:flex;flex-direction:column;gap:16px}

/* Header */
.header{display:flex;align-items:baseline;gap:12px;margin-bottom:4px}
.header-name{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.6rem;font-weight:600;color:#E8E8F0}
.header-symbol{font-size:0.7rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase}

/* Policy Banner */
.policy-banner{
    background:linear-gradient(135deg,#0D0D14 0%,#12121C 100%);
    border:1px solid #1E1E2A;border-left:3px solid #C9A962;
    border-radius:4px;padding:24px 28px;
}
.pb-badge{
    display:inline-block;font-size:0.5rem;letter-spacing:3px;text-transform:uppercase;
    border:1px solid;border-radius:2px;padding:3px 10px;margin-bottom:14px;
}
.pb-body{display:flex;justify-content:space-between;align-items:center;gap:16px}
.pb-left{flex:1}
.pb-level{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.8rem;font-weight:700;letter-spacing:1px;line-height:1.1}
.pb-themes{font-size:0.75rem;color:#8A8A9A;margin-top:6px;letter-spacing:0.5px}
.pb-desc{font-size:0.65rem;color:#5A5A6A;margin-top:8px;line-height:1.5}
.pb-right{text-align:right;flex-shrink:0}
.pb-score-label{font-size:0.5rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:4px}
.pb-score{font-family:'Cormorant Garamond',Georgia,serif;font-size:2.8rem;font-weight:700;line-height:1}
.pb-score-max{font-size:1rem;font-weight:300;color:#5A5A6A}

/* Sections */
.section{background:#0D0D14;border:1px solid #1E1E2A;border-radius:4px;padding:20px 24px}
.section-title{font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-bottom:14px}

/* Tags */
.tags-cloud{display:flex;flex-wrap:wrap;gap:8px}
.tag{font-size:0.7rem;padding:5px 12px;border:1px solid;border-radius:2px;letter-spacing:0.5px}
.tag-empty{font-size:0.75rem;color:#5A5A6A;font-style:italic}
.tags-legend{display:flex;align-items:center;margin-top:12px}
.legend-dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px}
.legend-text{font-size:0.55rem;color:#5A5A6A;letter-spacing:1px}

/* Valuation */
.val-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:14px}
@media(max-width:600px){.val-grid{grid-template-columns:repeat(2,1fr)}}
.val-item{}
.val-label{font-size:0.5rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:4px}
.val-value{font-size:1.2rem;font-weight:600;color:#E8E8F0}
.val-sub{font-size:0.55rem;color:#3A3A4A;margin-top:2px}
.val-note{font-size:0.6rem;color:#3A3A4A;border-top:1px solid #1E1E2A;padding-top:10px;line-height:1.6}

/* News */
.news-list{display:flex;flex-direction:column;gap:10px}
.news-item{display:block;text-decoration:none;padding:10px 14px;background:#0A0A10;border:1px solid #1A1A26;border-radius:3px;transition:border-color 0.2s}
.news-item:hover{border-color:#2A2A40}
.news-meta{display:flex;align-items:center;gap:10px;margin-bottom:4px}
.news-date{font-size:0.55rem;color:#5A5A6A;letter-spacing:1px}
.news-source{font-size:0.5rem;color:#3A3A4A;letter-spacing:1px;text-transform:uppercase}
.news-title{font-size:0.8rem;color:#C8C8D8;line-height:1.5}
.news-empty{font-size:0.75rem;color:#5A5A6A;font-style:italic}
"""

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{fonts}
<style>{css}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <span class="header-name">{name}</span>
        <span class="header-symbol">{symbol}</span>
    </div>
    {banner}
    {tags}
    {valuation}
    {news}
</div>
</body>
</html>""".format(
        fonts=_FONTS_HEAD,
        css=css,
        name=name,
        symbol=symbol.upper(),
        banner=banner_html,
        tags=tags_section,
        valuation=valuation_section,
        news=news_section,
    )

    return html


# ── render_ashare_score_banner ───────────────────────────────────────────────

def render_ashare_score_banner(
    alignment: dict,
    moat_score: float,
    tech_score: float,
) -> str:
    """
    三维度评分横幅。

    参数:
        alignment  — get_fifteen_five_alignment() 返回值
        moat_score — 基本面/护城河原始分（0-100）
        tech_score — 市场热度/技术面原始分（0-100）

    返回:
        完整 <!DOCTYPE html> HTML 字符串
    """
    policy_raw = alignment.get("score", 0)
    color = alignment.get("color", "#C9A962")

    policy_score = round(min(policy_raw * 2.67, 40))
    fundamental_score = round(min(moat_score * 0.35, 35))
    market_score = round(min(tech_score * 0.25, 25))
    total_score = policy_score + fundamental_score + market_score

    def _bar_width(val, max_val):
        return round(val / max_val * 100) if max_val > 0 else 0

    if total_score >= 75:
        total_color = "#00C853"
    elif total_score >= 55:
        total_color = "#C9A962"
    else:
        total_color = "#FF5722"

    dims = [
        {
            "label": "政策受益度",
            "score": policy_score,
            "max": 40,
            "color": color,
            "bar_w": _bar_width(policy_score, 40),
        },
        {
            "label": "基本面",
            "score": fundamental_score,
            "max": 35,
            "color": "#5B8DB8",
            "bar_w": _bar_width(fundamental_score, 35),
        },
        {
            "label": "市场热度",
            "score": market_score,
            "max": 25,
            "color": "#8A6DB8",
            "bar_w": _bar_width(market_score, 25),
        },
    ]

    dims_html = ""
    for d in dims:
        dims_html += """
<div class="dim">
    <div class="dim-header">
        <span class="dim-label">{label}</span>
        <span class="dim-score" style="color:{color}">{score}<span class="dim-max">/{max}</span></span>
    </div>
    <div class="dim-bar-track">
        <div class="dim-bar-fill" style="width:{bar_w}%;background:{color}"></div>
    </div>
</div>""".format(**d)

    css = _BASE_CSS + """
.banner{
    background:linear-gradient(135deg,#0D0D14 0%,#12121C 100%);
    border:1px solid #1E1E2A;border-radius:4px;padding:20px 24px;
    max-width:900px;margin:0 auto;
}
.banner-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.banner-title{font-size:0.5rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase}
.total-block{text-align:right}
.total-label{font-size:0.5rem;letter-spacing:3px;color:#5A5A6A;text-transform:uppercase;margin-bottom:2px}
.total-score{font-family:'Cormorant Garamond',Georgia,serif;font-size:2rem;font-weight:700}
.total-max{font-size:0.9rem;font-weight:300;color:#5A5A6A}
.dims{display:flex;gap:20px}
@media(max-width:600px){.dims{flex-direction:column}}
.dim{flex:1}
.dim-header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px}
.dim-label{font-size:0.6rem;letter-spacing:2px;color:#8A8A9A;text-transform:uppercase}
.dim-score{font-size:1rem;font-weight:600}
.dim-max{font-size:0.65rem;color:#5A5A6A;font-weight:400}
.dim-bar-track{height:3px;background:#1E1E2A;border-radius:2px;overflow:hidden}
.dim-bar-fill{height:100%;border-radius:2px;transition:width 0.3s}
"""

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{fonts}
<style>{css}</style>
</head>
<body>
<div class="banner">
    <div class="banner-header">
        <div class="banner-title">综合评分</div>
        <div class="total-block">
            <div class="total-label">综合</div>
            <div class="total-score" style="color:{total_color}">{total}<span class="total-max">/100</span></div>
        </div>
    </div>
    <div class="dims">
        {dims}
    </div>
</div>
</body>
</html>""".format(
        fonts=_FONTS_HEAD,
        css=css,
        total_color=total_color,
        total=total_score,
        dims=dims_html,
    )

    return html
