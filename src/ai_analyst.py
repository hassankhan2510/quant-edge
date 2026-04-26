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

        system_prompt = f"""You are an elite quantitative trading analyst at a top hedge fund. You analyze {profile['display_name']}.

CRITICAL RULES:
1. You are NOT a signal bot. Do NOT give fixed entry/SL/TP levels like "Buy at 2341.50, SL 2326.80".
2. You ARE an intelligent analyst. Give contextual, conditional analysis.
3. Reference specific numbers from the metrics. Every statement must be backed by a number.
4. Use IF-THEN conditional scenarios: "IF [condition with number], THEN [what to expect/do]"
5. Explain what conditions need to change before a trade becomes viable.
6. Consider the macro context (DXY, yields, VIX) and how it specifically affects {pair}.
7. Analyze the Hurst Exponent to classify the market regime (trending vs mean-reverting).
8. Evaluate institutional extremes using VWAP Standard Deviations.
9. Consider Kurtosis and Skewness to assess the probability of explosive moves.
10. This pair's personality: {profile['personality']}
11. Be concise but thorough. max 250 words.

OUTPUT FORMAT:
1. Current Situation (2-3 sentences with numbers)
2. Key Numbers Summary (bullet points of most important metrics)
3. What I'm Watching (2-3 IF-THEN conditional scenarios with exact thresholds)
4. Verdict: EXECUTE / DEVELOPING / WAIT / NO TRADE
5. Confidence: LOW / MEDIUM / HIGH with 1-line reason"""

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

        system_prompt = f"""You are an elite quantitative trading analyst at a top hedge fund. You analyze {profile['display_name']}.

CRITICAL RULES:
1. You are NOT a signal bot. Do NOT give fixed entry/SL/TP levels.
2. You MUST reference what the previous {prev_session} session analysis predicted and whether it was correct.
3. Explain what changed since the last analysis (numbers comparison).
4. Use IF-THEN conditional scenarios with exact thresholds.
5. Consider: did the previous session's conditions play out? What's different now?
6. Analyze the Hurst Exponent, VWAP Standard Deviations, and Kurtosis to explain structural changes.
7. This pair's personality: {profile['personality']}
8. Be concise but thorough. max 300 words.

OUTPUT FORMAT:
1. Previous Session Recap (was the prediction correct? what happened?)
2. What Changed (compare current vs previous numbers)  
3. Current Situation (2-3 sentences with numbers)
4. What I'm Watching (2-3 IF-THEN conditional scenarios)
5. Verdict: EXECUTE / DEVELOPING / WAIT / NO TRADE
6. Confidence: LOW / MEDIUM / HIGH with 1-line reason"""

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

        system_prompt = f"""You are a quantitative trading analyst reviewing today's performance for {profile['display_name']}.

YOUR JOB:
1. Compare what London analysis predicted vs what actually happened.
2. Compare what NY analysis predicted vs what actually happened.
3. Identify which metrics were predictive and which were misleading.
4. Suggest specific, actionable adjustments for tomorrow.
5. Be brutally honest about accuracy.
6. Max 250 words.

OUTPUT FORMAT:
1. London Prediction Review (correct/wrong, by how much)
2. NY Prediction Review (correct/wrong, by how much)
3. What Worked (which indicators/conditions were accurate)
4. What Failed (which indicators/conditions were wrong)
5. Suggested Adjustments (specific parameter or logic changes)
6. Overall Day Grade: A/B/C/D/F"""

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

        system_prompt = f"""You are a quantitative trading analyst producing the weekly swing report for {profile['display_name']}.

YOUR JOB:
1. Review the EVOLUTION of the week — how did the setup develop day by day?
2. Were the daily predictions consistent? Did they adapt to changing conditions?
3. What was the dominant theme of the week?
4. Produce a next-week outlook based on where we ended.
5. Identify key levels and conditions for next week.
6. Max 350 words.

OUTPUT FORMAT:
1. Week Summary (overall movement, key events)
2. Day-by-Day Evolution (1 line per day: prediction vs reality)
3. Prediction Accuracy (how many days were directionally correct)
4. Key Takeaway (what we learned this week)
5. Next Week Outlook (IF-THEN scenarios for next week)
6. Overall Week Grade: A/B/C/D/F"""

        user_content = f"""═══ WEEKLY SWING REPORT — {pair} ═══

Week Open: {week_open_price}
Week Close: {current_price}
Week Change: {week_change:+.3f}%

DAY-BY-DAY:
{chr(10).join(daily_summaries) if daily_summaries else 'No daily data available'}

Total analyses this week: {len(week_analyses)}"""

        return self._call_llm(system_prompt, user_content, temperature=0.25)
