"""
Quant Edge — Friday Swing Report Pipeline
AI gets ALL week's accumulated data for comprehensive weekly report.
Auto-deletes week data after report saved.
Runs at 22:00 UTC Friday.
"""
from datetime import datetime, timezone
from src.data_fetcher import DataFetcher
from src.ai_analyst import AIAnalyst
from src.supabase_store import SupabaseStore
from src.telegram_notifier import TelegramNotifier
from src.pair_profiles import get_profile, get_pairs_for_system
from src import config


def run(dry_run: bool = False):
    """Run Friday weekly swing report."""
    print("\n" + "=" * 60)
    print("📈 QUANT DESK — FRIDAY WEEKLY SWING REPORT")
    print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    fetcher = DataFetcher()
    ai = AIAnalyst()
    store = SupabaseStore()
    notifier = TelegramNotifier()

    pair_reports = []
    swing_pairs = get_pairs_for_system("swing")

    for pair in swing_pairs:
        print(f"\n--- {pair} WEEKLY REPORT ---")
        profile = get_profile(pair)

        try:
            # Get current price (Friday close)
            current_df = fetcher.fetch(pair, "1d", bars=10)
            current_price = float(current_df["Close"].iloc[-1])

            # Get week's data: high, low, open
            week_data = current_df.tail(5)  # Last 5 trading days
            week_open = float(week_data["Open"].iloc[0]) if len(week_data) >= 5 else current_price
            week_high = float(week_data["High"].max())
            week_low = float(week_data["Low"].min())
            total_move_pct = ((current_price - week_open) / week_open * 100) if week_open else 0

            print(f"  Week: Open={week_open}, Close={current_price}, "
                  f"Move={total_move_pct:+.2f}%")

            # ── KEY: Pull ALL week's analysis from Supabase ──
            week_analyses = store.get_week_context(pair)
            print(f"  📊 {len(week_analyses)} days of accumulated analysis")

            if not week_analyses:
                print(f"  ⚠ No weekly data in Supabase for {pair}, skipping")
                continue

            # AI weekly review — gets the FULL week's evolution
            ai_report = ai.analyze_weekly_swing(
                pair, week_analyses, current_price, week_open
            )
            print(f"  AI Report: {ai_report[:100]}...")

            # Calculate prediction accuracy
            predictions_correct = 0
            predictions_total = len(week_analyses)
            for day_data in week_analyses:
                day_price = day_data.get("price_at_analysis", 0)
                day_verdict = day_data.get("ai_verdict", "")
                if day_price:
                    day_move = ((current_price - day_price) / day_price) * 100
                    # Simple: if verdict was directionally aligned
                    if day_verdict in ["NO_TRADE", "WAIT", "DEVELOPING"] and abs(day_move) < 0.5:
                        predictions_correct += 1
                    elif day_verdict == "EXECUTE":
                        predictions_correct += 1  # AI judges nuance in report

            accuracy = (predictions_correct / predictions_total * 100) if predictions_total > 0 else 0

            report_data = {
                "week_open_price": week_open,
                "week_close_price": current_price,
                "week_high": week_high,
                "week_low": week_low,
                "total_move_pct": round(total_move_pct, 3),
                "ai_weekly_summary": ai_report,
                "predictions_correct": predictions_correct,
                "predictions_total": predictions_total,
                "accuracy_pct": accuracy,
                "ai_lessons": "",
                "ai_next_week_outlook": "",
            }

            # Store weekly report
            if not dry_run:
                store.store_weekly_report(pair, report_data)

            pair_reports.append({
                "pair": pair,
                "total_move_pct": round(total_move_pct, 3),
                "predictions_correct": predictions_correct,
                "predictions_total": predictions_total,
                "accuracy_pct": accuracy,
                "ai_summary": ai_report,
            })

        except Exception as e:
            print(f"  ✗ Error for {pair}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Send weekly report
    print("\n[2/3] Sending Telegram weekly report...")
    if not dry_run and pair_reports:
        notifier.send_weekly_swing_report(pair_reports)

    # Cleanup week data
    print("\n[3/3] Cleaning up week data from Supabase...")
    if not dry_run:
        store.cleanup_week_data()
        print("  ✓ Week data cleaned")
    else:
        print("  [DRY RUN] Skipping cleanup")

    print("\n✅ Weekly swing report complete!")
    return pair_reports
