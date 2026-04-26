"""
Quant Edge — Macro Engine
Calculates macro regime: DXY trend, yield direction, VIX/risk environment.
This feeds into every pair's analysis as context.
"""
import pandas as pd
import numpy as np
from typing import Optional
from ta.trend import ADXIndicator, SMAIndicator


def calculate_macro_context(macro_data: dict) -> dict:
    """
    Process raw macro dataframes into a structured MacroContext.

    Args:
        macro_data: dict from DataFetcher.fetch_macro_data()
            Keys: "DXY", "DXY_1h", "US10Y", "VIX"

    Returns:
        Structured macro context dict with all computed values.
    """
    context = {
        "dxy": _analyze_dxy(macro_data.get("DXY"), macro_data.get("DXY_1h")),
        "yields": _analyze_yields(macro_data.get("US10Y")),
        "vix": _analyze_vix(macro_data.get("VIX")),
        "macro_regime": "neutral",  # Will be determined below
    }

    # ── Determine overall macro regime ──
    context["macro_regime"] = _determine_regime(context)

    return context


def _analyze_dxy(daily_df: Optional[pd.DataFrame], hourly_df: Optional[pd.DataFrame]) -> dict:
    """Analyze Dollar Index for trend, momentum, and direction."""
    result = {
        "value": None,
        "change_pct": None,
        "trend": "unknown",
        "adx": None,
        "sma_20_position": "unknown",  # above/below SMA20
        "momentum": "unknown",         # strengthening/weakening/flat
        "bias": "unknown",             # bullish/bearish/neutral
    }

    if daily_df is None or daily_df.empty:
        return result

    df = daily_df.copy()
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest

    result["value"] = round(float(latest["Close"]), 2)
    result["change_pct"] = round(((latest["Close"] - prev["Close"]) / prev["Close"]) * 100, 3)

    # ADX for DXY trend strength
    if len(df) >= 20:
        try:
            adx = ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=14)
            adx_val = adx.adx().iloc[-1]
            result["adx"] = round(float(adx_val), 1) if not pd.isna(adx_val) else None
        except Exception:
            pass

    # SMA20 position
    if len(df) >= 20:
        sma20 = df["Close"].rolling(20).mean().iloc[-1]
        result["sma_20_position"] = "above" if latest["Close"] > sma20 else "below"

    # 5-day momentum (rate of change)
    if len(df) >= 6:
        close_5_ago = df["Close"].iloc[-6]
        roc = ((latest["Close"] - close_5_ago) / close_5_ago) * 100
        if roc > 0.15:
            result["momentum"] = "strengthening"
        elif roc < -0.15:
            result["momentum"] = "weakening"
        else:
            result["momentum"] = "flat"

    # Overall DXY bias
    above_sma = result["sma_20_position"] == "above"
    strong_trend = result["adx"] and result["adx"] > 25
    positive_change = result["change_pct"] and result["change_pct"] > 0

    if above_sma and (positive_change or strong_trend):
        result["bias"] = "bullish"
        result["trend"] = "uptrend"
    elif not above_sma and (not positive_change or not strong_trend):
        result["bias"] = "bearish"
        result["trend"] = "downtrend"
    else:
        result["bias"] = "neutral"
        result["trend"] = "sideways"

    return result


def _analyze_yields(daily_df: Optional[pd.DataFrame]) -> dict:
    """Analyze US 10-Year Treasury Yield for direction and level."""
    result = {
        "value": None,
        "change_pct": None,
        "direction": "unknown",  # rising/falling/flat
        "level": "unknown",      # high/normal/low
    }

    if daily_df is None or daily_df.empty:
        return result

    df = daily_df.copy()
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest

    result["value"] = round(float(latest["Close"]), 2)
    result["change_pct"] = round(((latest["Close"] - prev["Close"]) / max(prev["Close"], 0.01)) * 100, 3)

    # 5-day direction
    if len(df) >= 6:
        close_5_ago = df["Close"].iloc[-6]
        roc = ((latest["Close"] - close_5_ago) / max(close_5_ago, 0.01)) * 100
        if roc > 0.5:
            result["direction"] = "rising"
        elif roc < -0.5:
            result["direction"] = "falling"
        else:
            result["direction"] = "flat"

    # Yield level classification
    yield_val = latest["Close"]
    if yield_val > 4.5:
        result["level"] = "high"
    elif yield_val > 3.5:
        result["level"] = "normal"
    else:
        result["level"] = "low"

    return result


def _analyze_vix(daily_df: Optional[pd.DataFrame]) -> dict:
    """Analyze VIX for risk regime classification."""
    result = {
        "value": None,
        "change_pct": None,
        "regime": "unknown",     # low/normal/elevated/extreme
        "risk_env": "unknown",   # risk_on/risk_off/neutral
    }

    if daily_df is None or daily_df.empty:
        return result

    df = daily_df.copy()
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest

    result["value"] = round(float(latest["Close"]), 2)
    result["change_pct"] = round(((latest["Close"] - prev["Close"]) / max(prev["Close"], 0.01)) * 100, 2)

    vix_val = latest["Close"]

    # VIX regime classification
    if vix_val < 15:
        result["regime"] = "low"
        result["risk_env"] = "risk_on"
    elif vix_val < 20:
        result["regime"] = "normal"
        result["risk_env"] = "neutral"
    elif vix_val < 30:
        result["regime"] = "elevated"
        result["risk_env"] = "risk_off"
    else:
        result["regime"] = "extreme"
        result["risk_env"] = "risk_off"

    return result


def _determine_regime(context: dict) -> str:
    """
    Determine overall macro regime based on all components.
    Returns: 'risk_on', 'risk_off', or 'neutral'
    """
    signals = []

    # VIX signal
    vix_env = context.get("vix", {}).get("risk_env", "neutral")
    signals.append(vix_env)

    # DXY signal (strong dollar = risk_off for Gold/EUR, risk_on for USD pairs)
    dxy_bias = context.get("dxy", {}).get("bias", "neutral")
    if dxy_bias == "bullish":
        signals.append("usd_strong")
    elif dxy_bias == "bearish":
        signals.append("usd_weak")
    else:
        signals.append("neutral")

    # Yield signal (rising yields = risk_off for traditional assets)
    yield_dir = context.get("yields", {}).get("direction", "flat")
    if yield_dir == "rising":
        signals.append("yield_rising")
    elif yield_dir == "falling":
        signals.append("yield_falling")

    # Simple voting
    risk_off_count = sum(1 for s in signals if s in ["risk_off", "usd_strong", "yield_rising"])
    risk_on_count = sum(1 for s in signals if s in ["risk_on", "usd_weak", "yield_falling"])

    if risk_off_count >= 2:
        return "risk_off"
    elif risk_on_count >= 2:
        return "risk_on"
    else:
        return "neutral"


def format_macro_summary(context: dict) -> str:
    """Format macro context into a readable summary for AI and Telegram."""
    dxy = context.get("dxy", {})
    yields = context.get("yields", {})
    vix = context.get("vix", {})
    regime = context.get("macro_regime", "unknown")

    lines = []
    lines.append("🏛️ MACRO CONTEXT")

    # DXY
    dxy_val = dxy.get("value", "N/A")
    dxy_chg = dxy.get("change_pct", 0)
    dxy_arrow = "↑" if dxy_chg and dxy_chg > 0 else "↓" if dxy_chg and dxy_chg < 0 else "→"
    dxy_bias = dxy.get("bias", "unknown").upper()
    lines.append(f"  DXY: {dxy_val} ({dxy_arrow}{abs(dxy_chg) if dxy_chg else 0:.2f}%) — {dxy_bias}")
    if dxy.get("adx"):
        lines.append(f"  DXY ADX: {dxy['adx']} | Trend: {dxy.get('trend', 'N/A')}")

    # Yields
    y_val = yields.get("value", "N/A")
    y_dir = yields.get("direction", "N/A")
    lines.append(f"  US10Y: {y_val}% — {y_dir.capitalize()}")

    # VIX
    v_val = vix.get("value", "N/A")
    v_regime = vix.get("regime", "N/A")
    lines.append(f"  VIX: {v_val} ({v_regime.capitalize()})")

    # Overall
    regime_emoji = {"risk_on": "🟢", "risk_off": "🔴", "neutral": "🟡"}.get(regime, "⚪")
    lines.append(f"  Macro Regime: {regime_emoji} {regime.upper()}")

    return "\n".join(lines)
