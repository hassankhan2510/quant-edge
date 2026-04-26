"""
Quant Edge — Supabase Session Memory Store
Handles all database operations for session memory, reviews, and cleanup.
"""
import json
from datetime import datetime, date, timezone
from typing import Optional
from src import config

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


class SupabaseStore:
    """Session memory CRUD with auto-cleanup."""

    def __init__(self):
        self.enabled = bool(config.SUPABASE_URL and config.SUPABASE_KEY and SUPABASE_AVAILABLE)
        self.client: Optional[Client] = None

        if self.enabled:
            try:
                self.client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                print("  ✓ Supabase connected")
            except Exception as e:
                print(f"  ✗ Supabase connection failed: {e}")
                self.enabled = False
        else:
            print("  ⚠ Supabase disabled (missing URL/KEY or library not installed)")

    # ═══════════════════════════════════════════════════════════
    # DAY SESSION ANALYSIS
    # ═══════════════════════════════════════════════════════════

    def store_session_analysis(self, pair: str, session: str,
                                 metrics: dict, composite_score: float,
                                 macro_context: dict,
                                 ai_analysis: str, ai_verdict: str,
                                 ai_conditions: str,
                                 price_at_analysis: float) -> bool:
        """Store a session's analysis (London or NY) for later retrieval."""
        if not self.enabled:
            return False

        today = date.today().isoformat()

        data = {
            "pair": pair,
            "session": session,
            "analysis_date": today,
            "metrics": json.dumps(metrics, default=str),
            "composite_score": composite_score,
            "dxy_value": macro_context.get("dxy", {}).get("value"),
            "dxy_trend": macro_context.get("dxy", {}).get("bias", "unknown"),
            "macro_bias": macro_context.get("macro_regime", "neutral"),
            "ai_analysis": ai_analysis,
            "ai_verdict": ai_verdict,
            "ai_conditions": ai_conditions or "",
            "price_at_analysis": price_at_analysis,
        }

        try:
            # Upsert — update if already exists for this pair+session+date
            self.client.table("day_session_analysis").upsert(
                data,
                on_conflict="pair,session,analysis_date"
            ).execute()
            print(f"  ✓ Stored {session} analysis for {pair}")
            return True
        except Exception as e:
            print(f"  ✗ Failed to store {session} analysis for {pair}: {e}")
            return False

    def get_previous_session(self, pair: str, session: str,
                               analysis_date: str = None) -> Optional[dict]:
        """Retrieve a previous session's analysis (e.g., London data during NY)."""
        if not self.enabled:
            return None

        today = analysis_date or date.today().isoformat()

        try:
            result = self.client.table("day_session_analysis").select("*").eq(
                "pair", pair
            ).eq(
                "session", session
            ).eq(
                "analysis_date", today
            ).execute()

            if result.data and len(result.data) > 0:
                row = result.data[0]
                # Parse metrics JSON back
                if isinstance(row.get("metrics"), str):
                    row["metrics"] = json.loads(row["metrics"])
                return row
            return None
        except Exception as e:
            print(f"  ✗ Failed to get {session} analysis for {pair}: {e}")
            return None

    def get_all_sessions_today(self, pair: str) -> list:
        """Get all session analyses for a pair today (for EOD review)."""
        if not self.enabled:
            return []

        today = date.today().isoformat()

        try:
            result = self.client.table("day_session_analysis").select("*").eq(
                "pair", pair
            ).eq(
                "analysis_date", today
            ).order("created_at").execute()

            rows = result.data or []
            for row in rows:
                if isinstance(row.get("metrics"), str):
                    row["metrics"] = json.loads(row["metrics"])
            return rows
        except Exception as e:
            print(f"  ✗ Failed to get today's sessions for {pair}: {e}")
            return []

    # ═══════════════════════════════════════════════════════════
    # DAY REVIEW
    # ═══════════════════════════════════════════════════════════

    def store_day_review(self, pair: str, review_data: dict) -> bool:
        """Store end-of-day review."""
        if not self.enabled:
            return False

        today = date.today().isoformat()

        data = {
            "review_date": today,
            "pair": pair,
            "london_prediction": review_data.get("london_prediction", ""),
            "london_actual_move": review_data.get("london_actual_move", 0),
            "london_was_correct": review_data.get("london_was_correct", False),
            "ny_prediction": review_data.get("ny_prediction", ""),
            "ny_actual_move": review_data.get("ny_actual_move", 0),
            "ny_was_correct": review_data.get("ny_was_correct", False),
            "ai_self_review": review_data.get("ai_self_review", ""),
            "ai_suggested_adjustments": review_data.get("ai_suggested_adjustments", ""),
            "overall_accuracy_pct": review_data.get("overall_accuracy_pct", 0),
        }

        try:
            self.client.table("day_review").upsert(
                data,
                on_conflict="pair,review_date"
            ).execute()
            print(f"  ✓ Stored day review for {pair}")
            return True
        except Exception as e:
            print(f"  ✗ Failed to store day review for {pair}: {e}")
            return False

    def cleanup_day_data(self, analysis_date: str = None) -> bool:
        """Delete all day session analysis for a given date (after review is saved)."""
        if not self.enabled:
            return False

        target_date = analysis_date or date.today().isoformat()

        try:
            self.client.table("day_session_analysis").delete().eq(
                "analysis_date", target_date
            ).execute()
            print(f"  ✓ Cleaned up day data for {target_date}")
            return True
        except Exception as e:
            print(f"  ✗ Failed to cleanup day data: {e}")
            return False

    # ═══════════════════════════════════════════════════════════
    # SWING DAILY ANALYSIS
    # ═══════════════════════════════════════════════════════════

    def store_swing_daily(self, pair: str,
                           daily_metrics: dict, four_hour_metrics: dict,
                           weekly_context: dict,
                           composite_score: float,
                           macro_context: dict,
                           ai_analysis: str, ai_verdict: str,
                           price_at_analysis: float) -> bool:
        """Store daily swing analysis (accumulates through the week)."""
        if not self.enabled:
            return False

        today = date.today()
        iso_cal = today.isocalendar()

        data = {
            "pair": pair,
            "analysis_date": today.isoformat(),
            "week_number": iso_cal[1],
            "year": iso_cal[0],
            "day_of_week": iso_cal[2],  # 1=Mon, 7=Sun
            "daily_metrics": json.dumps(daily_metrics, default=str),
            "four_hour_metrics": json.dumps(four_hour_metrics, default=str),
            "weekly_context": json.dumps(weekly_context, default=str) if weekly_context else None,
            "composite_score": composite_score,
            "dxy_value": macro_context.get("dxy", {}).get("value"),
            "dxy_weekly_trend": macro_context.get("dxy", {}).get("bias", "unknown"),
            "macro_regime": macro_context.get("macro_regime", "neutral"),
            "ai_analysis": ai_analysis,
            "ai_verdict": ai_verdict,
            "price_at_analysis": price_at_analysis,
        }

        try:
            self.client.table("swing_daily_analysis").upsert(
                data,
                on_conflict="pair,analysis_date"
            ).execute()
            print(f"  ✓ Stored swing daily for {pair} (week {iso_cal[1]}, day {iso_cal[2]})")
            return True
        except Exception as e:
            print(f"  ✗ Failed to store swing daily for {pair}: {e}")
            return False

    def get_week_context(self, pair: str, week_number: int = None,
                          year: int = None) -> list:
        """Get all daily swing analyses for a week (for Friday report)."""
        if not self.enabled:
            return []

        today = date.today()
        iso_cal = today.isocalendar()
        wk = week_number or iso_cal[1]
        yr = year or iso_cal[0]

        try:
            result = self.client.table("swing_daily_analysis").select("*").eq(
                "pair", pair
            ).eq(
                "week_number", wk
            ).eq(
                "year", yr
            ).order("day_of_week").execute()

            rows = result.data or []
            for row in rows:
                for json_field in ["daily_metrics", "four_hour_metrics", "weekly_context"]:
                    if isinstance(row.get(json_field), str):
                        row[json_field] = json.loads(row[json_field])
            return rows
        except Exception as e:
            print(f"  ✗ Failed to get week context for {pair}: {e}")
            return []

    def get_previous_swing_days(self, pair: str) -> list:
        """Get all previous days of swing analysis this week (for context-aware daily)."""
        return self.get_week_context(pair)

    # ═══════════════════════════════════════════════════════════
    # SWING WEEKLY REPORT
    # ═══════════════════════════════════════════════════════════

    def store_weekly_report(self, pair: str, report_data: dict) -> bool:
        """Store the Friday weekly swing report."""
        if not self.enabled:
            return False

        today = date.today()
        iso_cal = today.isocalendar()

        data = {
            "pair": pair,
            "week_number": iso_cal[1],
            "year": iso_cal[0],
            "week_open_price": report_data.get("week_open_price", 0),
            "week_close_price": report_data.get("week_close_price", 0),
            "week_high": report_data.get("week_high", 0),
            "week_low": report_data.get("week_low", 0),
            "total_move_pct": report_data.get("total_move_pct", 0),
            "ai_weekly_summary": report_data.get("ai_weekly_summary", ""),
            "predictions_correct": report_data.get("predictions_correct", 0),
            "predictions_total": report_data.get("predictions_total", 0),
            "accuracy_pct": report_data.get("accuracy_pct", 0),
            "ai_lessons": report_data.get("ai_lessons", ""),
            "ai_next_week_outlook": report_data.get("ai_next_week_outlook", ""),
        }

        try:
            self.client.table("swing_weekly_report").upsert(
                data,
                on_conflict="pair,week_number,year"
            ).execute()
            print(f"  ✓ Stored weekly report for {pair}")
            return True
        except Exception as e:
            print(f"  ✗ Failed to store weekly report for {pair}: {e}")
            return False

    def cleanup_week_data(self, week_number: int = None, year: int = None) -> bool:
        """Delete all swing daily data for a week (after weekly report is saved)."""
        if not self.enabled:
            return False

        today = date.today()
        iso_cal = today.isocalendar()
        wk = week_number or iso_cal[1]
        yr = year or iso_cal[0]

        try:
            self.client.table("swing_daily_analysis").delete().eq(
                "week_number", wk
            ).eq(
                "year", yr
            ).execute()
            print(f"  ✓ Cleaned up swing data for week {wk}/{yr}")
        except Exception as e:
            print(f"  ✗ Failed to cleanup swing data: {e}")
            return False

    # ═══════════════════════════════════════════════════════════
    # PSX SPECIFIC CLEANUP
    # ═══════════════════════════════════════════════════════════
    
    def cleanup_psx_data(self) -> bool:
        """Delete all PSX session analysis data (after weekly PSX report is complete)."""
        if not self.enabled:
            return False

        try:
            self.client.table("day_session_analysis").delete().like(
                "pair", "PSX_%"
            ).execute()
            print("  ✓ Cleaned up all PSX session data from database")
            return True
        except Exception as e:
            print(f"  ✗ Failed to cleanup PSX data: {e}")
            return False
