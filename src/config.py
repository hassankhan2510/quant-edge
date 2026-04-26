"""
Quant Edge — Central Configuration
All tunable parameters live here. No magic numbers anywhere else.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).resolve().parent.parent / '.env.local'
load_dotenv(dotenv_path=env_path)

# ─── API Keys ─────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ─── Data Source Priority ─────────────────────────────────────
# Alpha Vantage is primary, yfinance is fallback
DATA_SOURCE_PRIMARY = "alpha_vantage"
DATA_SOURCE_FALLBACK = "yfinance"

# ─── Session Windows (UTC) ────────────────────────────────────
SESSIONS = {
    "london": {"open_utc": 7, "close_utc": 16},
    "newyork": {"open_utc": 12, "close_utc": 21},
    "overlap": {"open_utc": 12, "close_utc": 16},  # London-NY overlap
    "asia": {"open_utc": 0, "close_utc": 8},
}

# ─── Indicator Defaults ──────────────────────────────────────
# These are overridden per-pair in pair_profiles.py
DEFAULT_ATR_PERIOD = 14
DEFAULT_ADX_PERIOD = 14
DEFAULT_RSI_PERIOD = 14
DEFAULT_BB_PERIOD = 20
DEFAULT_BB_STD = 2
DEFAULT_VOL_SMA_PERIOD = 20
DEFAULT_ZSCORE_PERIOD = 20
DEFAULT_MACD_FAST = 12
DEFAULT_MACD_SLOW = 26
DEFAULT_MACD_SIGNAL = 9
DEFAULT_LR_PERIOD = 20
DEFAULT_OBV_SLOPE_PERIOD = 10
DEFAULT_ROC_PERIOD = 10

# ─── Scoring Thresholds ──────────────────────────────────────
SCORE_EXECUTE = 65      # Lowered since AI handles final conditional confluences (Score >= 65)
SCORE_DEVELOPING = 50   # 50 <= Score < 65 → DEVELOPING / CONDITIONAL
SCORE_NO_TRADE = 50     # Score < 50 → NO TRADE / WAIT

# ─── Risk Parameters ─────────────────────────────────────────
RISK_PER_TRADE_PCT = 1.0        # 1% of capital per trade
MAX_DAILY_LOSS_PCT = 3.0        # Kill switch if daily loss hits 3%
SWING_ATR_SL_MULTIPLIER = 2.0   # Stop loss = ATR × 2 for swing
DAY_ATR_SL_MULTIPLIER = 1.5     # Stop loss = ATR × 1.5 for day
MIN_REWARD_RISK_RATIO = 2.0     # Minimum 1:2 RR
KELLY_FRACTION = 0.25           # Quarter-Kelly for position sizing

# ─── Day Trading Pairs ───────────────────────────────────────
DAY_TRADE_PAIRS = ["XAUUSD", "EURUSD", "GBPUSD"]

# ─── Swing Trading Pairs ─────────────────────────────────────
SWING_TRADE_PAIRS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]

# ─── All Pairs (union) ───────────────────────────────────────
ALL_PAIRS = list(set(DAY_TRADE_PAIRS + SWING_TRADE_PAIRS))

# ─── Macro Symbols ───────────────────────────────────────────
DXY_SYMBOL = "DX-Y.NYB"          # Dollar Index (yfinance)
DXY_AV_SYMBOL = "DXY"            # Dollar Index (Alpha Vantage)
US10Y_SYMBOL = "^TNX"            # 10-Year Treasury Yield
VIX_SYMBOL = "^VIX"              # Volatility Index

# ─── Alpha Vantage Forex Mapping ─────────────────────────────
AV_FOREX_PAIRS = {
    "XAUUSD": {"from": "XAU", "to": "USD"},
    "EURUSD": {"from": "EUR", "to": "USD"},
    "GBPUSD": {"from": "GBP", "to": "USD"},
    "USDJPY": {"from": "USD", "to": "JPY"},
}

# ─── yfinance Symbol Mapping (Fallback) ──────────────────────
YF_SYMBOLS = {
    "XAUUSD": "GC=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
}

# ─── Timeframe Mapping for Alpha Vantage ─────────────────────
AV_INTERVALS = {
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    "60min": "60min",
    "1h": "60min",
    "4h": "60min",      # We'll resample 60min → 4h
    "1d": "daily",
    "1wk": "weekly",
}
