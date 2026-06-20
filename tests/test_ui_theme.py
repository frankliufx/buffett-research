"""Unit tests for render_kpi_card() and get_global_css()."""
import pytest
from src.ui_theme import render_kpi_card, get_global_css


class TestRenderKpiCard:
    def test_basic_card_contains_label_and_value(self):
        html = render_kpi_card("PE", "18.5")
        assert "PE" in html
        assert "18.5" in html
        assert "kpi-card" in html

    def test_color_class_applied_to_value_div(self):
        html = render_kpi_card("ROE", "28.5%", "positive")
        assert 'class="kpi-value positive"' in html

    def test_no_delta_html_when_delta_empty(self):
        html = render_kpi_card("ROE", "28.5%", "positive", "")
        assert "kpi-delta" not in html

    def test_up_arrow_delta_renders_delta_up_class(self):
        html = render_kpi_card("ROE", "28.5%", "positive", "↑ +2.1pp")
        assert "kpi-delta" in html
        assert "delta-up" in html
        assert "↑" in html
        assert "+2.1pp" in html

    def test_down_arrow_delta_renders_delta_down_class(self):
        html = render_kpi_card("ROE", "20.0%", "warning", "↓ -1.5pp")
        assert "kpi-delta" in html
        assert "delta-down" in html
        assert "↓" in html
        assert "-1.5pp" in html

    def test_delta_without_arrow_renders_delta_flat_class(self):
        html = render_kpi_card("PE", "18.5", "", "n/a")
        assert "kpi-delta" in html
        assert "delta-flat" in html

    def test_empty_color_class_produces_no_extra_class_attr(self):
        html = render_kpi_card("PB", "1.5")
        assert 'class="kpi-value "' in html


class TestGetGlobalCss:
    def test_kpi_delta_css_class_present(self):
        css = get_global_css()
        assert ".kpi-delta" in css
        assert "delta-up" in css
        assert "delta-down" in css
        assert "delta-flat" in css
