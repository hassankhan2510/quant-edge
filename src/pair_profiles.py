"""
Quant Edge — Per-Pair Mathematical Profiles
Each pair has its own statistical personality. Different weights, different thresholds.
This is our moat — the system isn't generic.
"""

PAIR_PROFILES = {
    # ═══════════════════════════════════════════════════════════
    # 🥇 XAUUSD (Gold)
    # Volatility-driven, macro-sensitive, mean-reverts from extremes
    # Gold moves inverse to DXY ~85% of the time
    # Real moves happen London+NY overlap
    # ═══════════════════════════════════════════════════════════
    "XAUUSD": {
        "display_name": "Gold (XAUUSD)",
        "emoji": "🥇",
        "personality": "volatility-driven, macro-sensitive, mean-reverts from extremes",
        "systems": ["day", "swing"],

        # Timeframes per system
        "day_timeframes": {
            "htf": "4h",        # Higher timeframe bias
            "primary": "1h",    # Main analysis
            "ltf": "15min",     # Entry timing
        },
        "swing_timeframes": {
            "htf": "1wk",       # Weekly context
            "primary": "1d",    # Main analysis
            "ltf": "4h",        # Confirmation
        },

        # Indicator parameters (tuned for Gold)
        "indicator_params": {
            "atr_period": 14,
            "adx_period": 14,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "bb_period": 20,
            "bb_std": 2,
            "vol_sma_period": 20,
            "zscore_period": 20,
            "zscore_extreme": 1.5,  # Gold mean-reverts aggressively
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "lr_period": 20,
            "obv_slope_period": 10,
            "roc_period": 10,
        },

        # Day trading scoring weights
        "day_scoring_weights": {
            "atr_regime": 0.25,         # Gold's daily range varies massively
            "dxy_correlation": 0.20,    # Gold-DXY inverse is critical
            "zscore_mean_rev": 0.20,    # Gold mean-reverts aggressively from extremes
            "volume_expansion": 0.15,   # Real moves need volume in Gold
            "rsi_condition": 0.10,      # RSI divergences work well on Gold
            "session_quality": 0.10,    # Gold's real moves = London+NY
        },

        # Swing scoring weights
        "swing_scoring_weights": {
            "atr_regime": 0.20,
            "dxy_correlation": 0.25,    # DXY even more important on swing
            "trend_strength": 0.20,     # ADX + slope
            "momentum": 0.15,          # MACD + ROC
            "volume_expansion": 0.10,
            "zscore_mean_rev": 0.10,
        },

        # Pre-filter gates (ALL must pass for analysis to proceed)
        "day_gates": {
            "min_adx": 18,
            "min_vol_ratio": 0.8,
            "allowed_sessions": ["london", "newyork", "overlap"],
            "no_trade_days": [],  # No specific day filter for Gold
        },
        "swing_gates": {
            "min_adx": 15,  # Lower threshold for swing (trends develop slower)
            "min_vol_ratio": 0.6,
        },

        # Key correlations to check
        "correlations": ["DXY"],
        "correlation_type": "inverse",  # Gold is inverse to DXY
    },

    # ═══════════════════════════════════════════════════════════
    # 💶 EURUSD
    # Trend-following, DXY-mirrored, consolidates then explodes
    # Bollinger squeeze detection is key
    # ═══════════════════════════════════════════════════════════
    "EURUSD": {
        "display_name": "EUR/USD",
        "emoji": "💶",
        "personality": "trend-following, DXY-mirrored, squeeze-and-explode pattern",
        "systems": ["day", "swing"],

        "day_timeframes": {
            "htf": "4h",
            "primary": "1h",
            "ltf": "15min",
        },
        "swing_timeframes": {
            "htf": "1wk",
            "primary": "1d",
            "ltf": "4h",
        },

        "indicator_params": {
            "atr_period": 14,
            "adx_period": 14,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "bb_period": 20,
            "bb_std": 2,
            "vol_sma_period": 20,
            "zscore_period": 20,
            "zscore_extreme": 2.0,  # EUR needs bigger deviation to confirm
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "lr_period": 20,
            "obv_slope_period": 10,
            "roc_period": 12,       # Slightly longer for EUR trends
        },

        "day_scoring_weights": {
            "trend_strength": 0.25,     # EUR trends cleanly
            "dxy_correlation": 0.20,    # EURUSD ≈ inverse DXY
            "bb_squeeze": 0.20,         # Squeeze → expansion is EUR's signature
            "momentum": 0.15,           # MACD histogram acceleration
            "lr_slope": 0.10,           # Trend direction quantified
            "volume_expansion": 0.10,   # Confirms institutional participation
        },

        "swing_scoring_weights": {
            "trend_strength": 0.25,
            "dxy_correlation": 0.25,
            "momentum": 0.20,
            "lr_slope": 0.15,
            "volume_expansion": 0.10,
            "atr_regime": 0.05,
        },

        "day_gates": {
            "min_adx": 18,
            "min_vol_ratio": 0.8,
            "allowed_sessions": ["london", "newyork", "overlap"],
            "no_trade_days": [],
        },
        "swing_gates": {
            "min_adx": 15,
            "min_vol_ratio": 0.5,
        },

        "correlations": ["DXY"],
        "correlation_type": "inverse",
    },

    # ═══════════════════════════════════════════════════════════
    # 💷 GBPUSD
    # Session-sensitive, volatile, fakes breakouts frequently
    # Almost exclusively a London pair
    # ═══════════════════════════════════════════════════════════
    "GBPUSD": {
        "display_name": "GBP/USD",
        "emoji": "💷",
        "personality": "session-sensitive, volatile, frequent false breakouts",
        "systems": ["day", "swing"],

        "day_timeframes": {
            "htf": "4h",
            "primary": "1h",
            "ltf": "15min",
        },
        "swing_timeframes": {
            "htf": "1wk",
            "primary": "1d",
            "ltf": "4h",
        },

        "indicator_params": {
            "atr_period": 14,
            "adx_period": 14,
            "rsi_period": 14,
            "rsi_overbought": 68,   # Slightly tighter thresholds for volatile GBP
            "rsi_oversold": 32,
            "bb_period": 20,
            "bb_std": 2,
            "vol_sma_period": 20,
            "zscore_period": 20,
            "zscore_extreme": 1.8,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "lr_period": 15,        # Shorter for GBP's faster moves
            "obv_slope_period": 10,
            "roc_period": 8,        # Shorter ROC for momentum
        },

        "day_scoring_weights": {
            "session_quality": 0.25,    # GBP is London-dominated
            "atr_regime": 0.20,         # Wider ranges, volatility matters
            "momentum": 0.20,           # GBP moves fast
            "false_breakout": 0.15,     # GBP fakes breakouts more than any major
            "dxy_correlation": 0.10,    # Less direct than EUR
            "volume_expansion": 0.10,   # Confirms real moves
        },

        "swing_scoring_weights": {
            "trend_strength": 0.25,
            "atr_regime": 0.20,
            "momentum": 0.20,
            "dxy_correlation": 0.15,
            "volume_expansion": 0.10,
            "lr_slope": 0.10,
        },

        "day_gates": {
            "min_adx": 20,              # Higher gate — GBP needs clear direction
            "min_vol_ratio": 1.0,       # Must have volume for GBP
            "allowed_sessions": ["london", "overlap"],  # Avoid NY-only for GBP
            "no_trade_days": [5],       # Avoid Friday for GBP day trading
        },
        "swing_gates": {
            "min_adx": 16,
            "min_vol_ratio": 0.6,
        },

        "correlations": ["DXY"],
        "correlation_type": "inverse",
    },

    # ═══════════════════════════════════════════════════════════
    # 💴 USDJPY
    # Carry-trade driven, yield-sensitive, trends for weeks
    # RSI extremes at 75/25 actually matter on JPY
    # ═══════════════════════════════════════════════════════════
    "USDJPY": {
        "display_name": "USD/JPY",
        "emoji": "💴",
        "personality": "carry-trade driven, yield-sensitive, strong trends, slower reversals",
        "systems": ["swing"],  # USDJPY is swing-only — too noisy for day trading

        "swing_timeframes": {
            "htf": "1wk",
            "primary": "1d",
            "ltf": "4h",
        },

        "indicator_params": {
            "atr_period": 14,
            "adx_period": 14,
            "rsi_period": 14,
            "rsi_overbought": 75,   # JPY needs extremes to signal reversal
            "rsi_oversold": 25,
            "bb_period": 20,
            "bb_std": 2,
            "vol_sma_period": 20,
            "zscore_period": 25,    # Longer window — JPY trends persist longer
            "zscore_extreme": 2.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "lr_period": 25,        # Longer for JPY's slow trends
            "obv_slope_period": 14,
            "roc_period": 14,
        },

        "swing_scoring_weights": {
            "yield_momentum": 0.25,     # US10Y yield drives JPY
            "trend_strength": 0.20,     # JPY trends for weeks
            "atr_regime": 0.15,         # Position sizing calibration
            "rsi_condition": 0.15,      # RSI extremes matter on JPY
            "lr_slope": 0.15,           # Direction clarity
            "volume_expansion": 0.10,   # Confirmation
        },

        "swing_gates": {
            "min_adx": 18,
            "min_vol_ratio": 0.5,
        },

        "correlations": ["US10Y"],
        "correlation_type": "positive",  # JPY weakens (USDJPY up) when yields rise
    },
}


def get_profile(pair: str) -> dict:
    """Get the complete profile for a pair."""
    if pair not in PAIR_PROFILES:
        raise ValueError(f"No profile defined for {pair}. Available: {list(PAIR_PROFILES.keys())}")
    return PAIR_PROFILES[pair]


def get_pairs_for_system(system: str) -> list:
    """Get all pairs configured for a specific system ('day' or 'swing')."""
    return [
        pair for pair, profile in PAIR_PROFILES.items()
        if system in profile["systems"]
    ]


def get_timeframes(pair: str, system: str) -> dict:
    """Get timeframes for a specific pair and system."""
    profile = get_profile(pair)
    key = f"{system}_timeframes"
    if key not in profile:
        raise ValueError(f"{pair} is not configured for {system} trading")
    return profile[key]


def get_scoring_weights(pair: str, system: str) -> dict:
    """Get scoring weights for a specific pair and system."""
    profile = get_profile(pair)
    key = f"{system}_scoring_weights"
    if key not in profile:
        raise ValueError(f"No {system} scoring weights defined for {pair}")
    return profile[key]


def get_gates(pair: str, system: str) -> dict:
    """Get gate filter thresholds for a specific pair and system."""
    profile = get_profile(pair)
    key = f"{system}_gates"
    if key not in profile:
        raise ValueError(f"No {system} gates defined for {pair}")
    return profile[key]
