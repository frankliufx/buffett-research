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
