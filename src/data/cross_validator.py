"""多数据源交叉校验器 — 检测数据源间差异，标注数据质量"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


_NUMERIC_FIELDS = [
    "roe", "roa", "profit_margin", "gross_margin", "operating_margin",
    "pe_trailing", "pe_forward", "pb", "ps",
    "debt_to_equity", "current_ratio", "quick_ratio",
    "revenue_growth", "earnings_growth",
    "dividend_yield", "market_cap", "total_revenue",
]

_DEFAULT_THRESHOLD = 0.05


@dataclass
class ValidationResult:
    value: Optional[float]
    quality: str  # "confirmed" | "uncertain" | "single_source"
    warning: str = ""
    sources: dict = field(default_factory=dict)


class CrossValidator:
    def __init__(self, threshold: float = _DEFAULT_THRESHOLD):
        self.default_threshold = threshold

    def validate_field(
        self,
        values: dict,
        threshold: float | None = None,
    ) -> ValidationResult:
        """
        values: {"source_name": float_or_none, ...}
        返回 ValidationResult 包含共识值、质量标注、警告信息。
        """
        th = threshold if threshold is not None else self.default_threshold
        valid = {k: v for k, v in values.items() if v is not None}

        if not valid:
            return ValidationResult(value=None, quality="single_source", sources=values)

        if len(valid) == 1:
            val = next(iter(valid.values()))
            return ValidationResult(value=val, quality="single_source", sources=values)

        vals = list(valid.values())
        mean_val = sum(vals) / len(vals)
        max_val = max(abs(v) for v in vals)

        if max_val == 0:
            return ValidationResult(value=mean_val, quality="confirmed", sources=values)

        max_diff = (max(vals) - min(vals)) / max_val

        if max_diff > th:
            warning = f"⚠️ 数据源差异 {max_diff:.1%}（{', '.join(f'{k}={v:.4g}' for k, v in valid.items())}）"
            return ValidationResult(
                value=mean_val, quality="uncertain", warning=warning, sources=values
            )

        return ValidationResult(value=mean_val, quality="confirmed", sources=values)

    def validate_fundamentals(
        self,
        *sources: dict,
        threshold: float | None = None,
    ) -> dict:
        """
        合并多个数据源的基本面 dict，对每个数字字段做交叉校验。
        返回合并后的 dict，新增 _data_quality: {field: quality} 和 _warnings: [str]。
        """
        if not sources:
            return {}

        merged = {}
        for src in sources:
            if src:
                merged.update({k: v for k, v in src.items() if not k.startswith("_")})
                break

        quality_map: dict = {}
        warnings: list = []

        for field_name in _NUMERIC_FIELDS:
            field_values = {}
            for src in sources:
                if src and field_name in src:
                    src_name = src.get("_source", f"source_{id(src)}")
                    field_values[src_name] = src[field_name]

            if not field_values:
                continue

            result = self.validate_field(field_values, threshold=threshold)
            merged[field_name] = result.value
            quality_map[field_name] = result.quality
            if result.warning:
                warnings.append(f"{field_name}: {result.warning}")

        merged["_data_quality"] = quality_map
        merged["_warnings"] = warnings

        src_names = [s.get("_source", "unknown") for s in sources if s]
        merged["data_source"] = "+".join(src_names)

        return merged
