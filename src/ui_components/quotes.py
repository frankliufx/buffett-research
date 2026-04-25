"""Quote rendering — Buffett / Duan philosophy citations.

Replaces 4 hardcoded `st.markdown('> *"..."*')` calls in 2_analysis.py and
the inline rendering in 3_chat.py with a single styled component.
"""

from __future__ import annotations

import html as _html
from typing import Literal

import streamlit as st

_AUTHOR_COLOR = {
    "buffett": "#C9A962",      # gold
    "duan": "#9CA3AF",         # silver
    "default": "#5A5A6A",
}

_AUTHOR_LABEL = {
    "buffett": "Warren Buffett",
    "duan": "段永平",
}


def render_quote(
    text: str,
    author: Literal["buffett", "duan", "default"] = "default",
    *,
    label: str | None = None,
) -> None:
    """Render a single quote block with a left-border accent.

    Args:
        text: The quote, plain text (HTML-escaped).
        author: Visual style — "buffett" (gold) | "duan" (silver) | "default".
        label: Optional override for the attribution line. Falls back to a
            sensible default based on `author`.
    """
    color = _AUTHOR_COLOR.get(author, _AUTHOR_COLOR["default"])
    attribution = label or _AUTHOR_LABEL.get(author, "")
    safe_text = _html.escape(text)
    safe_label = _html.escape(attribution)

    st.markdown(
        f"""
<div style="
  border-left:2px solid {color};
  padding:8px 16px;
  margin:12px 0;
  font-style:italic;
  color:#C8C8D0;
  font-family:'Cormorant Garamond',Georgia,serif;
  font-size:1.05rem;
  line-height:1.6;
">
  "{safe_text}"
  <div style="
    font-style:normal;
    font-size:0.65rem;
    letter-spacing:2px;
    color:{color};
    text-transform:uppercase;
    margin-top:6px;
  ">— {safe_label}</div>
</div>
""",
        unsafe_allow_html=True,
    )
