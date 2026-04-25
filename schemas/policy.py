"""A股政策面板的数据契约 (Pydantic v2)。

The single source of truth for the China A-share policy panel. Five
五年规划 (Five-Year Plan) themes plus per-stock alignment plus lifecycle
phase live here so the loader, the AI prompts, the Streamlit panel and
the (future) Next.js client all consume the same shapes.

Curation note: theme data lives in `data/cn_policy_themes.yaml` and is
maintained as a product asset (see schemas/__init__.py for the boundary).
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# 政策周期阶段 — 决定持仓节奏 (early/peak/late entry)。
LifecyclePhase = Literal["蓄势期", "爆发期", "退坡期", "未知"]

# 主题层级。Tier 1 = 国家核心主线；Tier 2 = 受益方向；Tier 3 = 政策外延。
ThemeTier = Literal[1, 2, 3]

# 五年规划期。
PlanCycle = Literal["十四五", "十五五"]


class _Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


class PolicyLifecycle(_Loose):
    """主题在政策周期中的位置（人工标注，季度 review）。"""

    phase: LifecyclePhase = "未知"
    since: Optional[date] = None
    last_catalyst: Optional[date] = Field(
        default=None,
        description="最近一次最高级别政策表态（部委文件/中央会议/国务院常务会议）",
    )
    next_window: Optional[date] = Field(
        default=None,
        description="下一次预期催化窗口（下次部委部署/规划落地节点）",
    )
    decay_after: Optional[date] = Field(
        default=None,
        description="预期退坡时点（补贴退出/政策周期收尾）",
    )
    notes: Optional[str] = None


class PolicyTheme(_Loose):
    """单个政策主题的完整画像（来自 YAML）。"""

    id: str = Field(description="稳定 slug — 不要改，会被 git 历史依赖")
    name: str = Field(description="主题中文名 — 会在 UI 卡片标题展示")
    plan: PlanCycle
    pillar: str = Field(description="上位主线（如：新质生产力、安全自主可控）")
    tier: ThemeTier
    lifecycle: PolicyLifecycle = Field(default_factory=PolicyLifecycle)
    keywords: list[str] = Field(
        default_factory=list,
        description="用于匹配概念板块的关键词（粗匹配，子串包含即命中）",
    )
    related_industries: list[str] = Field(
        default_factory=list,
        description="申万二级行业名（用于按行业反查）",
    )


class PolicyThemeMatch(_Loose):
    """单个主题对单只股票的匹配结果（带匹配证据）。"""

    theme_id: str
    theme_name: str
    tier: ThemeTier
    phase: LifecyclePhase
    matched_concepts: list[str] = Field(
        default_factory=list,
        description="该股票命中的具体概念板块名称",
    )
    matched_keywords: list[str] = Field(default_factory=list)


class PolicyAlignment(_Loose):
    """单只股票的主题对齐汇总（取代旧的 dict 返回值）。"""

    symbol: str
    score: float = Field(ge=0, description="0-100 综合对齐分（详见 policy_themes.score()）")
    level: Literal["核心主线", "受益方向", "暂无明显政策主题"]
    matches: list[PolicyThemeMatch] = Field(default_factory=list)
    raw_concepts: list[str] = Field(
        default_factory=list,
        description="股票所属概念板块原始列表（含非政策类）",
    )


class LifecycleSignal(_Loose):
    """三档周期信号灯（替代单点判断），用于 UI 信号灯渲染。

    每档表示一个时间窗口的信号强度：
      - past:    回看近期催化是否仍在窗口内
      - current: 当前周期阶段的强度
      - future:  下次窗口接近度
    每档 0/1/2 → 灯色 灰/黄/绿（退坡期会变红）。
    """

    past: int = Field(0, ge=0, le=2)
    current: int = Field(0, ge=0, le=2)
    future: int = Field(0, ge=0, le=2)
    label: str = "未知"
    color: str = "#5A5A6A"
