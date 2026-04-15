"""风险管理模块 — 波动率仓位调整 + 相关性分析

借鉴 ai-hedge-fund 的风险管理引擎：
- 基于年化波动率动态调整建议仓位
- 关注列表内股票间的相关性分析
- 输出仓位建议 + 止损位 + 风险等级
"""

import logging
import math
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_volatility(df: pd.DataFrame) -> Optional[dict]:
    """计算波动率指标

    Args:
        df: K线 DataFrame，需含 Close 列

    Returns dict:
        - daily_vol: 日波动率
        - annual_vol: 年化波动率 (daily * sqrt(252))
        - vol_percentile: 当前波动率在历史中的分位（0-100）
        - regime: 波动率 regime ("low"/<15%, "normal"/15-30%, "high"/30-50%, "extreme"/>50%)
    """
    if df is None or df.empty or len(df) < 30:
        return None

    close = df["Close"].dropna()
    if len(close) < 30:
        return None

    # 日收益率
    returns = close.pct_change().dropna()
    if len(returns) < 20:
        return None

    # 近60日波动率
    recent_returns = returns.tail(60)
    daily_vol = float(recent_returns.std())
    annual_vol = daily_vol * math.sqrt(252)

    # 滚动波动率分位数
    if len(returns) >= 120:
        rolling_vol = returns.rolling(60).std() * math.sqrt(252)
        rolling_vol = rolling_vol.dropna()
        if len(rolling_vol) > 0:
            vol_percentile = float(
                (rolling_vol < annual_vol).sum() / len(rolling_vol) * 100
            )
        else:
            vol_percentile = 50.0
    else:
        vol_percentile = 50.0

    # Regime 判定
    if annual_vol < 0.15:
        regime = "low"
    elif annual_vol < 0.30:
        regime = "normal"
    elif annual_vol < 0.50:
        regime = "high"
    else:
        regime = "extreme"

    return {
        "daily_vol": round(daily_vol, 4),
        "annual_vol": round(annual_vol, 4),
        "annual_vol_pct": round(annual_vol * 100, 1),
        "vol_percentile": round(vol_percentile, 1),
        "regime": regime,
    }


def calculate_position_limit(volatility: dict, portfolio_value: float = 100.0) -> dict:
    """基于波动率计算建议仓位上限

    借鉴 ai-hedge-fund 的仓位调整逻辑：
    - 低波动（<15%）：可配 25%
    - 正常（15-30%）：15-20%
    - 高波动（30-50%）：8-15%
    - 极端（>50%）：最多 5-10%

    Args:
        volatility: calculate_volatility() 的输出
        portfolio_value: 组合总值（百分比模式默认100）

    Returns dict:
        - max_position_pct: 建议最大仓位比例 (%)
        - risk_level: 风险等级 (低/中/高/极高)
        - rationale: 仓位建议理由
    """
    if not volatility:
        return {
            "max_position_pct": 10.0,
            "risk_level": "未知",
            "rationale": "波动率数据不足，建议保守配置",
        }

    annual_vol = volatility["annual_vol"]
    regime = volatility["regime"]

    if regime == "low":
        max_pct = 25.0
        risk_level = "低"
        rationale = "年化波动率{:.0f}%，波动极低，可以较重仓位配置".format(annual_vol * 100)
    elif regime == "normal":
        # 线性插值: 15% vol → 20%, 30% vol → 12%
        max_pct = 20.0 - (annual_vol - 0.15) / 0.15 * 8.0
        max_pct = max(12.0, min(20.0, max_pct))
        risk_level = "中"
        rationale = "年化波动率{:.0f}%，波动适中，建议中等仓位".format(annual_vol * 100)
    elif regime == "high":
        max_pct = 12.0 - (annual_vol - 0.30) / 0.20 * 4.0
        max_pct = max(8.0, min(12.0, max_pct))
        risk_level = "高"
        rationale = "年化波动率{:.0f}%，波动较大，需严格控制仓位".format(annual_vol * 100)
    else:
        max_pct = 5.0
        risk_level = "极高"
        rationale = "年化波动率{:.0f}%，波动极端，仅允许极小仓位或回避".format(annual_vol * 100)

    return {
        "max_position_pct": round(max_pct, 1),
        "risk_level": risk_level,
        "rationale": rationale,
    }


def calculate_correlation(price_series_list: list) -> Optional[dict]:
    """计算多只股票间的相关性矩阵

    Args:
        price_series_list: [{"symbol": str, "close": pd.Series}, ...]
            close 需为日频 Close 价格序列

    Returns dict:
        - correlation_matrix: dict of dict (symbol -> symbol -> corr)
        - avg_correlation: 平均相关系数
        - high_corr_pairs: 高相关性股票对 (>0.7)
        - diversification_score: 分散化得分 0-100 (越高越分散)
    """
    if not price_series_list or len(price_series_list) < 2:
        return None

    # 构建收益率 DataFrame
    returns_dict = {}
    for item in price_series_list:
        sym = item["symbol"]
        close = item["close"]
        if close is not None and len(close) >= 30:
            ret = close.pct_change().dropna()
            returns_dict[sym] = ret

    if len(returns_dict) < 2:
        return None

    # 对齐日期
    returns_df = pd.DataFrame(returns_dict).dropna()
    if len(returns_df) < 20:
        return None

    corr_matrix = returns_df.corr()

    # 提取上三角（去除对角线）
    symbols = list(corr_matrix.columns)
    pairs = []
    corr_values = []
    high_corr_pairs = []

    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            c = float(corr_matrix.iloc[i, j])
            corr_values.append(c)
            pairs.append((symbols[i], symbols[j], round(c, 3)))
            if abs(c) > 0.7:
                high_corr_pairs.append({
                    "pair": "{} / {}".format(symbols[i], symbols[j]),
                    "correlation": round(c, 3),
                    "warning": "高度正相关" if c > 0 else "高度负相关",
                })

    avg_corr = float(np.mean(corr_values)) if corr_values else 0.0

    # 分散化得分: 平均相关性越低，分散越好
    # avg_corr=0 → 100分, avg_corr=1 → 0分
    diversification_score = round(max(0, (1.0 - abs(avg_corr)) * 100), 1)

    return {
        "correlation_matrix": {
            sym: {s2: round(float(corr_matrix.loc[sym, s2]), 3) for s2 in symbols}
            for sym in symbols
        },
        "avg_correlation": round(avg_corr, 3),
        "high_corr_pairs": high_corr_pairs,
        "diversification_score": diversification_score,
        "pair_count": len(pairs),
    }


def generate_risk_report(volatility: dict, position: dict,
                         correlation: Optional[dict] = None,
                         dcf: Optional[dict] = None) -> dict:
    """汇总风险报告

    Returns:
        - summary: 一句话风险摘要
        - risk_score: 0-100 (越高风险越大)
        - recommendations: list of 建议
    """
    risk_score = 0
    recommendations = []

    # 波动率贡献
    if volatility:
        vol_pct = volatility["annual_vol"] * 100
        if vol_pct > 50:
            risk_score += 40
        elif vol_pct > 30:
            risk_score += 25
        elif vol_pct > 15:
            risk_score += 10

        if volatility["vol_percentile"] > 80:
            risk_score += 10
            recommendations.append(
                "当前波动率处于历史{:.0f}%分位，高于正常水平，建议减仓或等待波动收敛".format(
                    volatility["vol_percentile"]))

    # 仓位建议
    if position:
        if position["max_position_pct"] <= 8:
            recommendations.append(
                "建议仓位不超过{}%，波动率过高需严格控仓".format(position["max_position_pct"]))
        elif position["max_position_pct"] <= 15:
            recommendations.append(
                "建议仓位{}%左右，保持纪律性".format(position["max_position_pct"]))

    # 相关性贡献
    if correlation:
        if correlation["high_corr_pairs"]:
            risk_score += 15
            pair_names = [p["pair"] for p in correlation["high_corr_pairs"][:3]]
            recommendations.append(
                "高相关性警告：{} 走势高度同步，分散化不足".format("、".join(pair_names)))
        if correlation["diversification_score"] < 40:
            risk_score += 10
            recommendations.append(
                "分散化得分仅{:.0f}/100，建议增加低相关性标的".format(
                    correlation["diversification_score"]))

    # DCF 安全边际
    if dcf and dcf.get("method") != "insufficient":
        sm = dcf.get("safety_margin_pct", 0)
        if sm is not None:
            if sm < -30:
                risk_score += 20
                recommendations.append(
                    "严重高估：安全边际{:.0f}%，价格远超内在价值".format(sm))
            elif sm < -10:
                risk_score += 10
                recommendations.append(
                    "估值偏高：安全边际{:.0f}%，建议等待回调".format(sm))
            elif sm > 30:
                recommendations.append(
                    "安全边际充足（{:.0f}%），估值具有吸引力".format(sm))

    risk_score = min(100, risk_score)

    # 风险摘要
    if risk_score >= 60:
        summary = "高风险 — 波动大、估值偏高或集中度过高，建议谨慎"
    elif risk_score >= 30:
        summary = "中等风险 — 整体可控，注意仓位管理和止损纪律"
    else:
        summary = "低风险 — 波动率合理、估值有安全边际"

    if not recommendations:
        recommendations.append("各项风险指标正常，保持当前策略即可")

    return {
        "summary": summary,
        "risk_score": risk_score,
        "recommendations": recommendations,
    }
