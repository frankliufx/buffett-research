"""Shared, page-level UI components.

Canonical home for new shared UI. This package complements (not replaces)
`src/ui_theme.py` (global CSS + legacy primitives) and `src/ui_valuation.py`
(verdict / DCF / scenario cards).

Boundary:
- `ui_theme.py`        — CSS variables, COLORS, base widget primitives
- `ui_valuation.py`    — domain-specific verdict + DCF + insight cards
- `ui_committee.py`    — committee ensemble visualization
- `ui_components/`     — page-level layout components reused across 3+ pages
                         (page header, quotes, status, dividers)

Public API:
    from src.ui_components import render_page_header, render_quote, ...
"""

from src.ui_components.header import render_page_header
from src.ui_components.quotes import render_quote
from src.ui_components.layout import render_section_divider
from src.ui_components.loading import with_status
# v2 canonical components (P1 redesign)
from src.ui_components.verdict_banner import render_verdict_banner
from src.ui_components.stock_chip import render_stock_chip
from src.ui_components.score_card import render_score_card

__all__ = [
    # legacy
    "render_page_header",
    "render_quote",
    "render_section_divider",
    "with_status",
    # v2
    "render_verdict_banner",
    "render_stock_chip",
    "render_score_card",
]
