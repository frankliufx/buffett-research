"""测试 CrossValidator 多源校验逻辑"""
from __future__ import annotations
import pytest
from src.data.cross_validator import CrossValidator, ValidationResult


def test_single_source_returns_single_source_quality():
    cv = CrossValidator()
    result = cv.validate_field({"yfinance": 0.15})
    assert result.value == 0.15
    assert result.quality == "single_source"
    assert result.warning == ""


def test_two_sources_within_threshold_returns_confirmed():
    cv = CrossValidator()
    result = cv.validate_field({"yfinance": 0.15, "tushare": 0.153})
    assert result.quality == "confirmed"
    assert abs(result.value - 0.1515) < 0.001
    assert result.warning == ""


def test_two_sources_exceed_threshold_returns_uncertain():
    cv = CrossValidator()
    result = cv.validate_field({"yfinance": 0.15, "tushare": 0.22})
    assert result.quality == "uncertain"
    assert "⚠️" in result.warning


def test_none_values_filtered_out():
    cv = CrossValidator()
    result = cv.validate_field({"yfinance": 0.15, "tushare": None})
    assert result.value == 0.15
    assert result.quality == "single_source"


def test_all_none_returns_none():
    cv = CrossValidator()
    result = cv.validate_field({"yfinance": None, "tushare": None})
    assert result.value is None


def test_validate_fundamentals_merges_fields():
    cv = CrossValidator()
    source_a = {"roe": 0.15, "pe_trailing": 12.0, "gross_margin": 0.45, "_source": "a"}
    source_b = {"roe": 0.153, "pe_trailing": 12.5, "gross_margin": None, "_source": "b"}

    merged = cv.validate_fundamentals(source_a, source_b)
    assert merged["roe"] is not None
    assert merged["_data_quality"]["roe"] == "confirmed"
    assert merged["_data_quality"]["pe_trailing"] == "confirmed"
    assert merged["_data_quality"]["gross_margin"] == "single_source"


def test_threshold_customizable():
    cv = CrossValidator(threshold=0.10)
    result = cv.validate_field({"a": 1.00, "b": 1.08}, threshold=0.10)
    assert result.quality == "confirmed"
