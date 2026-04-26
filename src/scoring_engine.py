"""
Quant Edge — Per-Pair Scoring Engine
Two-phase decision system:
  Phase 1: Gate filters (binary pass/fail)
  Phase 2: Weighted composite score using pair-specific weights (0-100)
"""
import numpy as np
from datetime import datetime, timezone
from src.pair_profiles import get_profile, get_scoring_weights, get_gates
from src import config


def normalize_to_100(value: float, low: float, high: float, invert: bool = False) -> float:
    """
    Normalize a value to 0-100 scale between low and high bounds.
    If invert=True, lower values get higher scores.
    """
    if high == low:
        return 50.0
    score = ((value - low) / (high - low)) * 100
    score = max(0, min(100, score))
    if invert:
        score = 100 - score
    return round(score, 1)


# ═══════════════════════════════════════════════════════════════
# PHASE 1: GATE FILTERS
# Must-pass conditions. If ANY gate fails, analysis still runs
# but verdict is capped at "WAIT" or "NO TRADE"
# ═══════════════════════════════════════════════════════════════

def check_gates(metrics: dict, pair: str, system: str, current_hour_utc: int = None) -> dict:
    """
    Check pre-filter gates for a pair.

    Returns:
        {
            "all_passed": bool,
            "gates": {gate_name: {"passed": bool, "value": any, "threshold": any}},
            "failed_gates": [list of failed gate names],
        }
    """
    gates_config = get_gates(pair, system)
    results = {}
    failed = []

    # Gate: Minimum ADX (trend strength)
    min_adx = gates_config.get("min_adx", 15)
    adx_val = metrics.get("adx", 0)
    adx_passed = adx_val >= min_adx
    results["adx_minimum"] = {
        "passed": adx_passed,
        "value": adx_val,
        "threshold": min_adx,
        "description": f"ADX {adx_val:.1f} {'≥' if adx_passed else '<'} {min_adx}",
    }
    if not adx_passed:
        failed.append("adx_minimum")

    # Gate: Minimum volume ratio
    min_vol = gates_config.get("min_vol_ratio", 0.8)
    vol_val = metrics.get("volume_ratio", 1.0)
    vol_passed = vol_val >= min_vol
    results["volume_minimum"] = {
        "passed": vol_passed,
        "value": vol_val,
        "threshold": min_vol,
        "description": f"Vol Ratio {vol_val:.2f}× {'≥' if vol_passed else '<'} {min_vol}×",
    }
    if not vol_passed:
        failed.append("volume_minimum")

    # Gate: Session filter (day trading only)
    if system == "day":
        allowed = gates_config.get("allowed_sessions", ["london", "newyork", "overlap"])
        if current_hour_utc is not None:
            from src.indicators import is_session_active
            session_ok = is_session_active(current_hour_utc, allowed)
        else:
            session_ok = True  # Can't check without time
        results["session_active"] = {
            "passed": session_ok,
            "value": metrics.get("active_session", "unknown"),
            "threshold": allowed,
            "description": f"Session: {metrics.get('active_session', 'unknown')} {'✓' if session_ok else '✗'}",
        }
        if not session_ok:
            failed.append("session_active")

    # Gate: No-trade day filter
    if system == "day":
        no_trade_days = gates_config.get("no_trade_days", [])
        today = datetime.now(timezone.utc).isoweekday()  # 1=Mon, 7=Sun
        day_ok = today not in no_trade_days
        results["trade_day"] = {
            "passed": day_ok,
            "value": today,
            "threshold": f"Not in {no_trade_days}",
            "description": f"Day {today} {'✓ tradeable' if day_ok else '✗ filtered out'}",
        }
        if not day_ok:
            failed.append("trade_day")

    return {
        "all_passed": len(failed) == 0,
        "gates": results,
        "failed_gates": failed,
    }


# ═══════════════════════════════════════════════════════════════
# PHASE 2: WEIGHTED COMPOSITE SCORE
# Each factor is normalized to 0-100, then weighted per pair profile.
# ═══════════════════════════════════════════════════════════════

def _score_factor(factor_name: str, metrics: dict, pair: str) -> float:
    """
    Score an individual factor based on the pair's profile.
    Returns normalized 0-100 score.
    """
    profile = get_profile(pair)

    if factor_name == "atr_regime":
        # Score volatility: "normal" is ideal. Too high or too low = penalty.
        atr_pct = metrics.get("atr_percent", 0)
        if 0.5 <= atr_pct <= 2.0:
            return normalize_to_100(atr_pct, 0.5, 2.0)
        elif atr_pct > 2.0:
            return max(0, 100 - (atr_pct - 2.0) * 30)  # Penalty for extreme vol
        else:
            return max(0, atr_pct / 0.5 * 50)  # Low vol = low score

    elif factor_name == "trend_strength":
        adx = metrics.get("adx", 0)
        return normalize_to_100(adx, 10, 50)  # ADX 10=0, 50=100

    elif factor_name == "momentum":
        rsi = metrics.get("rsi", 50)
        macd_slope = metrics.get("macd_hist_slope", 0)
        roc = metrics.get("roc", 0)

        # RSI score: 50 is neutral, 30/70 are extremes (can be useful for mean-rev pairs)
        rsi_score = 100 - abs(rsi - 50) * 2  # Max at 50, drops toward extremes

        # MACD slope: positive is better (momentum aligned)
        macd_score = normalize_to_100(abs(macd_slope), 0, 0.05)

        # ROC contribution
        roc_score = normalize_to_100(abs(roc), 0, 2)

        return (rsi_score * 0.3 + macd_score * 0.4 + roc_score * 0.3)

    elif factor_name == "volume_expansion":
        vol = metrics.get("volume_ratio", 1.0)
        return normalize_to_100(vol, 0.5, 2.5)

    elif factor_name == "dxy_correlation":
        # This is scored based on macro context, not pair metrics
        # A correlated pair scoring depends on DXY alignment
        # For now, use VWAP deviation as proxy for directional strength
        vwap_dev = abs(metrics.get("vwap_deviation", 0))
        return normalize_to_100(vwap_dev, 0, 0.5)

    elif factor_name == "zscore_mean_rev":
        zs = abs(metrics.get("zscore", 0))
        zscore_extreme = profile.get("indicator_params", {}).get("zscore_extreme", 1.5)
        # Higher Z-score = more mean reversion potential = higher score
        return normalize_to_100(zs, 0, zscore_extreme * 1.5)

    elif factor_name == "rsi_condition":
        rsi = metrics.get("rsi", 50)
        # For mean-rev pairs: score higher at extremes
        distance_from_50 = abs(rsi - 50)
        return normalize_to_100(distance_from_50, 0, 30)

    elif factor_name == "session_quality":
        return metrics.get("session_quality", 50)

    elif factor_name == "bb_squeeze":
        bb_bw = metrics.get("bb_bandwidth", 0.01)
        squeeze = metrics.get("bb_squeeze", False)
        if squeeze:
            return 85.0  # Squeeze detected = high score (breakout coming)
        return normalize_to_100(bb_bw, 0.001, 0.05, invert=True)

    elif factor_name == "lr_slope":
        slope = abs(metrics.get("lr_slope", 0))
        return normalize_to_100(slope, 0, 0.1)

    elif factor_name == "false_breakout":
        fb = metrics.get("false_breakout_score", 0)
        # High false breakout score = avoid trade = LOWER score
        return normalize_to_100(fb, 0, 80, invert=True)

    elif factor_name == "yield_momentum":
        # Proxy: use ROC as momentum indicator
        roc = abs(metrics.get("roc", 0))
        return normalize_to_100(roc, 0, 1.5)

    else:
        return 50.0  # Unknown factor defaults to neutral


def calculate_composite_score(metrics: dict, pair: str, system: str) -> dict:
    """
    Calculate weighted composite score for a pair.

    Returns:
        {
            "composite_score": float (0-100),
            "factor_scores": {factor_name: {"score": float, "weight": float, "weighted": float}},
            "verdict": str ("EXECUTE" / "DEVELOPING" / "NO_TRADE"),
            "bias": str ("LONG" / "SHORT" / "NEUTRAL"),
        }
    """
    weights = get_scoring_weights(pair, system)
    factor_scores = {}
    total_weighted = 0.0

    for factor_name, weight in weights.items():
        score = _score_factor(factor_name, metrics, pair)
        weighted = score * weight
        factor_scores[factor_name] = {
            "score": round(score, 1),
            "weight": weight,
            "weighted": round(weighted, 2),
        }
        total_weighted += weighted

    composite = round(total_weighted, 1)

    # Determine verdict
    if composite >= config.SCORE_EXECUTE:
        verdict = "EXECUTE"
    elif composite >= config.SCORE_DEVELOPING:
        verdict = "DEVELOPING"
    else:
        verdict = "NO_TRADE"

    # Determine directional bias from indicators
    adx_dir = metrics.get("adx_direction", "neutral")
    lr_slope = metrics.get("lr_slope", 0)
    macd_hist = metrics.get("macd_histogram", 0)

    bullish_signals = sum([
        1 if adx_dir == "bullish" else 0,
        1 if lr_slope > 0 else 0,
        1 if macd_hist > 0 else 0,
    ])
    if bullish_signals >= 2:
        bias = "LONG"
    elif bullish_signals == 0:
        bias = "SHORT"
    else:
        bias = "NEUTRAL"

    return {
        "composite_score": composite,
        "factor_scores": factor_scores,
        "verdict": verdict,
        "bias": bias,
    }


def score_pair_full(metrics: dict, pair: str, system: str,
                    current_hour_utc: int = None) -> dict:
    """
    Full scoring pipeline: gates + composite.

    Returns complete scoring result with gates, composite, and final verdict.
    """
    # Phase 1: Gates
    gate_result = check_gates(metrics, pair, system, current_hour_utc)

    # Phase 2: Composite
    score_result = calculate_composite_score(metrics, pair, system)

    # Adjust verdict if gates failed
    final_verdict = score_result["verdict"]
    if not gate_result["all_passed"]:
        if final_verdict == "EXECUTE":
            final_verdict = "DEVELOPING"  # Downgrade if gates failed

    return {
        "pair": pair,
        "system": system,
        "gates": gate_result,
        "scoring": score_result,
        "final_verdict": final_verdict,
        "final_score": score_result["composite_score"],
        "bias": score_result["bias"],
    }
