"""Status / loading helpers.

Standardizes the `st.status(...)` pattern introduced in P3 so future pages
get consistent labels, completion states, and auto-collapse behavior.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st


@contextmanager
def with_status(
    label: str,
    *,
    complete_label: str | None = None,
    error_label: str | None = None,
    expanded: bool = False,
) -> Iterator:
    """Context manager that wraps `st.status` with sensible defaults.

    Auto-marks the status as `complete` (with checkmark prefix) on success,
    or `error` (with cross prefix) if an exception bubbles. Always
    self-collapses so finished operations don't clutter the page.

    Yields the underlying `st.status` handle so callers can `.write(...)`
    intermediate progress lines.

    Example:
        with with_status("AI 分析中", complete_label="AI 洞察已生成") as s:
            s.write("整理上下文")
            result = call_llm(...)
    """
    status = st.status(label, expanded=expanded)
    try:
        with status:
            yield status
    except Exception:
        status.update(
            label=f"✗ {error_label or label}",
            state="error",
            expanded=True,
        )
        raise
    else:
        final_label = complete_label or label
        status.update(
            label=f"✓ {final_label}",
            state="complete",
            expanded=False,
        )
