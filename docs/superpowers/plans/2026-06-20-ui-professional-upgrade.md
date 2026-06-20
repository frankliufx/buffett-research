# Plan: Phase 3 UI Professional Upgrade

**Date**: 2026-06-20
**Project**: stock-analyst (`~/stock-analyst/`)
**Branch**: `feat/ui-phase3-professional-upgrade`
**Estimated tasks**: 4
**Status**: READY

---

## Overview

Phase 3 targets four precision upgrades to the existing dark-gold Streamlit UI:

1. KPI cards gain delta/trend arrows showing YoY change
2. Committee member cards expose `key_evidence` and `main_concern` from Phase 2 data
3. AI report output moves from plain `st.markdown` to a styled gold-accent container
4. Financial metrics KPI cards receive dynamic color classes based on financial thresholds

All changes are additive — no existing interfaces are removed or made non-backward-compatible.

---

## Files Modified

| File | Purpose |
|---|---|
| `src/ui_theme.py` | Add `.kpi-delta` CSS + `ai-report-container` CSS; update `render_kpi_card()` signature |
| `src/ui_analysis.py` | Compute ROE delta; pass delta to KPI cards; wrap AI report; add threshold color logic |
| `src/ui_committee.py` | Extend member card HTML with `key_evidence` / `main_concern` + CSS classes |
| `tests/test_ui_theme.py` | New — unit tests for `render_kpi_card()` delta and CSS presence |
| `tests/test_ui_committee.py` | New — unit tests for extended member card HTML |
| `tests/test_ui_analysis_colors.py` | New — unit tests for threshold color-class logic |

---

## Task 1: KPI Card Delta Enhancement

**Files**: `src/ui_theme.py`, `src/ui_analysis.py`, `tests/test_ui_theme.py`

### Step 1.1 — Add `.kpi-delta` CSS to `get_global_css()`

In `src/ui_theme.py`, locate the existing KPI CSS block (lines 188–216). Insert the `.kpi-delta` rule immediately after `.kpi-card .kpi-value.warning`:

```python
# BEFORE (line 216):
    .kpi-card .kpi-value.warning { color: %(warning)s; }

# AFTER:
    .kpi-card .kpi-value.warning { color: %(warning)s; }
    .kpi-card .kpi-delta {
        font-size: 0.7rem;
        font-weight: 500;
        margin-top: 4px;
        letter-spacing: 0.3px;
        font-variant-numeric: tabular-nums;
    }
    .kpi-card .kpi-delta.delta-up   { color: %(success)s; }
    .kpi-card .kpi-delta.delta-down { color: %(danger)s; }
    .kpi-card .kpi-delta.delta-flat { color: %(text_muted)s; }
```

### Step 1.2 — Update `render_kpi_card()` signature

In `src/ui_theme.py`, replace `render_kpi_card()` (lines 819–825):

```python
# BEFORE:
def render_kpi_card(label, value, color_class=""):
    return """
<div class="kpi-card">
    <div class="kpi-label">{}</div>
    <div class="kpi-value {}">{}</div>
</div>
""".format(label, color_class, value)

# AFTER:
def render_kpi_card(label: str, value: str, color_class: str = "", delta: str = "") -> str:
    """Render a KPI card with optional YoY delta row.

    Args:
        label:       Uppercase metric label, e.g. "ROE"
        value:       Formatted metric value, e.g. "28.5%"
        color_class: One of "positive", "negative", "warning", or ""
        delta:       Optional delta string, e.g. "↑ +2.1pp" or "↓ -1.5pp".
                     Arrow prefix determines CSS class: ↑ → delta-up, ↓ → delta-down.
    """
    delta_html = ""
    if delta:
        if delta.startswith("↑"):
            delta_class = "delta-up"
        elif delta.startswith("↓"):
            delta_class = "delta-down"
        else:
            delta_class = "delta-flat"
        delta_html = '<div class="kpi-delta {}">{}</div>'.format(delta_class, delta)
    return (
        '<div class="kpi-card">'
        '<div class="kpi-label">{label}</div>'
        '<div class="kpi-value {color_class}">{value}</div>'
        '{delta_html}'
        '</div>'
    ).format(label=label, color_class=color_class, value=value, delta_html=delta_html)
```

### Step 1.3 — Compute ROE delta in `ui_analysis.py`

In `src/ui_analysis.py`, locate the `tab_finance` block (around line 827). Before the `metrics` list is constructed, add ROE delta computation:

```python
# INSERT before metrics list (after line 827 `with tab_finance:`):
        roe_history = normalized.get("roe_history", [])
        roe_delta = ""
        if len(roe_history) >= 2:
            # roe_history[0] is most recent; values are percentages (e.g. 28.5 not 0.285)
            diff = roe_history[0] - roe_history[1]
            arrow = "↑" if diff >= 0 else "↓"
            roe_delta = "{} {:+.1f}pp".format(arrow, diff)
```

### Step 1.4 — Apply delta to ROE card

Replace the ROE entry in the `metrics` list and the column render loop:

```python
# BEFORE (lines 828-838):
        metrics = [
            ("PE", "{:.1f}".format(normalized['pe_trailing']) if normalized.get('pe_trailing') else "--"),
            ("PB", "{:.2f}".format(normalized['pb']) if normalized.get('pb') else "--"),
            ("ROE", fmt_pct(normalized.get("roe"))),
            ("NET MARGIN", fmt_pct(normalized.get("profit_margin"))),
            ("GROSS MARGIN", fmt_pct(normalized.get("gross_margin"))),
        ]
        cols = st.columns(5)
        for i, (k, v) in enumerate(metrics):
            with cols[i]:
                st.markdown(render_kpi_card(k, v), unsafe_allow_html=True)

# AFTER:
        metrics = [
            ("PE",          "{:.1f}".format(normalized['pe_trailing']) if normalized.get('pe_trailing') else "--", "", ""),
            ("PB",          "{:.2f}".format(normalized['pb'])         if normalized.get('pb')           else "--", "", ""),
            ("ROE",         fmt_pct(normalized.get("roe")),                                                        "",  roe_delta),
            ("NET MARGIN",  fmt_pct(normalized.get("profit_margin")),                                              "",  ""),
            ("GROSS MARGIN",fmt_pct(normalized.get("gross_margin")),                                               "",  ""),
        ]
        cols = st.columns(5)
        for i, (k, v, cc, dt) in enumerate(metrics):
            with cols[i]:
                st.markdown(render_kpi_card(k, v, cc, dt), unsafe_allow_html=True)
```

Note: `color_class` for all row-1 cards is left as `""` here — Task 4 (Step 4.1) will add threshold-based color classes. Keep the tuple structure established in this step; Task 4 only fills the `cc` slot.

### Step 1.5 — Write tests (`tests/test_ui_theme.py`)

Create `tests/test_ui_theme.py`:

```python
"""Unit tests for render_kpi_card() and get_global_css()."""
import pytest
from src.ui_theme import render_kpi_card, get_global_css


class TestRenderKpiCard:
    def test_basic_card_contains_label_and_value(self):
        # Arrange
        label = "PE"
        value = "18.5"

        # Act
        html = render_kpi_card(label, value)

        # Assert
        assert "PE" in html
        assert "18.5" in html
        assert "kpi-card" in html

    def test_color_class_applied_to_value_div(self):
        # Arrange / Act
        html = render_kpi_card("ROE", "28.5%", "positive")

        # Assert
        assert 'class="kpi-value positive"' in html

    def test_no_delta_html_when_delta_empty(self):
        # Arrange / Act
        html = render_kpi_card("ROE", "28.5%", "positive", "")

        # Assert
        assert "kpi-delta" not in html

    def test_up_arrow_delta_renders_delta_up_class(self):
        # Arrange / Act
        html = render_kpi_card("ROE", "28.5%", "positive", "↑ +2.1pp")

        # Assert
        assert "kpi-delta" in html
        assert "delta-up" in html
        assert "↑" in html
        assert "+2.1pp" in html

    def test_down_arrow_delta_renders_delta_down_class(self):
        # Arrange / Act
        html = render_kpi_card("ROE", "20.0%", "warning", "↓ -1.5pp")

        # Assert
        assert "kpi-delta" in html
        assert "delta-down" in html
        assert "↓" in html
        assert "-1.5pp" in html

    def test_delta_without_arrow_renders_delta_flat_class(self):
        # Arrange / Act
        html = render_kpi_card("PE", "18.5", "", "n/a")

        # Assert
        assert "kpi-delta" in html
        assert "delta-flat" in html

    def test_empty_color_class_produces_no_extra_class_attr(self):
        # Arrange / Act
        html = render_kpi_card("PB", "1.5")

        # Assert
        assert 'class="kpi-value "' in html


class TestGetGlobalCss:
    def test_kpi_delta_css_class_present(self):
        # Arrange / Act
        css = get_global_css()

        # Assert
        assert ".kpi-delta" in css
        assert "delta-up" in css
        assert "delta-down" in css
        assert "delta-flat" in css
```

**Run tests:**
```bash
cd ~/stock-analyst && pytest tests/test_ui_theme.py -v
```

---

## Task 2: Committee Member Card Enhancement

**Files**: `src/ui_committee.py`, `tests/test_ui_committee.py`

### Step 2.1 — Add CSS classes to the committee HTML style block

In `src/ui_committee.py`, locate the `<style>` block embedded in the HTML string returned by `render_committee_page()`. Find the existing `.m-reason` rule and add after it:

```css
/* INSERT after .m-reason rule */
.m-evidence {
    font-size: 0.75rem;
    color: #A8A8B0;
    margin-top: 6px;
    padding: 5px 8px;
    border-left: 2px solid #2A2A33;
    line-height: 1.5;
}
.m-concern {
    font-size: 0.75rem;
    color: #F5A623;
    margin-top: 5px;
    padding: 4px 8px;
    display: flex;
    align-items: flex-start;
    gap: 4px;
    line-height: 1.5;
}
.m-concern-icon {
    flex-shrink: 0;
    margin-top: 1px;
}
```

### Step 2.2 — Extend member card HTML generation

In `src/ui_committee.py`, replace the `members_html +=` block (lines 196–209) with the version that conditionally appends `key_evidence` and `main_concern`:

```python
# BEFORE:
            members_html += (
                '<div class="m-card" style="border-left-color:{mc}">'
                '<div class="m-row1">'
                '<div class="m-who"><span class="m-icon">{icon}</span>'
                '<div><div class="m-name">{name}</div><div class="m-style">{style}</div></div></div>'
                '<div class="m-sig" style="color:{mc};border-color:{mc}">{label}</div></div>'
                '<div class="m-reason">{reason}</div>'
                '<div class="m-bar-row"><div class="m-bar-track">'
                '<div class="m-bar-fill" style="width:{conf}%;background:{mc}"></div></div>'
                '<span class="m-conf">{conf}%</span></div></div>'
            ).format(
                mc=mc, icon=m["icon"], name=m["name_cn"], style=m["style"],
                label=ml, reason=m["reasoning"], conf=m["confidence"],
            )

# AFTER:
            evidence_html = ""
            if m.get("key_evidence"):
                evidence_html = '<div class="m-evidence">{}</div>'.format(m["key_evidence"])

            concern_html = ""
            if m.get("main_concern"):
                concern_html = (
                    '<div class="m-concern">'
                    '<span class="m-concern-icon">&#9888;</span>'
                    '<span>{}</span>'
                    '</div>'
                ).format(m["main_concern"])

            members_html += (
                '<div class="m-card" style="border-left-color:{mc}">'
                '<div class="m-row1">'
                '<div class="m-who"><span class="m-icon">{icon}</span>'
                '<div><div class="m-name">{name}</div><div class="m-style">{style}</div></div></div>'
                '<div class="m-sig" style="color:{mc};border-color:{mc}">{label}</div></div>'
                '<div class="m-reason">{reason}</div>'
                '{evidence_html}'
                '{concern_html}'
                '<div class="m-bar-row"><div class="m-bar-track">'
                '<div class="m-bar-fill" style="width:{conf}%;background:{mc}"></div></div>'
                '<span class="m-conf">{conf}%</span></div></div>'
            ).format(
                mc=mc, icon=m["icon"], name=m["name_cn"], style=m["style"],
                label=ml, reason=m["reasoning"], conf=m["confidence"],
                evidence_html=evidence_html, concern_html=concern_html,
            )
```

### Step 2.3 — Write tests (`tests/test_ui_committee.py`)

Create `tests/test_ui_committee.py`:

```python
"""Unit tests for committee member card HTML rendering."""
import pytest
from src.ui_committee import render_committee_page


MINIMAL_MEMBER = {
    "icon": "📊",
    "name_cn": "价值投资者",
    "style": "Value",
    "signal": "bullish",
    "confidence": 75,
    "reasoning": "Strong FCF and low P/B.",
    "key_evidence": None,
    "main_concern": None,
}


def _build_committee(member_overrides: dict) -> dict:
    member = {**MINIMAL_MEMBER, **member_overrides}
    return {
        "members": [member],
        "consensus": {"signal": "bullish", "verdict": "BUY", "unanimity": "High"},
        "weighted_score": 60,
        "bullish_count": 1,
        "bearish_count": 0,
        "neutral_count": 0,
    }


class TestMemberCardEvidenceAndConcern:
    def test_no_evidence_section_when_key_evidence_absent(self):
        # Arrange
        committee = _build_committee({"key_evidence": None})

        # Act
        html = render_committee_page(committee=committee)

        # Assert
        assert "m-evidence" not in html

    def test_evidence_section_rendered_when_key_evidence_present(self):
        # Arrange
        committee = _build_committee({"key_evidence": "FCF yield 8.2% over 5Y avg."})

        # Act
        html = render_committee_page(committee=committee)

        # Assert
        assert "m-evidence" in html
        assert "FCF yield 8.2% over 5Y avg." in html

    def test_no_concern_section_when_main_concern_absent(self):
        # Arrange
        committee = _build_committee({"main_concern": None})

        # Act
        html = render_committee_page(committee=committee)

        # Assert
        assert "m-concern" not in html

    def test_concern_section_rendered_when_main_concern_present(self):
        # Arrange
        committee = _build_committee({"main_concern": "Leverage ratio elevated at 3.2x."})

        # Act
        html = render_committee_page(committee=committee)

        # Assert
        assert "m-concern" in html
        assert "Leverage ratio elevated at 3.2x." in html

    def test_concern_includes_warning_icon(self):
        # Arrange
        committee = _build_committee({"main_concern": "Revenue declining."})

        # Act
        html = render_committee_page(committee=committee)

        # Assert
        # &#9888; is the HTML entity for ⚠
        assert "&#9888;" in html

    def test_both_evidence_and_concern_render_together(self):
        # Arrange
        committee = _build_committee({
            "key_evidence": "ROE 25% for 10 consecutive years.",
            "main_concern": "High capex requirement limits FCF.",
        })

        # Act
        html = render_committee_page(committee=committee)

        # Assert
        assert "m-evidence" in html
        assert "m-concern" in html
        assert "ROE 25% for 10 consecutive years." in html
        assert "High capex requirement limits FCF." in html

    def test_existing_reasoning_still_present(self):
        # Arrange
        committee = _build_committee({"reasoning": "Durable moat confirmed."})

        # Act
        html = render_committee_page(committee=committee)

        # Assert
        assert "Durable moat confirmed." in html
        assert "m-reason" in html
```

**Run tests:**
```bash
cd ~/stock-analyst && pytest tests/test_ui_committee.py -v
```

---

## Task 3: AI Report Styled Container

**Files**: `src/ui_theme.py`, `src/ui_analysis.py`

### Step 3.1 — Add AI report CSS to `get_global_css()`

In `src/ui_theme.py`, inside `get_global_css()`, append the following CSS block before the closing `</style>` tag. Insert it after the last existing rule block:

```css
    /* ===== AI Report Container ===== */
    .ai-report-container {
        background: %(bg_card)s;
        border-left: 3px solid %(primary)s;
        border-radius: 0 8px 8px 0;
        padding: 1.5rem 2rem;
        margin-top: 1rem;
    }
    .ai-report-container h1,
    .ai-report-container h2,
    .ai-report-container h3 {
        color: %(primary)s;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        border-bottom: 1px solid %(border)s;
        padding-bottom: 0.4rem;
        margin-top: 1.4rem;
        margin-bottom: 0.6rem;
    }
    .ai-report-container h1 { font-size: 1.1rem; }
    .ai-report-container h2 { font-size: 1rem; }
    .ai-report-container h3 { font-size: 0.9rem; }
    .ai-report-container p {
        color: %(text_secondary)s;
        line-height: 1.8;
        margin-bottom: 0.6rem;
    }
    .ai-report-container strong {
        color: %(text)s;
        font-weight: 600;
    }
    .ai-report-container code {
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.85rem;
        color: %(primary_light)s;
        background: %(bg)s;
        padding: 1px 4px;
        border-radius: 3px;
    }
    .ai-report-container table {
        width: 100%%;
        border-collapse: collapse;
        margin: 0.8rem 0;
        font-size: 0.85rem;
    }
    .ai-report-container table th {
        background: %(primary_dark)s;
        color: %(bg)s;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.5px;
        padding: 6px 10px;
        border: 1px solid %(border)s;
    }
    .ai-report-container table td {
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.82rem;
        color: %(text)s;
        padding: 5px 10px;
        border: 1px solid %(border)s;
    }
    .ai-report-container table tr:nth-child(even) td {
        background: %(bg_elevated)s;
    }
    .ai-report-container ul,
    .ai-report-container ol {
        color: %(text_secondary)s;
        line-height: 1.8;
        padding-left: 1.4rem;
    }
    .ai-report-container li {
        margin-bottom: 0.3rem;
    }
```

Note: `%%` is required for literal `%` in Python `%`-formatted strings (the CSS uses `width: 100%%` for tables).

### Step 3.2 — Wrap AI report output in `ui_analysis.py`

In `src/ui_analysis.py`, locate the AI report display block (lines 939–940):

```python
# BEFORE:
        if ai_key in st.session_state:
            st.markdown(st.session_state[ai_key])

# AFTER:
        if ai_key in st.session_state:
            import markdown as _md  # noqa: PLC0415 — deferred to avoid cold-start cost
            raw_text: str = st.session_state[ai_key]
            body_html: str = _md.markdown(
                raw_text,
                extensions=["tables", "fenced_code"],
            )
            styled_html = (
                '<div class="ai-report-container">{}</div>'.format(body_html)
            )
            st.markdown(styled_html, unsafe_allow_html=True)
```

### Step 3.3 — Add `markdown` to dependencies

Verify `markdown` is already installed (it ships with Streamlit's transitive deps). If not present, add to `requirements.txt`:

```
markdown>=3.4
```

Check with:
```bash
cd ~/stock-analyst && python -c "import markdown; print(markdown.__version__)"
```

### Step 3.4 — Write CSS presence tests (append to `tests/test_ui_theme.py`)

Add these test methods to the `TestGetGlobalCss` class in `tests/test_ui_theme.py`:

```python
    def test_ai_report_container_css_present(self):
        # Arrange / Act
        css = get_global_css()

        # Assert
        assert ".ai-report-container" in css

    def test_ai_report_container_has_gold_border(self):
        # Arrange / Act
        css = get_global_css()

        # Assert
        # The CSS uses %(primary)s which resolves to #C9A962
        assert "ai-report-container" in css
        assert "border-left" in css

    def test_ai_report_h2_rule_present(self):
        # Arrange / Act
        css = get_global_css()

        # Assert
        assert ".ai-report-container h2" in css

    def test_ai_report_table_th_rule_present(self):
        # Arrange / Act
        css = get_global_css()

        # Assert
        assert ".ai-report-container table th" in css

    def test_ai_report_table_td_rule_present(self):
        # Arrange / Act
        css = get_global_css()

        # Assert
        assert ".ai-report-container table td" in css
```

**Run tests:**
```bash
cd ~/stock-analyst && pytest tests/test_ui_theme.py -v
```

---

## Task 4: ROE Table Conditional Coloring

**Files**: `src/ui_analysis.py`, `tests/test_ui_analysis_colors.py`

### Step 4.1 — Extract color-class helper function

In `src/ui_analysis.py`, add a module-level helper function near the top of the file (after existing imports, before `render_analysis_page` or equivalent). This keeps the logic testable in isolation:

```python
# CONSTANTS — financial metric thresholds
_ROE_GOLD_THRESHOLD    = 0.15   # 15%
_ROE_WARN_THRESHOLD    = 0.08   # 8%
_MARGIN_GOLD_THRESHOLD = 0.20   # 20%
_MARGIN_WARN_THRESHOLD = 0.10   # 10%


def _roe_color_class(roe: float | None) -> str:
    """Return KPI color class for ROE based on Buffett quality thresholds.

    Args:
        roe: ROE as a decimal fraction (e.g. 0.285 for 28.5%), or None.

    Returns:
        "positive" (>= 15%), "warning" (>= 8%), "negative" (< 8%), or "" if None.
    """
    if roe is None:
        return ""
    if roe >= _ROE_GOLD_THRESHOLD:
        return "positive"
    if roe >= _ROE_WARN_THRESHOLD:
        return "warning"
    return "negative"


def _margin_color_class(margin: float | None) -> str:
    """Return KPI color class for net/gross margin.

    Args:
        margin: Margin as a decimal fraction (e.g. 0.22 for 22%), or None.

    Returns:
        "positive" (>= 20%), "warning" (>= 10%), "negative" (< 10%), or "" if None.
    """
    if margin is None:
        return ""
    if margin >= _MARGIN_GOLD_THRESHOLD:
        return "positive"
    if margin >= _MARGIN_WARN_THRESHOLD:
        return "warning"
    return "negative"


def _growth_color_class(growth: float | None) -> str:
    """Return KPI color class for revenue/EPS growth.

    Args:
        growth: Growth rate as a decimal fraction (e.g. 0.12 for 12%), or None.

    Returns:
        "positive" (> 0), "negative" (< 0), or "" if None or zero.
    """
    if growth is None:
        return ""
    if growth > 0:
        return "positive"
    if growth < 0:
        return "negative"
    return ""
```

### Step 4.2 — Apply color classes to row-1 metrics

In `src/ui_analysis.py`, update the `metrics` list established in Task 1 (Step 1.4) to fill the `cc` (color_class) slot using the new helpers:

```python
# REPLACE the metrics list (built in Task 1 Step 1.4):
        roe_val    = normalized.get("roe")
        margin_val = normalized.get("profit_margin")
        gross_val  = normalized.get("gross_margin")

        metrics = [
            ("PE",           "{:.1f}".format(normalized['pe_trailing']) if normalized.get('pe_trailing') else "--", "",                              ""),
            ("PB",           "{:.2f}".format(normalized['pb'])         if normalized.get('pb')           else "--", "",                              ""),
            ("ROE",          fmt_pct(roe_val),                                                                       _roe_color_class(roe_val),       roe_delta),
            ("NET MARGIN",   fmt_pct(margin_val),                                                                    _margin_color_class(margin_val), ""),
            ("GROSS MARGIN", fmt_pct(gross_val),                                                                     _margin_color_class(gross_val),  ""),
        ]
```

### Step 4.3 — Apply color classes to row-2 metrics

In `src/ui_analysis.py`, update the `metrics2` list and its render loop similarly:

```python
# REPLACE (around line 842-852):
        rev_growth_val = normalized.get("revenue_growth")
        eps_growth_val = normalized.get("earnings_growth")

        metrics2 = [
            ("D/E RATIO",     "{:.2f}".format(normalized['debt_to_equity']) if normalized.get('debt_to_equity') is not None else "--", "", ""),
            ("CURRENT RATIO", "{:.2f}".format(normalized['current_ratio'])  if normalized.get('current_ratio')              else "--", "", ""),
            ("REV GROWTH",    fmt_pct(rev_growth_val),  _growth_color_class(rev_growth_val), ""),
            ("EPS GROWTH",    fmt_pct(eps_growth_val),  _growth_color_class(eps_growth_val), ""),
            ("FCF",           format_number(normalized.get("free_cashflow")),                "",                             ""),
        ]
        cols2 = st.columns(5)
        for i, (k, v, cc, dt) in enumerate(metrics2):
            with cols2[i]:
                st.markdown(render_kpi_card(k, v, cc, dt), unsafe_allow_html=True)
```

### Step 4.4 — Write threshold color tests (`tests/test_ui_analysis_colors.py`)

Create `tests/test_ui_analysis_colors.py`:

```python
"""Unit tests for KPI card threshold color-class logic."""
import pytest
from src.ui_analysis import _roe_color_class, _margin_color_class, _growth_color_class


class TestRoeColorClass:
    def test_none_returns_empty_string(self):
        assert _roe_color_class(None) == ""

    def test_above_15pct_returns_positive(self):
        assert _roe_color_class(0.15) == "positive"
        assert _roe_color_class(0.285) == "positive"
        assert _roe_color_class(0.50) == "positive"

    def test_between_8_and_15_pct_returns_warning(self):
        assert _roe_color_class(0.08) == "warning"
        assert _roe_color_class(0.12) == "warning"
        assert _roe_color_class(0.1499) == "warning"

    def test_below_8pct_returns_negative(self):
        assert _roe_color_class(0.0) == "negative"
        assert _roe_color_class(0.05) == "negative"
        assert _roe_color_class(0.0799) == "negative"

    def test_negative_roe_returns_negative(self):
        assert _roe_color_class(-0.05) == "negative"


class TestMarginColorClass:
    def test_none_returns_empty_string(self):
        assert _margin_color_class(None) == ""

    def test_above_20pct_returns_positive(self):
        assert _margin_color_class(0.20) == "positive"
        assert _margin_color_class(0.35) == "positive"

    def test_between_10_and_20_pct_returns_warning(self):
        assert _margin_color_class(0.10) == "warning"
        assert _margin_color_class(0.15) == "warning"
        assert _margin_color_class(0.1999) == "warning"

    def test_below_10pct_returns_negative(self):
        assert _margin_color_class(0.05) == "negative"
        assert _margin_color_class(0.0) == "negative"
        assert _margin_color_class(0.0999) == "negative"

    def test_gross_margin_same_thresholds(self):
        # gross margin uses same function
        assert _margin_color_class(0.50) == "positive"
        assert _margin_color_class(0.18) == "warning"
        assert _margin_color_class(0.07) == "negative"


class TestGrowthColorClass:
    def test_none_returns_empty_string(self):
        assert _growth_color_class(None) == ""

    def test_positive_growth_returns_positive(self):
        assert _growth_color_class(0.12) == "positive"
        assert _growth_color_class(0.001) == "positive"

    def test_negative_growth_returns_negative(self):
        assert _growth_color_class(-0.05) == "negative"
        assert _growth_color_class(-0.001) == "negative"

    def test_zero_growth_returns_empty(self):
        assert _growth_color_class(0.0) == ""
```

**Run tests:**
```bash
cd ~/stock-analyst && pytest tests/test_ui_analysis_colors.py -v
```

---

## Full Test Suite Command

After all tasks are complete, verify no regressions:

```bash
cd ~/stock-analyst && pytest tests/test_ui_theme.py tests/test_ui_committee.py tests/test_ui_analysis_colors.py -v --tb=short
```

Expected: all tests pass, no import errors.

---

## Implementation Order

Tasks are independent but share one dependency: Task 1 Step 1.4 establishes the 4-tuple `metrics` structure that Task 4 Step 4.2 fills. Implement in this sequence:

1. Task 1 (KPI delta) — establishes new `render_kpi_card()` signature and 4-tuple metrics structure
2. Task 4 (threshold colors) — fills `cc` slot in tuples from Task 1
3. Task 2 (committee cards) — fully independent
4. Task 3 (AI report container) — fully independent

Tasks 2, 3, and 4 can be implemented in parallel after Task 1 is done.

---

## Self-Review Checklist

- [x] All 4 design spec improvements covered (KPI delta, committee cards, AI report, conditional coloring)
- [x] No placeholders ("TBD", "implement later") — every step has complete code
- [x] Type annotations on all new function signatures
- [x] `render_kpi_card()` signature consistent across Task 1 (definition) and Tasks 2, 3, 4 (callers)
- [x] Color class names consistent: `"positive"`, `"warning"`, `"negative"` match existing CSS (lines 214–216 of ui_theme.py)
- [x] `delta` arrow detection consistent: `startswith("↑")` / `startswith("↓")` in function, `"↑" / "↓"` in format string
- [x] `roe_history` index convention consistent: `[0]` = most recent throughout
- [x] `%%` used for literal `%` in table CSS (Python `%`-format string safe)
- [x] `key_evidence` / `main_concern` accessed via `.get()` — backward compatible with members lacking those fields
- [x] Test file names match task descriptions; no cross-task imports
- [x] Test commands are runnable from `~/stock-analyst/` root
