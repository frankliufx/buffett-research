"""技术分析 — 辅助择时（巴菲特体系中的次要参考）

增强版：5策略集成（借鉴 ai-hedge-fund 的技术分析引擎）
1. 趋势跟踪 (EMA 多周期 + ADX)
2. 均值回归 (Z-score + 布林带 + RSI)
3. 多时间框架动量 (1月/3月/6月加权)
4. 波动率 Regime
5. 统计套利 (Hurst 指数)
"""

import math
import pandas as pd
import numpy as np
import ta


def compute_indicators(df: pd.DataFrame, config=None) -> pd.DataFrame:
    """计算全部技术指标（含增强指标）"""
    if df.empty or len(df) < 20:
        return df

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # 均线
    for period in (config.sma_periods if config else [20, 50, 200]):
        if len(df) >= period:
            df[f"SMA_{period}"] = ta.trend.SMAIndicator(close, window=period).sma_indicator()

    # EMA (增强：8/21/55 三周期，用于趋势跟踪策略)
    for ema_period in [8, 12, 21, 26, 55]:
        if len(df) >= ema_period:
            df[f"EMA_{ema_period}"] = ta.trend.EMAIndicator(close, window=ema_period).ema_indicator()

    # RSI
    rsi_period = config.rsi_period if config else 14
    df["RSI"] = ta.momentum.RSIIndicator(close, window=rsi_period).rsi()

    # MACD
    macd = ta.trend.MACD(close)
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"] = macd.macd_diff()

    # 布林带
    bb = ta.volatility.BollingerBands(close)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_middle"] = bb.bollinger_mavg()
    df["BB_lower"] = bb.bollinger_lband()

    # ATR (波动率)
    df["ATR"] = ta.volatility.AverageTrueRange(high, low, close).average_true_range()

    # 成交量均线
    df["Volume_SMA_20"] = volume.rolling(window=20).mean()

    # ── 增强指标 ──────────────────────────────────────────────
    # ADX 趋势强度
    if len(df) >= 14:
        adx_ind = ta.trend.ADXIndicator(high, low, close, window=14)
        df["ADX"] = adx_ind.adx()

    return df


def generate_technical_signal(df: pd.DataFrame) -> dict:
    """生成技术分析信号"""
    if df.empty or len(df) < 50:
        return {"trend": "unknown", "momentum": "unknown", "signals": []}

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    signals = []

    # 趋势判断
    price = latest["Close"]
    trend_scores = 0

    if "SMA_20" in latest and pd.notna(latest["SMA_20"]):
        if price > latest["SMA_20"]:
            trend_scores += 1
        else:
            trend_scores -= 1

    if "SMA_50" in latest and pd.notna(latest["SMA_50"]):
        if price > latest["SMA_50"]:
            trend_scores += 1
        else:
            trend_scores -= 1

    if "SMA_200" in latest and pd.notna(latest["SMA_200"]):
        if price > latest["SMA_200"]:
            trend_scores += 2  # 200日线权重更大
            signals.append("价格在200日均线之上，长期趋势向好")
        else:
            trend_scores -= 2
            signals.append("价格在200日均线之下，长期趋势偏弱")

    # 金叉/死叉
    if "SMA_50" in latest and "SMA_200" in latest:
        if pd.notna(latest["SMA_50"]) and pd.notna(latest["SMA_200"]):
            if pd.notna(prev.get("SMA_50")) and pd.notna(prev.get("SMA_200")):
                if prev["SMA_50"] <= prev["SMA_200"] and latest["SMA_50"] > latest["SMA_200"]:
                    signals.append("50/200日均线金叉，中长期看多信号")
                    trend_scores += 2
                elif prev["SMA_50"] >= prev["SMA_200"] and latest["SMA_50"] < latest["SMA_200"]:
                    signals.append("50/200日均线死叉，中长期看空信号")
                    trend_scores -= 2

    # RSI
    rsi = latest.get("RSI")
    momentum = "neutral"
    if pd.notna(rsi):
        if rsi > 70:
            momentum = "overbought"
            signals.append(f"RSI={rsi:.1f}，超买区域，短期可能回调")
        elif rsi < 30:
            momentum = "oversold"
            signals.append(f"RSI={rsi:.1f}，超卖区域，短期可能反弹")
        elif rsi > 50:
            momentum = "strong"
        else:
            momentum = "weak"

    # MACD
    macd_hist = latest.get("MACD_hist")
    if pd.notna(macd_hist):
        prev_hist = prev.get("MACD_hist")
        if pd.notna(prev_hist):
            if prev_hist <= 0 and macd_hist > 0:
                signals.append("MACD柱状图翻红，短期动能转强")
            elif prev_hist >= 0 and macd_hist < 0:
                signals.append("MACD柱状图翻绿，短期动能转弱")

    # 布林带位置
    bb_upper = latest.get("BB_upper")
    bb_lower = latest.get("BB_lower")
    if pd.notna(bb_upper) and pd.notna(bb_lower):
        if price >= bb_upper:
            signals.append("价格触及布林带上轨，短期压力较大")
        elif price <= bb_lower:
            signals.append("价格触及布林带下轨，可能存在支撑")

    # 量价关系
    vol = latest.get("Volume", 0)
    vol_avg = latest.get("Volume_SMA_20", 0)
    if pd.notna(vol) and pd.notna(vol_avg) and vol_avg > 0:
        vol_ratio = vol / vol_avg
        if vol_ratio > 2:
            signals.append(f"成交量放大{vol_ratio:.1f}倍，关注量价配合")

    # 支撑位/阻力位
    support = bb_lower if pd.notna(bb_lower) else None
    resistance = bb_upper if pd.notna(bb_upper) else None

    trend = "bullish" if trend_scores >= 2 else ("bearish" if trend_scores <= -2 else "neutral")

    return {
        "trend": trend,
        "trend_score": trend_scores,
        "momentum": momentum,
        "rsi": float(rsi) if pd.notna(rsi) else None,
        "macd_hist": float(macd_hist) if pd.notna(macd_hist) else None,
        "support": float(support) if support and pd.notna(support) else None,
        "resistance": float(resistance) if resistance and pd.notna(resistance) else None,
        "signals": signals,
        "price": float(price),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5 策略集成分析引擎 — 借鉴 ai-hedge-fund 的技术分析架构
# ══════════════════════════════════════════════════════════════════════════════

def _calc_hurst(series: pd.Series, max_lag: int = 20) -> float:
    """计算 Hurst 指数 (简化版 R/S 法)

    H < 0.5: 均值回归
    H = 0.5: 随机游走
    H > 0.5: 趋势延续
    """
    if len(series) < max_lag * 3:
        return 0.5  # 数据不足，返回随机游走

    lags = range(2, max_lag + 1)
    tau = []
    for lag in lags:
        pp = series.diff(lag).dropna()
        if len(pp) > 0:
            tau.append(np.sqrt(np.abs(pp).mean()))
        else:
            tau.append(0)

    # log-log 线性回归
    valid = [(l, t) for l, t in zip(lags, tau) if t > 0]
    if len(valid) < 3:
        return 0.5

    log_lags = np.log([v[0] for v in valid])
    log_tau = np.log([v[1] for v in valid])

    try:
        poly = np.polyfit(log_lags, log_tau, 1)
        return float(np.clip(poly[0], 0.0, 1.0))
    except (np.linalg.LinAlgError, ValueError):
        return 0.5


def _strategy_trend_following(df: pd.DataFrame) -> dict:
    """策略1: 趋势跟踪 (EMA 8/21/55 + ADX)"""
    latest = df.iloc[-1]
    signal = 0.0
    confidence = 0.0

    ema8 = latest.get("EMA_8")
    ema21 = latest.get("EMA_21")
    ema55 = latest.get("EMA_55")
    adx = latest.get("ADX")

    if pd.notna(ema8) and pd.notna(ema21) and pd.notna(ema55):
        if ema8 > ema21 > ema55:
            signal = 1.0  # 完美多头排列
        elif ema8 < ema21 < ema55:
            signal = -1.0  # 完美空头排列
        elif ema8 > ema21:
            signal = 0.5
        elif ema8 < ema21:
            signal = -0.5

        # ADX 加强置信度
        if pd.notna(adx):
            confidence = min(float(adx) / 100.0, 1.0)
        else:
            confidence = 0.5
    else:
        confidence = 0.0

    return {"signal": signal, "confidence": confidence, "name": "趋势跟踪"}


def _strategy_mean_reversion(df: pd.DataFrame) -> dict:
    """策略2: 均值回归 (Z-score + 布林带 + RSI)"""
    latest = df.iloc[-1]
    close = latest["Close"]
    signal = 0.0
    confidence = 0.0

    # Z-score (相对50日均线)
    sma50 = latest.get("SMA_50")
    if pd.notna(sma50) and sma50 > 0:
        close_series = df["Close"].tail(50)
        if len(close_series) >= 20:
            std = float(close_series.std())
            if std > 0:
                z_score = (close - sma50) / std
            else:
                z_score = 0
        else:
            z_score = 0
    else:
        z_score = 0

    # 布林带位置 (0-100)
    bb_upper = latest.get("BB_upper")
    bb_lower = latest.get("BB_lower")
    if pd.notna(bb_upper) and pd.notna(bb_lower) and bb_upper != bb_lower:
        bb_position = (close - bb_lower) / (bb_upper - bb_lower) * 100
    else:
        bb_position = 50

    # RSI
    rsi = latest.get("RSI")
    rsi_val = float(rsi) if pd.notna(rsi) else 50

    # 综合信号
    if z_score < -2 and bb_position < 20 and rsi_val < 30:
        signal = 1.0  # 极度超卖，均值回归买入
        confidence = min(abs(z_score) / 4, 1.0)
    elif z_score > 2 and bb_position > 80 and rsi_val > 70:
        signal = -1.0  # 极度超买，均值回归卖出
        confidence = min(abs(z_score) / 4, 1.0)
    elif z_score < -1:
        signal = 0.5
        confidence = 0.5
    elif z_score > 1:
        signal = -0.5
        confidence = 0.5

    return {"signal": signal, "confidence": confidence, "name": "均值回归"}


def _strategy_momentum(df: pd.DataFrame) -> dict:
    """策略3: 多时间框架动量 (1月/3月/6月加权收益)"""
    close = df["Close"]
    n = len(close)
    signal = 0.0
    confidence = 0.0

    returns = {}
    if n >= 21:
        returns["1m"] = float((close.iloc[-1] / close.iloc[-21] - 1) * 100)
    if n >= 63:
        returns["3m"] = float((close.iloc[-1] / close.iloc[-63] - 1) * 100)
    if n >= 126:
        returns["6m"] = float((close.iloc[-1] / close.iloc[-126] - 1) * 100)

    if not returns:
        return {"signal": 0, "confidence": 0, "name": "多周期动量"}

    # 加权动量 (1月 40%, 3月 30%, 6月 30%)
    weights = {"1m": 0.4, "3m": 0.3, "6m": 0.3}
    weighted_return = 0.0
    total_w = 0.0
    for period, ret in returns.items():
        w = weights.get(period, 0.3)
        weighted_return += ret * w
        total_w += w

    if total_w > 0:
        weighted_return /= total_w

    # 量价确认
    vol_ratio = 1.0
    latest = df.iloc[-1]
    vol = latest.get("Volume", 0)
    vol_avg = latest.get("Volume_SMA_20", 0)
    if pd.notna(vol) and pd.notna(vol_avg) and vol_avg > 0:
        vol_ratio = float(vol / vol_avg)

    if weighted_return > 5:
        signal = 1.0 if vol_ratio > 1.2 else 0.7
    elif weighted_return > 0:
        signal = 0.3
    elif weighted_return < -5:
        signal = -1.0 if vol_ratio > 1.2 else -0.7
    elif weighted_return < 0:
        signal = -0.3

    confidence = min(abs(weighted_return) / 20, 1.0)

    return {"signal": signal, "confidence": confidence, "name": "多周期动量"}


def _strategy_volatility_regime(df: pd.DataFrame) -> dict:
    """策略4: 波动率 Regime 识别"""
    close = df["Close"]
    if len(close) < 60:
        return {"signal": 0, "confidence": 0, "name": "波动率Regime"}

    returns = close.pct_change().dropna()
    if len(returns) < 60:
        return {"signal": 0, "confidence": 0, "name": "波动率Regime"}

    current_vol = float(returns.tail(20).std())
    ma_vol = float(returns.tail(60).std())

    if ma_vol == 0:
        return {"signal": 0, "confidence": 0, "name": "波动率Regime"}

    vol_ratio = current_vol / ma_vol

    # 低波动 → 可能即将扩张（看多机会）
    # 高波动 → 可能即将收缩（风险增加）
    if vol_ratio < 0.7:
        signal = 0.5  # 波动率压缩，可能爆发
        confidence = min((1 - vol_ratio) / 0.5, 1.0)
    elif vol_ratio > 1.5:
        signal = -0.5  # 波动率过高，风险大
        confidence = min((vol_ratio - 1) / 1.5, 1.0)
    else:
        signal = 0.0
        confidence = 0.3

    return {"signal": signal, "confidence": confidence, "name": "波动率Regime"}


def _strategy_stat_arb(df: pd.DataFrame) -> dict:
    """策略5: 统计套利 (Hurst 指数)"""
    close = df["Close"]
    if len(close) < 100:
        return {"signal": 0, "confidence": 0, "name": "统计套利"}

    hurst = _calc_hurst(close)

    # Hurst < 0.4: 均值回归市场 → 用均值回归策略买入超卖
    # Hurst > 0.6: 趋势市场 → 跟随趋势
    latest = df.iloc[-1]
    rsi = latest.get("RSI")
    rsi_val = float(rsi) if pd.notna(rsi) else 50

    if hurst < 0.4:
        # 均值回归 regime
        if rsi_val < 35:
            signal = 0.8
        elif rsi_val > 65:
            signal = -0.8
        else:
            signal = 0.0
        confidence = min((0.5 - hurst) / 0.3, 1.0)
    elif hurst > 0.6:
        # 趋势 regime
        sma50 = latest.get("SMA_50")
        if pd.notna(sma50):
            signal = 0.8 if latest["Close"] > sma50 else -0.8
        else:
            signal = 0.0
        confidence = min((hurst - 0.5) / 0.3, 1.0)
    else:
        signal = 0.0
        confidence = 0.2

    return {"signal": signal, "confidence": confidence, "name": "统计套利",
            "hurst": round(hurst, 3)}


def generate_ensemble_signal(df: pd.DataFrame) -> dict:
    """5策略集成信号 — 加权投票

    权重:
    - 趋势跟踪: 25%
    - 均值回归: 20%
    - 多周期动量: 25%
    - 波动率Regime: 15%
    - 统计套利: 15%

    Returns dict:
        - ensemble_signal: -1.0 to +1.0
        - ensemble_verdict: 看多/看空/中性
        - strategies: list of each strategy result
        - hurst: Hurst 指数
    """
    if df.empty or len(df) < 50:
        return {
            "ensemble_signal": 0,
            "ensemble_verdict": "数据不足",
            "strategies": [],
        }

    strategies = [
        (_strategy_trend_following(df), 0.25),
        (_strategy_mean_reversion(df), 0.20),
        (_strategy_momentum(df), 0.25),
        (_strategy_volatility_regime(df), 0.15),
        (_strategy_stat_arb(df), 0.15),
    ]

    weighted_signal = 0.0
    total_weight = 0.0
    strategy_results = []

    for strat, weight in strategies:
        w = weight * strat["confidence"]
        weighted_signal += strat["signal"] * w
        total_weight += weight
        strategy_results.append({
            "name": strat["name"],
            "signal": round(strat["signal"], 2),
            "confidence": round(strat["confidence"], 2),
            "weight": weight,
            "hurst": strat.get("hurst"),
        })

    if total_weight > 0:
        ensemble = weighted_signal / total_weight
    else:
        ensemble = 0.0

    ensemble = max(-1.0, min(1.0, ensemble))

    if ensemble >= 0.3:
        verdict = "技术面看多"
    elif ensemble <= -0.3:
        verdict = "技术面看空"
    else:
        verdict = "技术面中性"

    # 提取 Hurst
    hurst = None
    for s in strategy_results:
        if s.get("hurst") is not None:
            hurst = s["hurst"]

    return {
        "ensemble_signal": round(ensemble, 3),
        "ensemble_verdict": verdict,
        "strategies": strategy_results,
        "hurst": hurst,
    }
