import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env.local'
load_dotenv(dotenv_path=env_path)

class AIEngine:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing from environment variables.")
        
        self.client = Groq(api_key=self.api_key)

    def evaluate_trade(self, structured_data: dict) -> str:
        """
        Takes quantified metrics and sends to Groq model for a rule-based AI evaluation.
        Expects keys like: trend_strength, volume_expansion, volatility_regime, momentum_shift.
        """
        system_prompt = (
            "You are an elite quantitative trading architect and institutional strategist. "
            "Evaluate the provided quantitative technical attributes and respond strictly with: "
            "1. Decision: [EXECUTE TRADE / WAIT / NO TRADE]\n"
            "2. Score: [0-100]\n"
            "3. Reason: [Detailed mechanical breakdown including why, what condition failed, what needs to improve]\n\n"
            "Follow probabilistic logic: high volatility + weak momentum = NO TRADE. "
        )

        user_content = f"Evaluate this current market state:\n{structured_data}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2, # Keep it deterministic and analytical
        )
        return response.choices[0].message.content
