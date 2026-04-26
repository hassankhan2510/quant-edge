"""
Quant Edge — Monday Swing Setup Pipeline
Weekly setup analysis for Monday open.
Fresh weekly-level analysis to start the week.
Runs at 21:30 UTC Sunday.
"""
from datetime import datetime, timezone
from src.data_fetcher import DataFetcher
from src.macro_engine import calculate_macro_context, format_macro_summary
from src.indicators import calculate_all_indicators
from src.scoring_engine import score_pair_full
from src.ai_analyst import AIAnalyst
from src.supabase_store import SupabaseStore
from src.telegram_notifier import TelegramNotifier
from src.pair_profiles import get_profile, get_pairs_for_system
from src import config


def run(dry_run: bool = False):
    """Run Monday swing setup analysis."""
    print("\n" + "=" * 60)
    print("📈 QUANT DESK — MONDAY SWING SETUP")
    print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    fetcher = DataFetcher()
    ai = AIAnalyst()
    store = SupabaseStore()
    notifier = TelegramNotifier()

    # 1. Fetch macro context
    print("\n[1/3] Fetching macro data...")
    macro_data = fetcher.fetch_macro_data()
    macro_context = calculate_macro_context(macro_data)
    macro_summary = format_macro_summary(macro_context)
    print(macro_summary)

    # 2. Analyze each swing pair on weekly + daily
    print("\n[2/3] Analyzing swing pairs (weekly setup)...")
    current_hour = datetime.now(timezone.utc).hour
    pair_analyses = []
    swing_pairs = get_pairs_for_system("swing")

    for pair in swing_pairs:
        print(f"\n--- {pair} (Weekly Setup) ---")
        profile = get_profile(pair)

        try:
            # Fetch multi-TF data for swing
            tf_data = fetcher.fetch_multi_tf(pair, "swing")

            # Calculate indicators
            params = profile["indicator_params"]

            # Weekly (HTF) for big picture
            weekly_df = tf_data["htf"]
            weekly_metrics = calculate_all_indicators(weekly_df, params, current_hour)

            # Daily (primary)
            daily_df = tf_data["primary"]
            daily_metrics = calculate_all_indicators(daily_df, params, current_hour)

            # Score on daily
            score_result = score_pair_full(daily_metrics, pair, "swing")

            print(f"  Score: {score_result['final_score']}/100 | "
                  f"Verdict: {score_result['final_verdict']} | "
                  f"Bias: {score_result['bias']}")

            # AI Analysis — fresh weekly setup
            ai_analysis = ai.analyze_pre_session(
                pair, "swing", daily_metrics, score_result, macro_context
            )
            print(f"  AI: {ai_analysis[:100]}...")

            # Store as Monday's swing data (with weekly context)
            if not dry_run:
                store.store_swing_daily(
                    pair=pair,
                    daily_metrics=daily_metrics,
                    four_hour_metrics={},
                    weekly_context=weekly_metrics,
                    composite_score=score_result["final_score"],
                    macro_context=macro_context,
                    ai_analysis=ai_analysis,
                    ai_verdict=score_result["final_verdict"],
                    price_at_analysis=daily_metrics["current_price"],
                )

            pair_analyses.append({
                "pair": pair,
                "score": score_result["final_score"],
                "verdict": score_result["final_verdict"],
                "bias": score_result["bias"],
                "ai_analysis": ai_analysis,
                "metrics_summary": {
                    "atr_percent": daily_metrics.get("atr_percent"),
                    "adx": daily_metrics.get("adx"),
                    "rsi": daily_metrics.get("rsi"),
                    "zscore": daily_metrics.get("zscore"),
                    "volume_ratio": daily_metrics.get("volume_ratio"),
                    "bb_bandwidth": daily_metrics.get("bb_bandwidth"),
                    "macd_hist_slope": daily_metrics.get("macd_hist_slope"),
                },
            })

        except Exception as e:
            print(f"  ✗ Error analyzing {pair}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 3. Send Telegram
    print("\n[3/3] Sending Monday swing setup...")
    if not dry_run and pair_analyses:
        notifier.send_pre_session_briefing(
            "Monday Swing Setup", macro_summary, pair_analyses
        )

    print("\n✅ Monday swing setup complete!")
    return pair_analyses
