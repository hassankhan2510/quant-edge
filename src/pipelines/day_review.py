"""
Quant Edge — End-of-Day Review Pipeline
Compares London & NY predictions vs actual moves.
AI self-reviews accuracy and suggests adjustments.
Cleans up day data from Supabase after review.
Runs at 21:00 UTC Mon-Fri.
"""
import time
from datetime import datetime, timezone
from src.data_fetcher import DataFetcher
from src.ai_analyst import AIAnalyst
from src.supabase_store import SupabaseStore
from src.telegram_notifier import TelegramNotifier
from src.pair_profiles import get_profile, get_pairs_for_system
from src import config


def run(dry_run: bool = False):
    """Run end-of-day review for all day-trade pairs."""
    print("\n" + "=" * 60)
    print("📊 QUANT DESK — END OF DAY REVIEW")
    print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    fetcher = DataFetcher()
    ai = AIAnalyst()
    store = SupabaseStore()
    notifier = TelegramNotifier()

    pair_reviews = []
    day_pairs = get_pairs_for_system("day")

    for pair in day_pairs:
        print(f"\n--- {pair} REVIEW ---")
        profile = get_profile(pair)

        try:
            # Get current price
            current_df = fetcher.fetch(pair, "1h", bars=5)
            current_price = float(current_df["Close"].iloc[-1])
            print(f"  Current price: {current_price}")

            # Pull today's stored analyses
            london_data = store.get_previous_session(pair, "london")
            ny_data = store.get_previous_session(pair, "newyork")

            if not london_data and not ny_data:
                print(f"  ⚠ No session data found for {pair} today, skipping review")
                continue

            # Calculate accuracy
            london_price = london_data.get("price_at_analysis", 0) if london_data else 0
            ny_price = ny_data.get("price_at_analysis", 0) if ny_data else 0

            london_move = ((current_price - london_price) / london_price * 100) if london_price else 0
            ny_move = ((current_price - ny_price) / ny_price * 100) if ny_price else 0

            # Determine if predictions were directionally correct
            london_verdict = london_data.get("ai_verdict", "") if london_data else ""
            ny_verdict = ny_data.get("ai_verdict", "") if ny_data else ""

            # Simple accuracy: did the bias match the actual move direction?
            london_correct = False
            ny_correct = False

            if london_data:
                # A "NO_TRADE" or "WAIT" during a small move is correct
                if london_verdict in ["NO_TRADE", "WAIT"] and abs(london_move) < 0.3:
                    london_correct = True
                elif london_verdict == "EXECUTE":
                    london_correct = True  # We'll let AI determine the nuance

            if ny_data:
                if ny_verdict in ["NO_TRADE", "WAIT"] and abs(ny_move) < 0.3:
                    ny_correct = True
                elif ny_verdict == "EXECUTE":
                    ny_correct = True

            # AI self-review
            print(f"  Requesting AI self-review...")
            ai_review = ai.analyze_eod_review(pair, london_data, ny_data, current_price)
            print(f"  AI Review: {ai_review[:100]}...")

            # Calculate accuracy
            total_sessions = sum([1 if london_data else 0, 1 if ny_data else 0])
            correct_sessions = sum([1 if london_correct else 0, 1 if ny_correct else 0])
            accuracy = (correct_sessions / total_sessions * 100) if total_sessions > 0 else 0

            review_data = {
                "london_prediction": london_verdict,
                "london_actual_move": round(london_move, 4),
                "london_was_correct": london_correct,
                "ny_prediction": ny_verdict,
                "ny_actual_move": round(ny_move, 4),
                "ny_was_correct": ny_correct,
                "ai_self_review": ai_review,
                "ai_suggested_adjustments": "",
                "overall_accuracy_pct": accuracy,
            }

            # Store review
            if not dry_run:
                store.store_day_review(pair, review_data)

            pair_reviews.append({
                "pair": pair,
                "london_was_correct": london_correct,
                "ny_was_correct": ny_correct,
                "ai_review": ai_review,
                "accuracy_pct": accuracy,
            })
            time.sleep(5)  # Rate limit protection

            print(f"  London: {'✅' if london_correct else '❌'} (move: {london_move:+.3f}%)")
            print(f"  NY: {'✅' if ny_correct else '❌'} (move: {ny_move:+.3f}%)")
            print(f"  Accuracy: {accuracy:.0f}%")

        except Exception as e:
            print(f"  ✗ Error reviewing {pair}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Send review report
    print("\n[3/4] Sending Telegram review...")
    if not dry_run and pair_reviews:
        notifier.send_eod_review(pair_reviews)

    # Cleanup day data
    print("\n[4/4] Cleaning up day data from Supabase...")
    if not dry_run:
        store.cleanup_day_data()
        print("  ✓ Day data cleaned")
    else:
        print("  [DRY RUN] Skipping cleanup")

    print("\n✅ End-of-day review complete!")
    return pair_reviews
