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


class CapitalFlowDay(_Loose):
    """单日资金流（北向 / 主力）。"""

    date: date
    net_inflow_yuan: Optional[float] = Field(
        default=None,
        description="净流入金额（元）— 正=买入，负=卖出。",
    )


class CapitalFlow(_Loose):
    """资金面卡片的完整数据契约。

    All fetchers degrade gracefully — a missing data source sets the
    relevant fields to None, the UI shows a "数据加载失败" sub-line for
    that row only, and the rest of the card still renders.
    """

    symbol: str
    # 北向资金
    northbound_holding_pct: Optional[float] = Field(
        default=None,
        description="北向当前持有占流通股 %",
    )
    northbound_5d_yuan: Optional[float] = Field(
        default=None, description="北向 5 日净流入（元）"
    )
    northbound_20d_yuan: Optional[float] = Field(
        default=None, description="北向 20 日净流入（元）"
    )
    northbound_history: list[CapitalFlowDay] = Field(default_factory=list)
    # 主力资金
    main_5d_yuan: Optional[float] = Field(
        default=None, description="主力 5 日累计净流入（元）"
    )
    main_history: list[CapitalFlowDay] = Field(default_factory=list)
    # 龙虎榜
    lhb_30d_count: Optional[int] = Field(
        default=None, description="近 30 日上龙虎榜次数"
    )
    # 综合评分
    consensus_score: Optional[float] = Field(
        default=None, ge=0, le=100,
        description="资金共识评分 — 由四个子指标聚合得到 (0-100)",
    )
    consensus_label: Optional[Literal["强共识", "中性", "弱共识", "分歧"]] = None
    # 数据健康
    fetch_errors: list[str] = Field(
        default_factory=list,
        description="哪些子指标抓取失败（用于 UI 显示局部降级）",
    )


ControllerType = Literal[
    "央企", "地方国企", "民营企业", "外资企业", "公众企业", "无实控人", "未知"
]
RiskLevel = Literal["低", "中", "高", "极高"]


class RegulatoryStatus(_Loose):
    """风险面卡片的完整数据契约。"""

    symbol: str
    # ST / 退市
    is_st: Optional[bool] = None
    st_label: Optional[str] = Field(
        default=None, description="ST 类型: ST / *ST / 暂停上市 / null"
    )
    # 实控人 / 控股股东类型
    controller_type: ControllerType = "未知"
    controller_name: Optional[str] = None
    # 业绩预警
    perf_warning: Optional[str] = Field(
        default=None, description="预亏 / 预减 / null"
    )
    # CSRC 处罚
    csrc_penalty_count_3y: Optional[int] = None
    csrc_penalty_recent: Optional[str] = Field(
        default=None, description="最近一次处罚事项摘要（截断）"
    )
    # 综合风险等级
    risk_level: RiskLevel = "低"
    risk_color: str = "#3ECF8E"
    risk_reasons: list[str] = Field(default_factory=list)
    fetch_errors: list[str] = Field(default_factory=list)


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
