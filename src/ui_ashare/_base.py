"""Shared chrome — fonts, base CSS, small formatters."""

# Google Fonts head snippet shared by every legacy hero and new card.
FONTS_HEAD = (
    '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond'
    ':wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap" '
    'rel="stylesheet">'
)

BASE_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:0}
"""

# 单一卡片的暗色背景（与 ui_components 风格一致）
CARD_BG = "#0D0D14"
CARD_BORDER = "#1E1E2A"
GOLD = "#C9A962"

# Phase color palette (mirrors src/data/policy_lifecycle.py)
PHASE_COLOR = {
    "爆发期": "#3ECF8E",
    "蓄势期": "#C9A962",
    "退坡期": "#EF4444",
    "未知":   "#5A5A6A",
}


def truncate(text: str, max_len: int = 50) -> str:
    if not text:
        return ""
    return text[:max_len] + "…" if len(text) > max_len else text


def fmt_date(pub_date: str) -> str:
    """Extract a readable date from an RFC 822 string (RSS dates)."""
    if not pub_date:
        return ""
    parts = pub_date.split()
    if len(parts) >= 4:
        return " ".join(parts[1:4])
    return pub_date[:16]


def days_ago(d) -> str:
    """Human-readable '8天前' / '3个月前' / '已过去 X 天'."""
    from datetime import date as _date
    if d is None:
        return ""
    if not isinstance(d, _date):
        return ""
    delta = (_date.today() - d).days
    if delta < 0:
        return "{}天后".format(-delta)
    if delta == 0:
        return "今日"
    if delta < 30:
        return "{}天前".format(delta)
    if delta < 365:
        return "{}个月前".format(delta // 30)
    return "{}年前".format(delta // 365)
