"""
Quant Edge — CLI Entry Point
Usage:
    python -m src.run --pipeline london
    python -m src.run --pipeline newyork
    python -m src.run --pipeline review
    python -m src.run --pipeline swing-daily
    python -m src.run --pipeline swing-monday
    python -m src.run --pipeline swing-friday
    python -m src.run --pipeline london --dry-run
"""
import argparse
import sys
import os

# Fix Windows console encoding for emoji/unicode output
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Quant Edge — Intelligent Quantitative Trading Analyst"
    )
    parser.add_argument(
        "--pipeline",
        required=True,
        choices=[
            "london", "newyork", "review",
            "swing-daily", "swing-monday", "swing-friday",
            "psx-daily", "psx-weekly"
        ],
        help="Which pipeline to run"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run without sending Telegram messages or writing to Supabase"
    )

    args = parser.parse_args()

    print(f"\n🔧 Quant Edge — Running pipeline: {args.pipeline}")
    if args.dry_run:
        print("  ⚠ DRY RUN MODE — no Telegram, no Supabase writes")

    try:
        if args.pipeline == "london":
            from src.pipelines.day_london import run
            run(dry_run=args.dry_run)

        elif args.pipeline == "newyork":
            from src.pipelines.day_newyork import run
            run(dry_run=args.dry_run)

        elif args.pipeline == "review":
            from src.pipelines.day_review import run
            run(dry_run=args.dry_run)

        elif args.pipeline == "swing-daily":
            from src.pipelines.swing_daily import run
            run(dry_run=args.dry_run)

        elif args.pipeline == "swing-monday":
            from src.pipelines.swing_monday import run
            run(dry_run=args.dry_run)

        elif args.pipeline == "swing-friday":
            from src.pipelines.swing_friday import run
            run(dry_run=args.dry_run)

        elif args.pipeline == "psx-daily":
            from src.psx.pipelines import run_psx_pipeline
            run_psx_pipeline("psx-daily", dry_run=args.dry_run)

        elif args.pipeline == "psx-weekly":
            from src.psx.pipelines import run_psx_pipeline
            run_psx_pipeline("psx-weekly", dry_run=args.dry_run)

        else:
            print(f"Unknown pipeline: {args.pipeline}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n✅ Pipeline finished successfully.")


if __name__ == "__main__":
    main()
