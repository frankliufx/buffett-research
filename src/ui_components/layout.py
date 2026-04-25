"""Layout primitives — section dividers, spacers."""

from __future__ import annotations

import streamlit as st


def render_section_divider(*, height: int = 16, color: str = "#1A1A22") -> None:
    """Render the project's standard 1px gold-friendly divider.

    Replaces 47+ ad-hoc `<div style='border-top:...'>` calls scattered
    across pages. Default thickness/color match the existing visual.
    """
    st.markdown(
        f"<div style='height:{height}px;border-top:1px solid {color};margin-top:{height}px'></div>",
        unsafe_allow_html=True,
    )
