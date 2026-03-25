"""技术分析 — 辅助择时（巴菲特体系中的次要参考）"""

import pandas as pd
import ta


def compute_indicators(df: pd.DataFrame, config=None) -> pd.DataFrame:
    """计算全部技术指标"""
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

    # EMA
    df["EMA_12"] = ta.trend.EMAIndicator(close, window=12).ema_indicator()
    df["EMA_26"] = ta.trend.EMAIndicator(close, window=26).ema_indicator()

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
