"""
Quant Edge — Pre-London Pipeline
Fresh session analysis. No previous context. Start of day.
Runs at 06:30 UTC Mon-Fri.
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
    """Run pre-London analysis for all day-trade pairs."""
    print("\n" + "=" * 60)
    print("📋 QUANT DESK — PRE-LONDON ANALYSIS")
    print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    fetcher = DataFetcher()
    ai = AIAnalyst()
    store = SupabaseStore()
    notifier = TelegramNotifier()

    # 1. Fetch macro context
    print("\n[1/4] Fetching macro data...")
    macro_data = fetcher.fetch_macro_data()
    macro_context = calculate_macro_context(macro_data)
    macro_summary = format_macro_summary(macro_context)
    print(macro_summary)

    # 2. Analyze each pair
    print("\n[2/4] Analyzing pairs...")
    current_hour = datetime.now(timezone.utc).hour
    pair_analyses = []
    day_pairs = get_pairs_for_system("day")

    for pair in day_pairs:
        print(f"\n--- {pair} ---")
        profile = get_profile(pair)

        try:
            # Fetch multi-TF data
            tf_data = fetcher.fetch_multi_tf(pair, "day")

            # Calculate indicators on primary timeframe
            params = profile["indicator_params"]
            primary_df = tf_data["primary"]
            metrics = calculate_all_indicators(primary_df, params, current_hour)

            # Also get HTF metrics for context
            htf_df = tf_data["htf"]
            htf_metrics = calculate_all_indicators(htf_df, params, current_hour)

            # Score the setup
            score_result = score_pair_full(metrics, pair, "day", current_hour)

            print(f"  Score: {score_result['final_score']}/100 | "
                  f"Verdict: {score_result['final_verdict']} | "
                  f"Bias: {score_result['bias']}")

            # AI Analysis (pre-session — no previous context)
            print(f"  Requesting AI analysis...")
            ai_analysis = ai.analyze_pre_session(
                pair, "day", metrics, score_result, macro_context
            )
            print(f"  AI: {ai_analysis[:100]}...")

            # Store in Supabase
            if not dry_run:
                store.store_session_analysis(
                    pair=pair,
                    session="london",
                    metrics=metrics,
                    composite_score=score_result["final_score"],
                    macro_context=macro_context,
                    ai_analysis=ai_analysis,
                    ai_verdict=score_result["final_verdict"],
                    ai_conditions="",
                    price_at_analysis=metrics["current_price"],
                )

            pair_analyses.append({
                "pair": pair,
                "score": score_result["final_score"],
                "verdict": score_result["final_verdict"],
                "bias": score_result["bias"],
                "ai_analysis": ai_analysis,
                "metrics_summary": {
                    "atr_percent": metrics.get("atr_percent"),
                    "adx": metrics.get("adx"),
                    "rsi": metrics.get("rsi"),
                    "zscore": metrics.get("zscore"),
                    "volume_ratio": metrics.get("volume_ratio"),
                    "bb_bandwidth": metrics.get("bb_bandwidth"),
                    "macd_hist_slope": metrics.get("macd_hist_slope"),
                },
            })

        except Exception as e:
            print(f"  ✗ Error analyzing {pair}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 3. Send Telegram briefing
    print("\n[3/4] Sending Telegram briefing...")
    if not dry_run and pair_analyses:
        notifier.send_pre_session_briefing(
            "Pre-London", macro_summary, pair_analyses
        )
    elif dry_run:
        print("  [DRY RUN] Skipping Telegram")

    # 4. Done
    print("\n[4/4] Pre-London analysis complete!")
    print(f"  Pairs analyzed: {len(pair_analyses)}")
    for pa in pair_analyses:
        print(f"  {pa['pair']}: {pa['score']}/100 → {pa['verdict']}")

    return pair_analyses
