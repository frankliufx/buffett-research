"""A股政策面板 — 公开 UI 接口。

Package boundary:
- `legacy.py`        — 旧的 hero / banner（保留向后兼容，新代码不要再用）
- `_base.py`         — 共享 CSS / fonts / formatters
- `decision_banner.py` — 综合判断横幅（替代旧 banner，吃 PolicyAlignment）
- `card_alignment.py`  — 主题对齐卡片
- `card_lifecycle.py`  — 政策周期卡片（信号灯 + 文字）
- `card_capital.py`    — 资金面卡片（A5.1 占位，A5.2 接 akshare）
- `card_risk.py`       — 风险面卡片（A5.1 占位，A5.2 接监管数据）

新代码请只导入：
    from src.ui_ashare import (
        render_decision_banner,
        render_alignment_card,
        render_lifecycle_card,
        render_capital_card,
        render_risk_card,
    )
"""

# New API (A5.1)
from src.ui_ashare.decision_banner import render_decision_banner
from src.ui_ashare.card_alignment import render_alignment_card
from src.ui_ashare.card_lifecycle import render_lifecycle_card
from src.ui_ashare.card_capital import render_capital_card
from src.ui_ashare.card_risk import render_risk_card

# Legacy API (kept working for unmigrated callers — see legacy.py)
from src.ui_ashare.legacy import (
    render_policy_hero,
    render_ashare_score_banner,
)

__all__ = [
    # new
    "render_decision_banner",
    "render_alignment_card",
    "render_lifecycle_card",
    "render_capital_card",
    "render_risk_card",
    # legacy
    "render_policy_hero",
    "render_ashare_score_banner",
]
