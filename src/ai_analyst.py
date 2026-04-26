"""
Quant Edge — Intelligent AI Analyst
NOT a signal generator. An analyst that thinks, conditions, and references previous sessions.
Uses Groq LLM with structured prompts per analysis type.
"""
import json
from groq import Groq
from src import config
from src.pair_profiles import get_profile


class AIAnalyst:
    """AI-powered analyst that produces contextual, conditional market analysis."""

    def __init__(self):
        if not config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing from environment variables.")
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = config.GROQ_MODEL

    def _call_llm(self, system_prompt: str, user_content: str, temperature: float = 0.3) -> str:
        """Make a call to Groq LLM."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[AI ERROR] {str(e)}"

    # ═══════════════════════════════════════════════════════════
    # PRE-SESSION ANALYSIS (London — No Previous Context)
    # ═══════════════════════════════════════════════════════════

    def analyze_pre_session(self, pair: str, system: str,
                            metrics: dict, score_result: dict,
                            macro_context: dict) -> str:
        """
        Fresh session analysis — no previous context.
        Used for London open and Monday swing setup.
        """
        profile = get_profile(pair)

        system_prompt = f"""Adopt the persona of a battle-hardened Street Trader—an institutional 'shark' at a top-tier desk. You analyze {profile['display_name']}. 

CRITICAL TRADING PHILOSOPHY:
1. STOP LOOKING FOR PERFECTION. Textbooks are for losers. Real traders find an edge in the chaos and take calculated risk.
2. AVOID GPT FLUFF. No polite introductions, no "as an AI" garbage. Speak like you're on a live desk where every second costs money.
3. BE AGGRESSIVE. If you see a probability-weighted opportunity, say it clearly. If the market is garbage, say stay out.
4. HUNT THE ANOMALY. Use Hurst, Kurtosis, and VWAP not to find "signals," but to find the 'trap'—where is the retail crowd getting liquidated?
5. YOU ARE A RISK TAKER. You aren't afraid of a messy chart as long as the statistical numbers (Z-score, Vol Ratio, Kurtosis) favor an aggressive move.

RULES:
1. NO fixed Entry/SL/TP levels. That's for retail signal bots.
2. Contextual & Conditional only. Always IF [number threshold] THEN [Aggressive Scenario].
3. Back every single claim with a specific metric number. 
4. Personality for this asset: {profile['personality']}
5. Max 250 words. Be sharp, direct, and slightly cynical of the "obvious" move.

OUTPUT FORMAT:
1. THE TAPE: (2-3 sentences: what is the market actually doing versus what it should be doing?)
2. HARD NUMBERS: (Bullet points of the metrics that actually matter for this setup)
3. THE HUSTLE: (2-3 IF-THEN aggressive conditional scenarios. Where do we attack?)
4. VERDICT: EXECUTE / DEVELOPING / WAIT / NO TRADE
5. CONVICTION: LOW / MEDIUM / HIGH (Explicitly why you are willing to risk capital here)"""

        user_content = f"""Analyze {pair} for {system} trading.

QUANTITATIVE METRICS (Primary Timeframe):
{json.dumps(metrics, indent=2, default=str)}

SCORING RESULT:
Composite Score: {score_result.get('final_score', 0)}/100
Verdict: {score_result.get('final_verdict', 'N/A')}
Bias: {score_result.get('bias', 'N/A')}
Gates Passed: {score_result.get('gates', {}).get('all_passed', False)}
Failed Gates: {score_result.get('gates', {}).get('failed_gates', [])}

Factor Breakdown:
{json.dumps(score_result.get('scoring', {}).get('factor_scores', {}), indent=2, default=str)}

MACRO CONTEXT:
{json.dumps(macro_context, indent=2, default=str)}"""

        return self._call_llm(system_prompt, user_content)

    # ═══════════════════════════════════════════════════════════
    # CONTEXTUAL ANALYSIS (NY — Has London's Previous Analysis)
    # ═══════════════════════════════════════════════════════════

    def analyze_with_context(self, pair: str, system: str,
                              current_metrics: dict, score_result: dict,
                              macro_context: dict,
                              previous_analysis: dict) -> str:
        """
        Context-aware analysis — references previous session's predictions.
        Used for NY (with London context) and daily swing (with week context).
        """
        profile = get_profile(pair)

        prev_session = previous_analysis.get("session", "previous")
        prev_ai_text = previous_analysis.get("ai_analysis", "No previous analysis available")
        prev_price = previous_analysis.get("price_at_analysis", 0)
        prev_score = previous_analysis.get("composite_score", 0)
        prev_verdict = previous_analysis.get("ai_verdict", "N/A")
        current_price = current_metrics.get("current_price", 0)

        price_change = 0
        if prev_price and current_price:
            price_change = ((current_price - prev_price) / prev_price) * 100

        system_prompt = f"""You are the Street Shark Analyst. You analyze {profile['display_name']} with a memory.

TRADING PHILOSOPHY:
1. AUDIT THE PREVIOUS SESSION. Did our {prev_session} analysis get it right? If it failed, EXPLAIN WHY. Don't hide.
2. NO TEXTBOOK ANSWERS. Focus on the 'Why' behind the move. 
3. STREET SMARTS. Analyze the change in Hurst and VWAP Sigmas to see if the 'Smart Money' is rotating or trapping.
4. AGGRESSIVE CONDITIONING. Don't just say wait. Say "If they push it past [Number], they are trapping the shorts and we attack LONG."

RULES:
1. NO fixed entry/SL levels.
2. Reference the previous session's predictions explicitly.
3. Use IF-THEN scenarios for the transition from {prev_session} into the current session.
4. Max 300 words. Brutally direct.

OUTPUT FORMAT:
1. THE AUDIT: (Did the {prev_session} prediction hold up? Compare current price vs predicted levels)
2. THE SHIFT: (What changed specifically in the numbers current vs previous?)
3. THE PLAY: (IF-THEN aggressive conditional scenarios for the next 4-8 hours)
4. VERDICT: EXECUTE / DEVELOPING / WAIT / NO TRADE
5. CONVICTION: LOW / MEDIUM / HIGH (Why are we taking this risk?)"""

        user_content = f"""Analyze {pair} for {system} trading.

═══ PREVIOUS {prev_session.upper()} SESSION ANALYSIS ═══
Score: {prev_score}/100 | Verdict: {prev_verdict}
Price at analysis: {prev_price}
AI Analysis: {prev_ai_text}

═══ SINCE THEN ═══
Current Price: {current_price} (change: {price_change:+.3f}%)

═══ CURRENT METRICS (Fresh Calculation) ═══
{json.dumps(current_metrics, indent=2, default=str)}

═══ CURRENT SCORING ═══
Composite Score: {score_result.get('final_score', 0)}/100
Verdict: {score_result.get('final_verdict', 'N/A')}
Bias: {score_result.get('bias', 'N/A')}
Gates: {score_result.get('gates', {}).get('all_passed', False)}

Factor Breakdown:
{json.dumps(score_result.get('scoring', {}).get('factor_scores', {}), indent=2, default=str)}

═══ MACRO CONTEXT ═══
{json.dumps(macro_context, indent=2, default=str)}"""

        return self._call_llm(system_prompt, user_content)

    # ═══════════════════════════════════════════════════════════
    # END-OF-DAY REVIEW
    # ═══════════════════════════════════════════════════════════

    def analyze_eod_review(self, pair: str,
                            london_data: dict, ny_data: dict,
                            current_price: float) -> str:
        """
        End-of-day self-review. Compare predictions vs actuals.
        AI identifies what worked, what didn't, and suggests adjustments.
        """
        profile = get_profile(pair)

        london_price = london_data.get("price_at_analysis", 0) if london_data else 0
        ny_price = ny_data.get("price_at_analysis", 0) if ny_data else 0

        london_move = ((current_price - london_price) / london_price * 100) if london_price else 0
        ny_move = ((current_price - ny_price) / ny_price * 100) if ny_price else 0

        system_prompt = f"""You are the Head Risk Manager reviewing today's execution for {profile['display_name']}. 

Be BRUTALLY HONEST. Your job isn't to be nice; it's to keep the capital from evaporating.

1. Did the analysis catch the trap?
2. Were our IF-THEN scenarios reality-based or just wishful thinking?
3. Which indicator lied to us today? (Hurst, VWAP, RSI?)
4. GRADE THE TRADERS. Was our AI/Math engine 'dumb' or 'street smart' today?
5. Max 250 words. No fluff.

OUTPUT FORMAT:
1. REALITY CHECK: (London & NY vs Actual Move)
2. THE TRAP WE MISSED: (What did we overlook?)
3. THE EDGE WE CAUGHT: (What was correctly diagnosed?)
4. STREET ADJUSTMENTS: (Actionable risk/logic changes for tomorrow)
5. GRADE: A/B/C/D/F (If we lost money on a bad read, it's an F)"""

        user_content = f"""═══ TODAY'S REVIEW — {pair} ═══

LONDON SESSION:
Prediction: {london_data.get('ai_verdict', 'N/A') if london_data else 'No analysis'}
Score: {london_data.get('composite_score', 'N/A') if london_data else 'N/A'}/100
AI Said: {london_data.get('ai_analysis', 'No analysis') if london_data else 'N/A'}
Price at London analysis: {london_price}
Key Metrics: {json.dumps(london_data.get('metrics', {}), indent=2, default=str) if london_data else 'N/A'}

NY SESSION:
Prediction: {ny_data.get('ai_verdict', 'N/A') if ny_data else 'No analysis'}
Score: {ny_data.get('composite_score', 'N/A') if ny_data else 'N/A'}/100
AI Said: {ny_data.get('ai_analysis', 'No analysis') if ny_data else 'N/A'}
Price at NY analysis: {ny_price}
Key Metrics: {json.dumps(ny_data.get('metrics', {}), indent=2, default=str) if ny_data else 'N/A'}

ACTUAL RESULTS:
Current Price: {current_price}
Move since London: {london_move:+.3f}%
Move since NY: {ny_move:+.3f}%"""

        return self._call_llm(system_prompt, user_content, temperature=0.2)

    # ═══════════════════════════════════════════════════════════
    # WEEKLY SWING REPORT
    # ═══════════════════════════════════════════════════════════

    def analyze_weekly_swing(self, pair: str,
                              week_analyses: list,
                              current_price: float,
                              week_open_price: float) -> str:
        """
        Friday weekly review for swing trades.
        AI gets the full week's evolution to produce comprehensive report.
        """
        profile = get_profile(pair)

        week_change = ((current_price - week_open_price) / week_open_price * 100) if week_open_price else 0

        # Build day-by-day summary
        daily_summaries = []
        for day_data in week_analyses:
            day = day_data.get("analysis_date", "?")
            score = day_data.get("composite_score", 0)
            verdict = day_data.get("ai_verdict", "N/A")
            price = day_data.get("price_at_analysis", 0)
            ai_text = day_data.get("ai_analysis", "")[:200]  # Truncate
            daily_summaries.append(
                f"Day {day}: Score={score}/100, Verdict={verdict}, "
                f"Price={price}\n  AI: {ai_text}..."
            )

        system_prompt = f"""You are the Senior Portfolio Manager executing the Weekly Debrief for {profile['display_name']}. 

CRITICAL MISSION:
1. HUNT THE ALPHA. Did we exploit the week's biggest moves or were we asleep at the wheel?
2. AUDIT THE ADAPTABILITY. Did our daily logic pivot when the Hurst regime shifted, or were we trading yesterday's news?
3. NEXT WEEK'S TARGETS. Don't give me vague outlooks. Give me the zones where we are going to attack. 
4. NO GPT POLITENESS. Be cold, analytical, and focused on the next profitable risk.
5. Max 350 words.

OUTPUT FORMAT:
1. THE HUNT: (Overall week movement vs our performance)
2. THE TAPE EVOLUTION: (How the price action actually traded vs our day-by-day bias)
3. THE ALPHA CAUGHT: (Where did our analysis explicitly win?)
4. THE BLIND SPOTS: (Where did we get trapped or outsmarted by the tape?)
5. NEXT WEEK'S WAR ROOM: (IF-THEN aggressive attack scenarios for Monday-Friday)
6. PERFORMANCE GRADE: A/B/C/D/F"""

        user_content = f"""═══ WEEKLY SWING REPORT — {pair} ═══

Week Open: {week_open_price}
Week Close: {current_price}
Week Change: {week_change:+.3f}%

DAY-BY-DAY:
{chr(10).join(daily_summaries) if daily_summaries else 'No daily data available'}

Total analyses this week: {len(week_analyses)}"""

        return self._call_llm(system_prompt, user_content, temperature=0.25)
