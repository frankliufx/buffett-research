"""综合信号 — 结合技术面和基本面"""

from dataclasses import dataclass, field


@dataclass
class AnalysisResult:
    symbol: str
    name: str
    market: str
    price: float = 0
    change_pct: float = 0
    # 技术面
    tech_signal: dict = field(default_factory=dict)
    # 基本面 (巴菲特评分)
    buffett_result: dict = field(default_factory=dict)
    # 原始财务数据 (供 AI 分析使用)
    fundamentals: dict = field(default_factory=dict)
    # AI 分析
    ai_analysis: str = ""
    # 综合
    overall_score: float = 0
    recommendation: str = ""
    action: str = ""

    def compute_overall(self):
        """综合评分：基本面70% + 技术面30%"""
        fundamental_pct = self.buffett_result.get("percentage", 50)

        tech_score = self.tech_signal.get("trend_score", 0)
        # 将 trend_score (-6 到 +6) 映射到 0-100
        tech_pct = max(0, min(100, (tech_score + 6) / 12 * 100))

        self.overall_score = round(fundamental_pct * 0.7 + tech_pct * 0.3, 1)

        self.recommendation = self.buffett_result.get("recommendation", "")
        self.action = self.buffett_result.get("action", "")

        # 技术面修正
        momentum = self.tech_signal.get("momentum", "")
        if momentum == "oversold" and self.buffett_result.get("grade", "") in ("A", "B"):
            self.action += " | 技术面超卖，买入时机较好"
        elif momentum == "overbought" and self.buffett_result.get("grade", "") in ("A", "B"):
            self.action += " | 技术面超买，可等待回调再加仓"
