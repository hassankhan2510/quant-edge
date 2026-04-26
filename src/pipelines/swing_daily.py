"""
Quant Edge — Daily Swing Update Pipeline
Accumulates daily swing analysis in Supabase throughout the week.
AI gets context from all previous days this week.
Runs at 20:00 UTC Mon-Fri.
"""
import time
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
    """Run daily swing analysis with weekly context accumulation."""
    print("\n" + "=" * 60)
    print("📈 QUANT DESK — DAILY SWING UPDATE")
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

    # 2. Analyze each swing pair
    print("\n[2/3] Analyzing swing pairs...")
    current_hour = datetime.now(timezone.utc).hour
    pair_analyses = []
    swing_pairs = get_pairs_for_system("swing")

    for pair in swing_pairs:
        print(f"\n--- {pair} (Swing) ---")
        profile = get_profile(pair)

        try:
            # Fetch multi-TF data for swing
            tf_data = fetcher.fetch_multi_tf(pair, "swing")

            # Calculate indicators on daily (primary) and 4H (ltf)
            params = profile["indicator_params"]
            daily_df = tf_data["primary"]
            daily_metrics = calculate_all_indicators(daily_df, params, current_hour)

            four_h_df = tf_data["ltf"]
            four_h_metrics = calculate_all_indicators(four_h_df, params, current_hour)

            # Score the swing setup
            score_result = score_pair_full(daily_metrics, pair, "swing")

            print(f"  Score: {score_result['final_score']}/100 | "
                  f"Verdict: {score_result['final_verdict']} | "
                  f"Bias: {score_result['bias']}")

            # Get previous swing days this week for context
            prev_days = store.get_previous_swing_days(pair)

            if prev_days:
                print(f"  ✓ {len(prev_days)} previous days of context this week")
                # Build context from previous days
                previous_context = {
                    "session": f"previous {len(prev_days)} swing days",
                    "ai_analysis": "\n".join([
                        f"Day {d.get('day_of_week')}: Score={d.get('composite_score')}/100, "
                        f"Verdict={d.get('ai_verdict')}"
                        for d in prev_days
                    ]),
                    "price_at_analysis": prev_days[-1].get("price_at_analysis", 0),
                    "composite_score": prev_days[-1].get("composite_score", 0),
                    "ai_verdict": prev_days[-1].get("ai_verdict", "N/A"),
                }
                ai_analysis = ai.analyze_with_context(
                    pair, "swing",
                    current_metrics=daily_metrics,
                    score_result=score_result,
                    macro_context=macro_context,
                    previous_analysis=previous_context,
                )
            else:
                print(f"  ⚠ No previous context this week — fresh analysis")
                ai_analysis = ai.analyze_pre_session(
                    pair, "swing", daily_metrics, score_result, macro_context
                )

            print(f"  AI: {ai_analysis[:100]}...")

            # Store in Supabase
            if not dry_run:
                store.store_swing_daily(
                    pair=pair,
                    daily_metrics=daily_metrics,
                    four_hour_metrics=four_h_metrics,
                    weekly_context=None,
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
            time.sleep(5)  # Rate limit protection

        except Exception as e:
            print(f"  ✗ Error analyzing {pair}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 3. Send Telegram update
    print("\n[3/3] Sending Telegram swing update...")
    if not dry_run and pair_analyses:
        notifier.send_pre_session_briefing(
            "Daily Swing Update", macro_summary, pair_analyses
        )

    print("\n✅ Daily swing update complete!")
    return pair_analyses
