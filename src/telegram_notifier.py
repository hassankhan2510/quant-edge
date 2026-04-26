"""
Quant Edge — Telegram Notifier
Sends formatted analyst briefings (not signal cards) to Telegram.
"""
import requests
import json
from src import config
from src.pair_profiles import get_profile


class TelegramNotifier:
    """Send formatted analyst briefings to Telegram."""

    BASE_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)

        if not self.enabled:
            print("  ⚠ Telegram disabled (missing BOT_TOKEN or CHAT_ID)")

    def _send(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to Telegram."""
        if not self.enabled:
            print("  [TELEGRAM DISABLED] Would send:")
            print(text[:500])
            return False

        url = self.BASE_URL.format(token=self.token)

        # Telegram has a 4096 character limit, split if needed
        chunks = self._split_message(text, 4090)

        for chunk in chunks:
            try:
                resp = requests.post(url, json={
                    "chat_id": self.chat_id,
                    "text": chunk,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                }, timeout=15)

                if resp.status_code != 200:
                    print(f"  ✗ Telegram error: {resp.status_code} — {resp.text[:200]}")
                    # Retry without parse_mode if HTML failed
                    resp2 = requests.post(url, json={
                        "chat_id": self.chat_id,
                        "text": chunk,
                        "disable_web_page_preview": True,
                    }, timeout=15)
                    if resp2.status_code != 200:
                        return False
            except Exception as e:
                print(f"  ✗ Telegram send failed: {e}")
                return False

        return True

    def _split_message(self, text: str, max_len: int = 4090) -> list:
        """Split long messages into chunks for Telegram's 4096 char limit."""
        if len(text) <= max_len:
            return [text]

        chunks = []
        lines = text.split("\n")
        current = ""

        for line in lines:
            if len(current) + len(line) + 1 > max_len:
                if current:
                    chunks.append(current)
                current = line
            else:
                current = current + "\n" + line if current else line

        if current:
            chunks.append(current)

        return chunks

    # ═══════════════════════════════════════════════════════════
    # PRE-SESSION BRIEFING (London or Monday Swing)
    # ═══════════════════════════════════════════════════════════

    def send_pre_session_briefing(self, session_name: str,
                                    macro_summary: str,
                                    pair_analyses: list) -> bool:
        """
        Send pre-session briefing with macro context + per-pair analysis.

        pair_analyses: list of dicts with keys:
            pair, score, verdict, bias, ai_analysis, metrics_summary
        """
        header = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        header += f"📋 QUANT DESK — {session_name.upper()} BRIEFING\n"
        header += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        header += macro_summary + "\n"

        body = ""
        for analysis in pair_analyses:
            profile = get_profile(analysis["pair"])
            emoji = profile.get("emoji", "📊")

            body += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            body += f"{emoji} {analysis['pair']} — {analysis['verdict']} "
            body += f"(Score: {analysis['score']}/100)\n\n"

            # Key metrics line
            ms = analysis.get("metrics_summary", {})
            if ms:
                body += f"ATR%: {ms.get('atr_percent', 'N/A')} | "
                body += f"ADX: {ms.get('adx', 'N/A')} | "
                body += f"RSI: {ms.get('rsi', 'N/A')}\n"
                body += f"Z-Score: {ms.get('zscore', 'N/A')} | "
                body += f"Vol Ratio: {ms.get('volume_ratio', 'N/A')}×\n\n"

            body += analysis.get("ai_analysis", "No analysis available")
            body += "\n"

        footer = f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        footer += f"🤖 Quant Edge | Numbers Only\n"

        full_message = header + body + footer
        return self._send(full_message, parse_mode=None)

    # ═══════════════════════════════════════════════════════════
    # CONTEXTUAL BRIEFING (NY with London context)
    # ═══════════════════════════════════════════════════════════

    def send_contextual_briefing(self, session_name: str,
                                   macro_summary: str,
                                   pair_analyses: list) -> bool:
        """
        Send context-aware briefing (NY with London reference).
        Same format as pre-session but with context note.
        """
        header = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        header += f"📋 QUANT DESK — {session_name.upper()} BRIEFING\n"
        header += f"🔄 (Includes {self._get_prev_session(session_name)} session context)\n"
        header += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        header += macro_summary + "\n"

        body = ""
        for analysis in pair_analyses:
            profile = get_profile(analysis["pair"])
            emoji = profile.get("emoji", "📊")

            body += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            body += f"{emoji} {analysis['pair']} — {analysis['verdict']} "
            body += f"(Score: {analysis['score']}/100)\n\n"

            ms = analysis.get("metrics_summary", {})
            if ms:
                body += f"ATR%: {ms.get('atr_percent', 'N/A')} | "
                body += f"ADX: {ms.get('adx', 'N/A')} | "
                body += f"RSI: {ms.get('rsi', 'N/A')}\n"
                body += f"Z-Score: {ms.get('zscore', 'N/A')} | "
                body += f"Vol Ratio: {ms.get('volume_ratio', 'N/A')}×\n\n"

            body += analysis.get("ai_analysis", "No analysis available")
            body += "\n"

        footer = f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        footer += f"🤖 Quant Edge | Session Memory Active\n"

        full_message = header + body + footer
        return self._send(full_message, parse_mode=None)

    # ═══════════════════════════════════════════════════════════
    # END-OF-DAY REVIEW
    # ═══════════════════════════════════════════════════════════

    def send_eod_review(self, pair_reviews: list) -> bool:
        """
        Send end-of-day review report.

        pair_reviews: list of dicts with keys:
            pair, london_was_correct, ny_was_correct, ai_review, accuracy_pct
        """
        header = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        header += f"📊 QUANT DESK — END OF DAY REVIEW\n"
        header += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        body = ""
        for review in pair_reviews:
            profile = get_profile(review["pair"])
            emoji = profile.get("emoji", "📊")
            l_icon = "✅" if review.get("london_was_correct") else "❌"
            n_icon = "✅" if review.get("ny_was_correct") else "❌"

            body += f"{emoji} {review['pair']}\n"
            body += f"  London: {l_icon} | NY: {n_icon}\n"
            body += f"  Accuracy: {review.get('accuracy_pct', 0):.0f}%\n\n"
            body += review.get("ai_review", "No review available")
            body += "\n\n"

        footer = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        footer += f"🗑️ Day data cleaned from database.\n"
        footer += f"🤖 Quant Edge | Self-Improving\n"

        full_message = header + body + footer
        return self._send(full_message, parse_mode=None)

    # ═══════════════════════════════════════════════════════════
    # WEEKLY SWING REPORT
    # ═══════════════════════════════════════════════════════════

    def send_weekly_swing_report(self, pair_reports: list) -> bool:
        """Send Friday weekly swing report."""
        header = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        header += f"📈 QUANT DESK — WEEKLY SWING REPORT\n"
        header += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        body = ""
        for report in pair_reports:
            profile = get_profile(report["pair"])
            emoji = profile.get("emoji", "📊")
            move = report.get("total_move_pct", 0)
            move_icon = "📈" if move > 0 else "📉" if move < 0 else "➡️"

            body += f"{emoji} {report['pair']} — Week: {move:+.2f}% {move_icon}\n"
            body += f"  Predictions: {report.get('predictions_correct', 0)}/{report.get('predictions_total', 0)} correct\n"
            body += f"  Accuracy: {report.get('accuracy_pct', 0):.0f}%\n\n"
            body += report.get("ai_summary", "No summary available")
            body += "\n\n"

        footer = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        footer += f"🗑️ Week data cleaned. Fresh start Monday.\n"
        footer += f"🤖 Quant Edge | Weekly Intelligence\n"

        full_message = header + body + footer
        return self._send(full_message, parse_mode=None)

    def _get_prev_session(self, current: str) -> str:
        """Get the name of the previous session."""
        if "ny" in current.lower() or "newyork" in current.lower():
            return "London"
        return "Previous"
