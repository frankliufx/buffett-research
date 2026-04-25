"""政策周期信号灯计算 — 把 YAML 标注的日期翻译成 UI 信号。

Renders three lights per theme:
    past:    最近催化是否仍在窗口内 → 0/1/2
    current: 当前周期阶段强度       → 0/1/2 (退坑期 → 红)
    future:  下次催化窗口接近度     → 0/1/2

The phase color follows our convention:
    爆发期 → green (#3ECF8E)
    蓄势期 → gold  (#C9A962)
    退坡期 → red   (#EF4444)
    未知   → gray  (#5A5A6A)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from schemas.policy import LifecyclePhase, LifecycleSignal, PolicyTheme


_PHASE_COLOR = {
    "爆发期": "#3ECF8E",
    "蓄势期": "#C9A962",
    "退坡期": "#EF4444",
    "未知":   "#5A5A6A",
}


def _days_between(a: Optional[date], b: date) -> Optional[int]:
    if a is None:
        return None
    return (b - a).days


def lifecycle_signal(theme: PolicyTheme, today: Optional[date] = None) -> LifecycleSignal:
    """Compute a 3-light signal for a theme.

    The thresholds below are tuned for quarterly policy cadence and
    deliberately conservative — this is a heuristic on top of human
    annotation, not a forecasting model.
    """
    today = today or date.today()
    lc = theme.lifecycle
    phase: LifecyclePhase = lc.phase
    color = _PHASE_COLOR.get(phase, _PHASE_COLOR["未知"])

    # 1) past — proximity to the most recent catalyst
    past = 0
    days_since = _days_between(lc.last_catalyst, today)
    if days_since is not None:
        if days_since < 60:
            past = 2          # 近2月内有催化 → 强信号
        elif days_since < 180:
            past = 1          # 近半年内 → 中信号
        else:
            past = 0

    # 2) current — phase strength
    if phase == "爆发期":
        current = 2
    elif phase == "蓄势期":
        current = 1
    elif phase == "退坡期":
        current = 0           # 退坡期当下信号弱（红色另外靠 color 表达）
    else:
        current = 0

    # 3) future — proximity to next expected window
    future = 0
    days_until = _days_between(today, lc.next_window) if lc.next_window else None
    if days_until is not None and days_until >= 0:
        if days_until < 90:
            future = 2        # 90 天内 → 强预期
        elif days_until < 180:
            future = 1
        else:
            future = 0
    elif lc.next_window is not None and days_until is not None and days_until < 0:
        # next_window 已过去 — YAML 待更新
        future = 0

    label = phase
    if phase == "爆发期" and lc.decay_after:
        days_to_decay = _days_between(today, lc.decay_after)
        if days_to_decay is not None and 0 <= days_to_decay < 365:
            label = "爆发期 · 接近退坡"
            current = 1   # 临近退坡降一档

    return LifecycleSignal(
        past=past,
        current=current,
        future=future,
        label=label,
        color=color,
    )


def aggregate_phase(themes: list[PolicyTheme]) -> tuple[LifecyclePhase, str]:
    """Across multiple themes a stock matches, return the dominant phase.

    Priority: 爆发期 (>= 1 hit) > 蓄势期 > 退坡期 > 未知.
    Reason: a stock holding any 爆发期 theme is functionally in 爆发期
    for portfolio purposes; 退坡期-only stocks are downgraded.
    """
    if not themes:
        return "未知", _PHASE_COLOR["未知"]

    phases = [t.lifecycle.phase for t in themes]
    if "爆发期" in phases:
        return "爆发期", _PHASE_COLOR["爆发期"]
    if "蓄势期" in phases:
        return "蓄势期", _PHASE_COLOR["蓄势期"]
    if "退坡期" in phases:
        return "退坡期", _PHASE_COLOR["退坡期"]
    return "未知", _PHASE_COLOR["未知"]
