"""政策主题加载器 + 对齐评分。

Sources `data/cn_policy_themes.yaml` (the curated knowledge base) and
exposes typed accessors. This module replaces the hardcoded keyword
lists in `src/data/policy.py` — the legacy module continues to work
and now delegates to this loader for keyword data.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from schemas.policy import (
    PolicyAlignment,
    PolicyTheme,
    PolicyThemeMatch,
)

logger = logging.getLogger(__name__)

_THEMES_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "cn_policy_themes.yaml"


# ── Loading ──────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def load_themes() -> list[PolicyTheme]:
    """Load and validate `cn_policy_themes.yaml`. Cached process-wide."""
    if not _THEMES_FILE.exists():
        logger.warning("policy themes file missing: %s", _THEMES_FILE)
        return []
    try:
        with open(_THEMES_FILE, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        raw = doc.get("themes") or []
        themes = [PolicyTheme.model_validate(t) for t in raw]
        return themes
    except Exception as e:
        logger.warning("failed to load policy themes: %s", e)
        return []


def reload_themes() -> list[PolicyTheme]:
    """Bypass the lru_cache (for tests / manual edits during dev)."""
    load_themes.cache_clear()
    return load_themes()


def all_keywords() -> list[str]:
    """Flat list of every keyword across all themes (for legacy callers)."""
    out: list[str] = []
    for t in load_themes():
        out.extend(t.keywords)
    return out


def themes_by_tier(tier: int) -> list[PolicyTheme]:
    return [t for t in load_themes() if t.tier == tier]


def find_theme(theme_id: str) -> Optional[PolicyTheme]:
    return next((t for t in load_themes() if t.id == theme_id), None)


# ── Matching ─────────────────────────────────────────────────────────────────


def _theme_matches_concepts(theme: PolicyTheme, concepts: list[str]) -> tuple[list[str], list[str]]:
    """Return (matched_concepts, matched_keywords). Substring containment."""
    matched_concepts: list[str] = []
    matched_keywords: list[str] = []
    for kw in theme.keywords:
        kw_hits: list[str] = []
        for c in concepts:
            if kw in c:
                kw_hits.append(c)
        if kw_hits:
            matched_keywords.append(kw)
            for c in kw_hits:
                if c not in matched_concepts:
                    matched_concepts.append(c)
    return matched_concepts, matched_keywords


# Tier-weighted scoring used by `score_alignment`.
#   tier 1 = 30 pts/theme (cap 60), tier 2 = 12 pts/theme (cap 24),
#   tier 3 = 5 pts/theme (cap 16). Score capped at 100.
_TIER_WEIGHTS = {1: 30, 2: 12, 3: 5}
_TIER_CAPS = {1: 60, 2: 24, 3: 16}


def score_alignment(symbol: str, concepts: list[str]) -> PolicyAlignment:
    """Compute the structured alignment for a stock given its concept list.

    Args:
        symbol:    Stock symbol (used only as identifier in the result).
        concepts:  List of concept-board names the stock belongs to. The
                   caller is responsible for fetching this (typically
                   via akshare in `src/data/policy.py`).

    Returns:
        A `PolicyAlignment` with per-theme matches and a 0-100 score.
    """
    matches: list[PolicyThemeMatch] = []
    tier_points: dict[int, int] = {1: 0, 2: 0, 3: 0}

    for theme in load_themes():
        mc, mk = _theme_matches_concepts(theme, concepts)
        if not mc:
            continue
        matches.append(
            PolicyThemeMatch(
                theme_id=theme.id,
                theme_name=theme.name,
                tier=theme.tier,
                phase=theme.lifecycle.phase,
                matched_concepts=mc,
                matched_keywords=mk,
            )
        )
        tier_points[theme.tier] = min(
            tier_points.get(theme.tier, 0) + _TIER_WEIGHTS.get(theme.tier, 0),
            _TIER_CAPS.get(theme.tier, 0),
        )

    score = float(min(sum(tier_points.values()), 100))

    if score >= 50:
        level = "核心主线"
    elif score >= 12:
        level = "受益方向"
    else:
        level = "暂无明显政策主题"

    matches.sort(key=lambda m: (m.tier, -len(m.matched_concepts)))

    return PolicyAlignment(
        symbol=symbol,
        score=score,
        level=level,
        matches=matches,
        raw_concepts=list(concepts),
    )
