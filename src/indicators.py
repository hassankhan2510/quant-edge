"""
Quant Edge — Pure Math Indicators
Every indicator returns a float. No opinions. No visuals.
Each function is self-contained and takes a DataFrame.
"""
import pandas as pd
import numpy as np
from numpy import log, polyfit, sqrt, std, subtract
from scipy import stats as scipy_stats
from ta.volatility import AverageTrueRange, BollingerBands, KeltnerChannel
from ta.trend import ADXIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator, ROCIndicator
from ta.volume import OnBalanceVolumeIndicator


# ═══════════════════════════════════════════════════════════════
# VOLATILITY INDICATORS
# ═══════════════════════════════════════════════════════════════

def atr_percent(df: pd.DataFrame, period: int = 14) -> float:
    """ATR as percentage of current price. Measures volatility regime."""
    atr = AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=period)
    atr_val = atr.average_true_range().iloc[-1]
    price = df["Close"].iloc[-1]
    return round((atr_val / price) * 100, 4) if price > 0 else 0.0


def atr_value(df: pd.DataFrame, period: int = 14) -> float:
    """Raw ATR value in price units."""
    atr = AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=period)
    return round(float(atr.average_true_range().iloc[-1]), 4)


def bollinger_bandwidth(df: pd.DataFrame, period: int = 20, std: int = 2) -> float:
    """
    Bollinger Bandwidth = (Upper - Lower) / Middle.
    Low value = volatility compression (squeeze). High = expansion.
    """
    bb = BollingerBands(close=df["Close"], window=period, window_dev=std)
    upper = bb.bollinger_hband().iloc[-1]
    lower = bb.bollinger_lband().iloc[-1]
    middle = bb.bollinger_mavg().iloc[-1]
    if middle == 0:
        return 0.0
    return round((upper - lower) / middle, 6)


def bollinger_percent_b(df: pd.DataFrame, period: int = 20, std: int = 2) -> float:
    """
    %B = (Price - Lower Band) / (Upper Band - Lower Band).
    0 = at lower band, 1 = at upper band, 0.5 = at middle.
    """
    bb = BollingerBands(close=df["Close"], window=period, window_dev=std)
    return round(float(bb.bollinger_pband().iloc[-1]), 4)


def volatility_regime(df: pd.DataFrame, period: int = 14) -> str:
    """Classify volatility regime: 'high', 'normal', 'low'."""
    atr_pct = atr_percent(df, period)
    if atr_pct > 1.5:
        return "high"
    elif atr_pct < 0.5:
        return "low"
    else:
        return "normal"


def is_bb_squeeze(df: pd.DataFrame, period: int = 20, threshold: float = 0.02) -> bool:
    """Detect Bollinger Band squeeze (low bandwidth = coiling for breakout)."""
    bw = bollinger_bandwidth(df, period)
    return bw < threshold


# ═══════════════════════════════════════════════════════════════
# STATISTICAL REGIME & SHAPE INDICATORS
# ═══════════════════════════════════════════════════════════════

def hurst_exponent(df: pd.DataFrame, lags_to_test: int = 20) -> float:
    """
    Calculate the Hurst Exponent to determine market regime.
    H > 0.55: Trending Regime
    H < 0.45: Mean Reverting
    H ~ 0.5: Random Walk
    """
    ts = df['Close'].values
    if len(ts) < 100:
        return 0.5  # default to random walk if not enough data
        
    lags = range(2, min(lags_to_test, len(ts) // 2))
    tau = [sqrt(std(subtract(ts[lag:], ts[:-lag]))) for lag in lags]
    poly = polyfit(log(list(lags)), log(tau), 1)
    return round(poly[0]*2.0, 4)


def kurtosis_skewness(df: pd.DataFrame, period: int = 20) -> dict:
    """
    Calculates Statistical Kurtosis and Skewness of returns.
    High Kurtosis = Fat tails (explosive move coming).
    Skewness = Direction of asymmetry.
    """
    returns = df['Close'].pct_change().dropna().tail(period)
    if len(returns) < 10:
        return {"kurtosis": 0.0, "skewness": 0.0}
        
    kurt = scipy_stats.kurtosis(returns)
    skew = scipy_stats.skew(returns)
    
    return {
        "kurtosis": round(float(kurt), 4),
        "skewness": round(float(skew), 4)
    }


# ═══════════════════════════════════════════════════════════════
# TREND INDICATORS
# ═══════════════════════════════════════════════════════════════

def adx_value(df: pd.DataFrame, period: int = 14) -> float:
    """ADX trend strength. >25 = strong trend, <20 = weak/ranging."""
    adx = ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=period)
    val = adx.adx().iloc[-1]
    return round(float(val), 2) if not pd.isna(val) else 0.0


def adx_direction(df: pd.DataFrame, period: int = 14) -> dict:
    """ADX with +DI/-DI for trend direction."""
    adx = ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=period)
    adx_val = adx.adx().iloc[-1]
    plus_di = adx.adx_pos().iloc[-1]
    minus_di = adx.adx_neg().iloc[-1]

    direction = "bullish" if plus_di > minus_di else "bearish"
    return {
        "adx": round(float(adx_val), 2) if not pd.isna(adx_val) else 0.0,
        "plus_di": round(float(plus_di), 2) if not pd.isna(plus_di) else 0.0,
        "minus_di": round(float(minus_di), 2) if not pd.isna(minus_di) else 0.0,
        "direction": direction,
    }


def linear_regression_slope(df: pd.DataFrame, period: int = 20) -> float:
    """
    Slope of linear regression on closing prices, normalized by price.
    Positive = uptrend, negative = downtrend. Magnitude = strength.
    """
    if len(df) < period:
        return 0.0
    closes = df["Close"].tail(period).values
    x = np.arange(period)
    slope, _, _, _, _ = scipy_stats.linregress(x, closes)
    # Normalize by price
    price = closes[-1]
    if price == 0:
        return 0.0
    return round((slope / price) * 100, 6)


def hma_direction(df: pd.DataFrame, period: int = 20) -> str:
    """Hull Moving Average direction. 'up', 'down', or 'flat'."""
    if len(df) < period:
        return "flat"

    closes = df["Close"]

    # HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
    half = max(int(period / 2), 1)
    sqrt_n = max(int(np.sqrt(period)), 1)

    wma_half = closes.rolling(half).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x) + 1)), raw=True
    )
    wma_full = closes.rolling(period).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x) + 1)), raw=True
    )

    diff = 2 * wma_half - wma_full
    hma = diff.rolling(sqrt_n).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x) + 1)), raw=True
    )

    if hma.iloc[-1] > hma.iloc[-2]:
        return "up"
    elif hma.iloc[-1] < hma.iloc[-2]:
        return "down"
    return "flat"


# ═══════════════════════════════════════════════════════════════
# MOMENTUM INDICATORS
# ═══════════════════════════════════════════════════════════════

def rsi_value(df: pd.DataFrame, period: int = 14) -> float:
    """RSI value. Standard 0-100 range."""
    rsi = RSIIndicator(close=df["Close"], window=period)
    val = rsi.rsi().iloc[-1]
    return round(float(val), 2) if not pd.isna(val) else 50.0


def rsi_condition(df: pd.DataFrame, period: int = 14,
                  overbought: float = 70, oversold: float = 30) -> str:
    """RSI condition: 'overbought', 'oversold', or 'neutral'."""
    rsi = rsi_value(df, period)
    if rsi >= overbought:
        return "overbought"
    elif rsi <= oversold:
        return "oversold"
    return "neutral"


def macd_histogram_slope(df: pd.DataFrame,
                         fast: int = 12, slow: int = 26, signal: int = 9) -> float:
    """
    Slope of MACD histogram over last 3 bars.
    Positive slope = momentum accelerating bullish.
    Negative slope = momentum accelerating bearish.
    """
    macd = MACD(close=df["Close"], window_fast=fast, window_slow=slow, window_sign=signal)
    hist = macd.macd_diff()

    if len(hist.dropna()) < 3:
        return 0.0

    recent = hist.dropna().tail(3).values
    x = np.arange(len(recent))
    slope, _, _, _, _ = scipy_stats.linregress(x, recent)

    # Normalize by price
    price = df["Close"].iloc[-1]
    if price == 0:
        return 0.0
    return round((slope / price) * 10000, 4)


def macd_values(df: pd.DataFrame,
                fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Full MACD values: line, signal, histogram."""
    macd = MACD(close=df["Close"], window_fast=fast, window_slow=slow, window_sign=signal)
    return {
        "macd_line": round(float(macd.macd().iloc[-1]), 4) if not pd.isna(macd.macd().iloc[-1]) else 0.0,
        "signal_line": round(float(macd.macd_signal().iloc[-1]), 4) if not pd.isna(macd.macd_signal().iloc[-1]) else 0.0,
        "histogram": round(float(macd.macd_diff().iloc[-1]), 4) if not pd.isna(macd.macd_diff().iloc[-1]) else 0.0,
    }


def rate_of_change(df: pd.DataFrame, period: int = 10) -> float:
    """Rate of Change (ROC) in percentage."""
    roc = ROCIndicator(close=df["Close"], window=period)
    val = roc.roc().iloc[-1]
    return round(float(val), 4) if not pd.isna(val) else 0.0


def momentum_acceleration(df: pd.DataFrame, period: int = 10) -> float:
    """
    Second derivative of momentum — acceleration.
    Positive = momentum speeding up, negative = slowing down.
    """
    roc = ROCIndicator(close=df["Close"], window=period)
    roc_series = roc.roc().dropna()
    if len(roc_series) < 3:
        return 0.0

    recent = roc_series.tail(3).values
    # First differences of ROC = acceleration
    accel = np.diff(recent)
    return round(float(accel[-1]), 4)


def rsi_divergence(df: pd.DataFrame, period: int = 14, lookback: int = 20) -> dict:
    """
    Detect RSI divergence numerically.
    Bullish: price making lower lows but RSI making higher lows.
    Bearish: price making higher highs but RSI making lower highs.
    """
    if len(df) < lookback + period:
        return {"type": "none", "strength": 0.0}

    rsi = RSIIndicator(close=df["Close"], window=period)
    rsi_series = rsi.rsi().tail(lookback)
    price_series = df["Close"].tail(lookback)

    # Find local minima and maxima (simplified — compare every 5 bars)
    chunk = 5
    if len(price_series) < chunk * 2:
        return {"type": "none", "strength": 0.0}

    # Split into two halves
    mid = len(price_series) // 2
    p1, p2 = price_series.iloc[:mid], price_series.iloc[mid:]
    r1, r2 = rsi_series.iloc[:mid], rsi_series.iloc[mid:]

    p1_low, p2_low = p1.min(), p2.min()
    p1_high, p2_high = p1.max(), p2.max()
    r1_low, r2_low = r1.min(), r2.min()
    r1_high, r2_high = r1.max(), r2.max()

    # Bullish divergence: lower price low + higher RSI low
    if p2_low < p1_low and r2_low > r1_low:
        strength = abs(r2_low - r1_low)
        return {"type": "bullish", "strength": round(strength, 2)}

    # Bearish divergence: higher price high + lower RSI high
    if p2_high > p1_high and r2_high < r1_high:
        strength = abs(r1_high - r2_high)
        return {"type": "bearish", "strength": round(strength, 2)}

    return {"type": "none", "strength": 0.0}


# ═══════════════════════════════════════════════════════════════
# VOLUME INDICATORS
# ═══════════════════════════════════════════════════════════════

def volume_ratio(df: pd.DataFrame, period: int = 20) -> float:
    """
    Current volume / SMA(volume, period).
    >1.5 = strong expansion, <0.5 = dead market.
    Returns 1.0 if volume data unavailable (Forex via AV has no volume).
    """
    if "Volume" not in df.columns or df["Volume"].sum() == 0:
        return 1.0  # Default neutral for Forex

    sma = df["Volume"].rolling(period).mean().iloc[-1]
    if sma == 0 or pd.isna(sma):
        return 1.0
    return round(float(df["Volume"].iloc[-1] / sma), 2)


def obv_slope(df: pd.DataFrame, period: int = 10) -> float:
    """
    Slope of On-Balance Volume over last N bars, normalized.
    Positive = accumulation, negative = distribution.
    """
    if "Volume" not in df.columns or df["Volume"].sum() == 0:
        return 0.0

    obv = OnBalanceVolumeIndicator(close=df["Close"], volume=df["Volume"])
    obv_series = obv.on_balance_volume().tail(period)

    if len(obv_series.dropna()) < period:
        return 0.0

    x = np.arange(len(obv_series))
    slope, _, _, _, _ = scipy_stats.linregress(x, obv_series.values)

    # Normalize by average OBV magnitude
    avg_obv = abs(obv_series.mean())
    if avg_obv == 0:
        return 0.0
    return round(slope / avg_obv, 4)


def vwap_deviation(df: pd.DataFrame) -> float:
    """
    Percentage deviation of current price from VWAP.
    Positive = above VWAP (bullish), negative = below (bearish).
    Returns 0.0 if no volume data.
    """
    if "Volume" not in df.columns or df["Volume"].sum() == 0:
        # Fallback: use price vs SMA20 as proxy
        sma20 = df["Close"].rolling(20).mean().iloc[-1]
        price = df["Close"].iloc[-1]
        if sma20 == 0 or pd.isna(sma20):
            return 0.0
        return round(((price - sma20) / sma20) * 100, 4)

    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    vwap = (typical_price * df["Volume"]).cumsum() / df["Volume"].cumsum()
    vwap_val = vwap.iloc[-1]
    price = df["Close"].iloc[-1]

    if vwap_val == 0 or pd.isna(vwap_val):
        return 0.0
    return round(((price - vwap_val) / vwap_val) * 100, 4)


def cvd_proxy(df: pd.DataFrame, period: int = 14) -> float:
    """
    Cumulative Volume Delta Proxy.
    Distributes volume based on candle close relative to high/low.
    Positive = Buying pressure, Negative = Selling pressure.
    """
    if "Volume" not in df.columns or df["Volume"].sum() == 0:
        return 0.0
        
    range_val = df["High"] - df["Low"]
    # prevent division by zero
    val_fixed = np.where(range_val == 0, 1e-8, range_val)
    
    cv_proxy = 2 * ((df["Close"] - df["Low"]) / val_fixed) - 1
    period_volume = df["Volume"].tail(period).values
    period_cv = cv_proxy.tail(period).values * period_volume
    
    return round(float(np.sum(period_cv)), 2)


def vwap_extremes(df: pd.DataFrame) -> dict:
    """
    Calculates VWAP and standard deviations to find extremes.
    Returns the VWAP limits and where the price is currently sitting.
    """
    if "Volume" not in df.columns or df["Volume"].sum() == 0:
        return {"vwap": 0.0, "vwap_z_score": 0.0, "vwap_sigma_stage": 0}
        
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    cum_vol = df["Volume"].cumsum()
    vwap = (typical_price * df["Volume"]).cumsum() / cum_vol
    
    # VWAP variance
    variance = ((typical_price - vwap) ** 2 * df["Volume"]).cumsum() / cum_vol
    vwap_std = np.sqrt(variance)
    
    price = df["Close"].iloc[-1]
    vwap_val = vwap.iloc[-1]
    std_val = vwap_std.iloc[-1]
    
    if std_val == 0 or pd.isna(std_val) or pd.isna(vwap_val) or cum_vol.iloc[-1] == 0:
         return {"vwap": 0.0, "vwap_z_score": 0.0, "vwap_sigma_stage": 0}
         
    z_score = (price - vwap_val) / std_val
    sigma_stage = int(np.floor(abs(z_score))) if z_score > 0 else -int(np.floor(abs(z_score)))
    
    return {
        "vwap": round(float(vwap_val), 4),
        "vwap_z_score": round(float(z_score), 4),
        "vwap_sigma_stage": sigma_stage
    }


# ═══════════════════════════════════════════════════════════════
# MEAN REVERSION INDICATORS
# ═══════════════════════════════════════════════════════════════

def zscore(df: pd.DataFrame, period: int = 20) -> float:
    """
    Z-Score of current price vs rolling mean/stdev.
    > +2 = extremely overbought, < -2 = extremely oversold.
    Between -1 and +1 = fair value.
    """
    closes = df["Close"]
    mean = closes.rolling(period).mean().iloc[-1]
    std = closes.rolling(period).std().iloc[-1]

    if std == 0 or pd.isna(std) or pd.isna(mean):
        return 0.0

    return round((closes.iloc[-1] - mean) / std, 4)


# ═══════════════════════════════════════════════════════════════
# LIQUIDITY / STRUCTURE INDICATORS
# ═══════════════════════════════════════════════════════════════

def wick_body_ratio(df: pd.DataFrame) -> float:
    """
    Average wick-to-body ratio of last 3 candles.
    High ratio = liquidity sweep / rejection candles.
    """
    recent = df.tail(3)
    ratios = []
    for _, row in recent.iterrows():
        body = abs(row["Close"] - row["Open"])
        upper_wick = row["High"] - max(row["Close"], row["Open"])
        lower_wick = min(row["Close"], row["Open"]) - row["Low"]
        total_wick = upper_wick + lower_wick

        if body == 0:
            ratios.append(10.0)  # Doji — all wick
        else:
            ratios.append(total_wick / body)

    return round(float(np.mean(ratios)), 2)


def false_breakout_score(df: pd.DataFrame, lookback: int = 20) -> float:
    """
    Detect false breakout probability.
    Checks if recent high/low was pierced and then price reversed.
    Returns 0-100 score (higher = more likely false breakout).
    """
    if len(df) < lookback + 3:
        return 0.0

    recent = df.tail(lookback)
    last_3 = df.tail(3)

    prev_high = recent.iloc[:-3]["High"].max()
    prev_low = recent.iloc[:-3]["Low"].min()

    latest_close = last_3.iloc[-1]["Close"]
    latest_high = last_3["High"].max()
    latest_low = last_3["Low"].min()

    score = 0.0

    # Check upside false breakout: pierced high but closed below it
    if latest_high > prev_high and latest_close < prev_high:
        pierce_pct = ((latest_high - prev_high) / prev_high) * 100
        reversal_pct = ((prev_high - latest_close) / prev_high) * 100
        score = min(50 + (reversal_pct * 20), 100)

    # Check downside false breakout: pierced low but closed above it
    elif latest_low < prev_low and latest_close > prev_low:
        pierce_pct = ((prev_low - latest_low) / prev_low) * 100
        reversal_pct = ((latest_close - prev_low) / prev_low) * 100
        score = min(50 + (reversal_pct * 20), 100)

    return round(score, 1)


# ═══════════════════════════════════════════════════════════════
# SESSION / TIME INDICATORS
# ═══════════════════════════════════════════════════════════════

def session_quality_score(current_hour_utc: int) -> float:
    """
    Score the current trading session quality (0-100).
    London+NY overlap is highest quality.
    """
    if 12 <= current_hour_utc <= 16:  # London-NY overlap
        return 100.0
    elif 7 <= current_hour_utc < 12:  # London only
        return 80.0
    elif 13 <= current_hour_utc <= 21:  # NY only
        return 70.0
    elif 0 <= current_hour_utc < 8:  # Asia
        return 40.0
    else:
        return 20.0


def is_session_active(current_hour_utc: int, allowed_sessions: list) -> bool:
    """Check if current time falls within allowed sessions."""
    from src.config import SESSIONS
    for session_name in allowed_sessions:
        session = SESSIONS.get(session_name, {})
        if session.get("open_utc", 0) <= current_hour_utc < session.get("close_utc", 24):
            return True
    return False


def get_active_session(current_hour_utc: int) -> str:
    """Get the name of the currently active session."""
    from src.config import SESSIONS
    if 12 <= current_hour_utc < 16:
        return "overlap"
    for name, times in SESSIONS.items():
        if name == "overlap":
            continue
        if times["open_utc"] <= current_hour_utc < times["close_utc"]:
            return name
    return "off_hours"


# ═══════════════════════════════════════════════════════════════
# COMPREHENSIVE CALCULATION
# ═══════════════════════════════════════════════════════════════

def calculate_all_indicators(df: pd.DataFrame, params: dict, current_hour_utc: int = 12) -> dict:
    """
    Calculate ALL indicators for a single DataFrame using pair-specific parameters.

    Args:
        df: OHLCV DataFrame
        params: indicator_params from pair_profiles
        current_hour_utc: current hour in UTC

    Returns:
        Dict with all indicator values.
    """
    result = {}

    # Volatility
    result["atr_percent"] = atr_percent(df, params.get("atr_period", 14))
    result["atr_value"] = atr_value(df, params.get("atr_period", 14))
    result["volatility_regime"] = volatility_regime(df, params.get("atr_period", 14))
    result["bb_bandwidth"] = bollinger_bandwidth(df, params.get("bb_period", 20), params.get("bb_std", 2))
    result["bb_percent_b"] = bollinger_percent_b(df, params.get("bb_period", 20), params.get("bb_std", 2))
    result["bb_squeeze"] = is_bb_squeeze(df, params.get("bb_period", 20))

    # Trend
    adx_data = adx_direction(df, params.get("adx_period", 14))
    result["adx"] = adx_data["adx"]
    result["adx_plus_di"] = adx_data["plus_di"]
    result["adx_minus_di"] = adx_data["minus_di"]
    result["adx_direction"] = adx_data["direction"]
    result["lr_slope"] = linear_regression_slope(df, params.get("lr_period", 20))
    result["hma_direction"] = hma_direction(df)

    # Momentum
    result["rsi"] = rsi_value(df, params.get("rsi_period", 14))
    result["rsi_condition"] = rsi_condition(
        df, params.get("rsi_period", 14),
        params.get("rsi_overbought", 70),
        params.get("rsi_oversold", 30)
    )
    result["macd_hist_slope"] = macd_histogram_slope(
        df, params.get("macd_fast", 12),
        params.get("macd_slow", 26),
        params.get("macd_signal", 9)
    )
    macd_data = macd_values(
        df, params.get("macd_fast", 12),
        params.get("macd_slow", 26),
        params.get("macd_signal", 9)
    )
    result["macd_line"] = macd_data["macd_line"]
    result["macd_signal_line"] = macd_data["signal_line"]
    result["macd_histogram"] = macd_data["histogram"]
    result["roc"] = rate_of_change(df, params.get("roc_period", 10))
    result["momentum_accel"] = momentum_acceleration(df, params.get("roc_period", 10))

    # RSI Divergence
    div = rsi_divergence(df, params.get("rsi_period", 14))
    result["rsi_divergence_type"] = div["type"]
    result["rsi_divergence_strength"] = div["strength"]

    # Volume & Order Flow
    result["volume_ratio"] = volume_ratio(df, params.get("vol_sma_period", 20))
    result["obv_slope"] = obv_slope(df, params.get("obv_slope_period", 10))
    result["vwap_deviation"] = vwap_deviation(df)
    result["cvd_proxy"] = cvd_proxy(df, params.get("cvd_period", 14))
    
    vwap_data = vwap_extremes(df)
    result["vwap_z_score"] = vwap_data["vwap_z_score"]
    result["vwap_sigma_stage"] = vwap_data["vwap_sigma_stage"]

    # Statistical
    result["hurst_exponent"] = hurst_exponent(df)
    result["zscore"] = zscore(df, params.get("zscore_period", 20))
    ks = kurtosis_skewness(df, params.get("ks_period", 20))
    result["kurtosis"] = ks["kurtosis"]
    result["skewness"] = ks["skewness"]

    # Liquidity / Structure
    result["wick_body_ratio"] = wick_body_ratio(df)
    result["false_breakout_score"] = false_breakout_score(df)

    # Session
    result["session_quality"] = session_quality_score(current_hour_utc)
    result["active_session"] = get_active_session(current_hour_utc)

    # Price snapshot
    result["current_price"] = round(float(df["Close"].iloc[-1]), 5)
    result["price_open"] = round(float(df["Open"].iloc[-1]), 5)
    result["price_high"] = round(float(df["High"].iloc[-1]), 5)
    result["price_low"] = round(float(df["Low"].iloc[-1]), 5)

    return result
