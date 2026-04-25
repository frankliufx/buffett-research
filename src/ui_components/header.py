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
        # v2: accent word is serif italic (.accent class), not bold-gold caps.
        title_html += ' <span class="accent">' + _html.escape(accent) + "</span>"

    eyebrow_block = (
        f'<div class="eyebrow">{_html.escape(eyebrow)}</div>' if eyebrow else ""
    )
    icon_block = f'<div class="icon">{icon}</div>' if icon else ""
    subtitle_block = (
        f'<div class="sub">{_html.escape(subtitle)}</div>' if subtitle else ""
    )

    # v2 typography (P1 redesign):
    # - Title is sans (Inter 600), not full-Cormorant; only the accent word is serif.
    # - Letter-spacing softened from 3-4px to 0.6-1.5px (was 8x too tight to read).
    # - Bottom divider is tighter (60% width centered) — less "luxury catalog" feel.
    components.html(
        f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="{_FONTS}" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0A0A0F;font-family:'Inter',-apple-system,sans-serif;padding:20px 0 10px;text-align:center;color:#F2F2F5;letter-spacing:0.005em}}
.eyebrow{{font-size:0.66rem;letter-spacing:1.5px;color:#9A9AA8;text-transform:uppercase;margin-bottom:6px;font-weight:500}}
.icon{{font-size:1.8rem;margin-bottom:8px;opacity:0.85}}
.title{{font-family:'Inter',-apple-system,sans-serif;font-size:1.45rem;font-weight:600;color:#F2F2F5;letter-spacing:-0.015em;line-height:1.25}}
.title .accent{{font-family:'Cormorant Garamond',Georgia,serif;font-weight:600;color:#C9A962;font-style:italic;letter-spacing:0.005em;padding:0 0.05em}}
.sub{{font-size:0.74rem;letter-spacing:0.5px;color:#9A9AA8;margin-top:6px;font-weight:400}}
.divider{{height:1px;background:linear-gradient(90deg,transparent 20%,#C9A962 50%,transparent 80%);margin:14px auto 0;opacity:0.35;max-width:60%}}
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
