"""Page-level hero header.

Replaces ~50 lines of duplicated `<DOCTYPE html>` boilerplate that lived at
the top of chat / portfolio / dashboard. Visual contract identical to v1
(Cormorant Garamond title with gold-accented bold word, optional
eyebrow / subtitle, gradient divider).
"""

from __future__ import annotations

import html as _html
from typing import Optional

import streamlit.components.v1 as components

_FONTS = (
    "https://fonts.googleapis.com/css2?"
    "family=Cormorant+Garamond:wght@300;400;600;700"
    "&family=Inter:wght@300;400;500;600&display=swap"
)


def render_page_header(
    title: str,
    *,
    accent: Optional[str] = None,
    subtitle: Optional[str] = None,
    eyebrow: Optional[str] = None,
    icon: Optional[str] = None,
    height: int = 100,
) -> None:
    """Render the standard luxury page header.

    Args:
        title: The main word(s). Plain text. If `accent` is also given, it is
            bolded and gold-accented after the title (e.g. title="AI",
            accent="Advisor" renders as "AI **Advisor**").
        accent: Optional bold word that follows `title`.
        subtitle: Small uppercase tagline below the divider area.
        eyebrow: Tiny uppercase line above the title (used by dashboard's
            "Welcome back, …").
        icon: Optional emoji or text rendered above the title.
        height: Iframe height in px. 90 is the default for title-only pages,
            ~130 leaves room for icon + subtitle.
    """
    title_html = _html.escape(title)
    if accent:
        title_html += " <b>" + _html.escape(accent) + "</b>"

    eyebrow_block = (
        f'<div class="eyebrow">{_html.escape(eyebrow)}</div>' if eyebrow else ""
    )
    icon_block = f'<div class="icon">{icon}</div>' if icon else ""
    subtitle_block = (
        f'<div class="sub">{_html.escape(subtitle)}</div>' if subtitle else ""
    )

    components.html(
        f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="{_FONTS}" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#08080C;font-family:'Inter',-apple-system,sans-serif;padding:24px 0 8px;text-align:center}}
.eyebrow{{font-size:0.55rem;letter-spacing:4px;color:#C9A962;text-transform:uppercase;margin-bottom:6px}}
.icon{{font-size:2.2rem;margin-bottom:12px;opacity:0.8}}
.title{{font-family:'Cormorant Garamond',Georgia,serif;font-size:1.7rem;font-weight:300;color:#E8E8F0;letter-spacing:3px;text-transform:uppercase}}
.title b{{font-weight:700;color:#C9A962}}
.sub{{font-size:0.55rem;letter-spacing:4px;color:#5A5A6A;text-transform:uppercase;margin-top:6px}}
.divider{{height:1px;background:linear-gradient(90deg,transparent,#C9A962 30%,transparent);margin-top:16px;opacity:0.3}}
</style></head><body>
{eyebrow_block}
{icon_block}
<div class="title">{title_html}</div>
{subtitle_block}
<div class="divider"></div>
</body></html>""",
        height=height,
        scrolling=False,
    )
