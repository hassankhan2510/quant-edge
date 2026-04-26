import json
from src import config
from groq import Groq

# We reuse the core Groq client
client = Groq(api_key=config.GROQ_API_KEY)
MODEL = config.GROQ_MODEL

def _run_agent(system_prompt: str, user_prompt: str) -> str:
    """Helper to run a specific agent's prompt through Groq."""
    if not config.GROQ_API_KEY:
        return "ERROR: Groq API key not found. Dry run fallback."
        
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Highly deterministic for agents
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Agent Error] {e}")
        return f"Error evaluating data: {e}"

class PSXAgents:
    """
    Lightweight python-based multi-agent orchestrator for PSX.
    Simulates a LangGraph directed acyclic graph.
    """
    
    @staticmethod
    def run_macro_agent(macro_data: dict) -> str:
        """Evaluates USD/PKR and Emerging Market flows to determine risk regime."""
        system_prompt = (
            "You are the PSX Macro Shark. Your job is to sniff out the real risk regime in Pakistan. "
            "Ignore the noise. Look at USD/PKR and EM flows to decide if the big money is running for the exit or loading up. "
            "Output one aggressive paragraph declaring RISK-ON, NEUTRAL, or RISK-OFF with a street-smart justification."
        )
        user_prompt = f"Here is the latest macro data proxy:\n{json.dumps(macro_data, indent=2)}"
        return _run_agent(system_prompt, user_prompt)
        
    @staticmethod
    def run_sentiment_agent(news_items: list) -> str:
        """Evaluates Business Recorder / local headlines for market sentiment."""
        system_prompt = (
            "You are the PSX Sentiment Profiler. Review these headlines. Are we looking at a 'Buy the Rumor' trap, "
            "genuine panic, or institutional accumulation? Forget textbook sentiment. "
            "Return BULLISH, BEARISH, or MIXED and a blunt 2-sentence summary of the psychological state of the Karachi market."
        )
        headlines = "\n".join([f"- {n['title']} ({n['published']})" for n in news_items])
        user_prompt = f"Recent news headlines:\n{headlines}"
        return _run_agent(system_prompt, user_prompt)
        
    @staticmethod
    def run_quant_agent(ticker: str, technical_metrics: dict) -> str:
        """Evaluates technical indicators and anomaly scores."""
        system_prompt = (
            "You are the Quant Anomaly Agent. You analyze mathematical indicators for a specific stock "
            "on the PSX to find statistical edges. Return an analysis identifying if the setup is "
            "oversold, overbought, trending, or ranging."
        )
        user_prompt = f"Ticker: {ticker}\nTechnical Data:\n{json.dumps(technical_metrics, indent=2, default=str)}"
        return _run_agent(system_prompt, user_prompt)
        
    @staticmethod
    def run_risk_agent(ticker: str, current_price: float, atr: float) -> str:
        """Calculates portfolio risk and stop placement."""
        # This is hybrid math + AI formatting
        stop_loss = current_price - (atr * 1.5)
        kelly_fraction = config.KELLY_FRACTION * 100 # percentage base
        
        system_prompt = (
            "You are the Risk & Kelly Agent. Given the price, ATR, and system Kelly constraints, "
            "output a strictly formatted risk management block."
        )
        user_prompt = (
            f"Ticker: {ticker}\nCurrent Price: {current_price}\nATR: {atr}\n"
            f"Calculated Hard Stop: {stop_loss}\nSystem Kelly Fraction: {kelly_fraction}%"
        )
        return _run_agent(system_prompt, user_prompt)
        
    @staticmethod
    def run_synthesizer_agent(ticker: str, macro_out: str, sentiment_out: str, quant_out: str, risk_out: str) -> dict:
        """
        The Final Synthesizer. Takes input from all 4 upstream agents and makes 
        the ultimate probability-weighted trading decision.
        """
        system_prompt = (
            "You are the CHIEF EXECUTION SHARK for the PSX Quant Desk. "
            "Review the intel from Macro, Sentiment, Quant, and Risk. Do not search for perfection. "
            "If the confluences favor a dirty, high-probability trap, we take it. "
            "Output JSON ONLY: {'verdict': 'EXECUTE/DEVELOPING/NO_TRADE', 'bias': 'LONG/NO_BIAS', "
            "'probability': 0-100, 'synthesis_reasoning': 'Blunt, 2-sentence justification for the capital risk.'}"
        )
        user_prompt = f"""
        TICKER: {ticker}
        
        [MACRO AGENT]: {macro_out}
        [SENTIMENT AGENT]: {sentiment_out}
        [QUANT AGENT]: {quant_out}
        [RISK AGENT]: {risk_out}
        
        Synthesize this into the final JSON output.
        """
        
        raw_response = _run_agent(system_prompt, user_prompt)
        
        try:
            # Clean possible markdown from response
            cleaned = raw_response.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception as e:
            print(f"[Synthesizer Error] Failed to parse JSON: {e}")
            return {
                "verdict": "ERROR",
                "bias": "NO_BIAS",
                "probability": 0,
                "synthesis_reasoning": f"Failed to parse agent output: {raw_response[:100]}..."
            }
