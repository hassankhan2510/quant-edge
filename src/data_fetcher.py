"""
Quant Edge — Data Fetcher
Alpha Vantage as primary source, yfinance as fallback.
Handles multi-timeframe data for any pair across both sources.
"""
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from typing import Optional
from src import config
from src.pair_profiles import get_profile, get_timeframes

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False


class DataFetcher:
    """Fetches market data with Alpha Vantage primary and yfinance fallback."""

    AV_BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        self.av_key = config.ALPHA_VANTAGE_API_KEY
        self._av_call_count = 0
        self._av_last_call = 0

    # ─── Rate Limiter ─────────────────────────────────────────
    def _av_rate_limit(self):
        """Alpha Vantage free tier: 25 requests/day, 5/min. Wait if needed."""
        now = time.time()
        elapsed = now - self._av_last_call
        if elapsed < 12.5:  # ~5 calls/min → wait 12.5s between calls
            time.sleep(12.5 - elapsed)
        self._av_last_call = time.time()
        self._av_call_count += 1

    # ─── Alpha Vantage: Forex Intraday ───────────────────────
    def _fetch_av_forex_intraday(self, pair: str, interval: str, outputsize: str = "compact") -> pd.DataFrame:
        """Fetch forex intraday data from Alpha Vantage."""
        av_pair = config.AV_FOREX_PAIRS.get(pair)
        if not av_pair:
            raise ValueError(f"No AV mapping for {pair}")

        self._av_rate_limit()

        params = {
            "function": "FX_INTRADAY",
            "from_symbol": av_pair["from"],
            "to_symbol": av_pair["to"],
            "interval": interval,
            "outputsize": outputsize,
            "apikey": self.av_key,
        }

        resp = requests.get(self.AV_BASE_URL, params=params, timeout=30)
        data = resp.json()

        ts_key = f"Time Series FX (Intraday)"
        # Alpha Vantage uses dynamic key names
        ts_key = None
        for key in data:
            if "Time Series" in key:
                ts_key = key
                break

        if not ts_key or ts_key not in data:
            note = data.get("Note", data.get("Information", "Unknown error"))
            raise ValueError(f"AV forex intraday error for {pair}: {note}")

        df = pd.DataFrame.from_dict(data[ts_key], orient="index")
        df.columns = ["Open", "High", "Low", "Close"]
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df.astype(float)
        df["Volume"] = 0  # Forex has no true volume in AV
        return df

    # ─── Alpha Vantage: Forex Daily ──────────────────────────
    def _fetch_av_forex_daily(self, pair: str, outputsize: str = "compact") -> pd.DataFrame:
        """Fetch forex daily data from Alpha Vantage."""
        av_pair = config.AV_FOREX_PAIRS.get(pair)
        if not av_pair:
            raise ValueError(f"No AV mapping for {pair}")

        self._av_rate_limit()

        params = {
            "function": "FX_DAILY",
            "from_symbol": av_pair["from"],
            "to_symbol": av_pair["to"],
            "outputsize": outputsize,
            "apikey": self.av_key,
        }

        resp = requests.get(self.AV_BASE_URL, params=params, timeout=30)
        data = resp.json()

        ts_key = None
        for key in data:
            if "Time Series" in key:
                ts_key = key
                break

        if not ts_key:
            note = data.get("Note", data.get("Information", "Unknown error"))
            raise ValueError(f"AV forex daily error for {pair}: {note}")

        df = pd.DataFrame.from_dict(data[ts_key], orient="index")
        df.columns = ["Open", "High", "Low", "Close"]
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df.astype(float)
        df["Volume"] = 0
        return df

    # ─── Alpha Vantage: Forex Weekly ─────────────────────────
    def _fetch_av_forex_weekly(self, pair: str) -> pd.DataFrame:
        """Fetch forex weekly data from Alpha Vantage."""
        av_pair = config.AV_FOREX_PAIRS.get(pair)
        if not av_pair:
            raise ValueError(f"No AV mapping for {pair}")

        self._av_rate_limit()

        params = {
            "function": "FX_WEEKLY",
            "from_symbol": av_pair["from"],
            "to_symbol": av_pair["to"],
            "apikey": self.av_key,
        }

        resp = requests.get(self.AV_BASE_URL, params=params, timeout=30)
        data = resp.json()

        ts_key = None
        for key in data:
            if "Time Series" in key:
                ts_key = key
                break

        if not ts_key:
            note = data.get("Note", data.get("Information", "Unknown error"))
            raise ValueError(f"AV forex weekly error for {pair}: {note}")

        df = pd.DataFrame.from_dict(data[ts_key], orient="index")
        df.columns = ["Open", "High", "Low", "Close"]
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df.astype(float)
        df["Volume"] = 0
        return df

    # ─── yfinance Fallback ───────────────────────────────────
    def _fetch_yf(self, symbol: str, interval: str, period: str) -> pd.DataFrame:
        """Fetch data from yfinance as fallback."""
        if not YF_AVAILABLE:
            raise ImportError("yfinance not installed")

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            raise ValueError(f"No yfinance data for {symbol}")
        df = df.dropna()

        # Standardize columns
        if "Adj Close" in df.columns:
            df = df.drop(columns=["Adj Close"], errors="ignore")
        if "Dividends" in df.columns:
            df = df.drop(columns=["Dividends"], errors="ignore")
        if "Stock Splits" in df.columns:
            df = df.drop(columns=["Stock Splits"], errors="ignore")

        return df[["Open", "High", "Low", "Close", "Volume"]]

    # ─── Resample to 4H ─────────────────────────────────────
    def _resample_to_4h(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resample 1h data to 4h candles."""
        resampled = df.resample("4h").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }).dropna()
        return resampled

    # ─── Universal Fetch ─────────────────────────────────────
    def fetch(self, pair: str, timeframe: str, bars: int = 100) -> pd.DataFrame:
        """
        Fetch data for a pair at a given timeframe.
        Strategy: 
          - Daily/Weekly → Alpha Vantage first (free tier), yfinance fallback
          - Intraday → yfinance first (AV intraday is premium), AV daily fallback

        Args:
            pair: e.g., "XAUUSD", "EURUSD"
            timeframe: e.g., "15min", "1h", "4h", "1d", "1wk"
            bars: approximate number of bars desired
        """
        df = None
        source = "none"
        is_intraday = timeframe in ["1min", "5min", "15min", "30min", "60min", "1h", "4h"]

        if is_intraday:
            # ── Intraday: yfinance FIRST (AV intraday is premium) ──
            if YF_AVAILABLE:
                yf_symbol = config.YF_SYMBOLS.get(pair, pair)
                try:
                    yf_interval_map = {
                        "1min": ("1m", "7d"),
                        "5min": ("5m", "60d"),
                        "15min": ("15m", "60d"),
                        "30min": ("30m", "60d"),
                        "1h": ("1h", "2y"),
                        "60min": ("60m", "2y"),
                        "4h": ("1h", "2y"),
                    }
                    yf_tf, yf_period = yf_interval_map.get(timeframe, ("1h", "2y"))
                    df = self._fetch_yf(yf_symbol, yf_tf, yf_period)
                    if timeframe == "4h":
                        df = self._resample_to_4h(df)
                    source = "yfinance"
                except Exception as e:
                    print(f"[YF] Failed for {pair} ({yf_symbol}) {timeframe}: {e}")
                    df = None
        else:
            # ── Daily/Weekly: Alpha Vantage FIRST (free tier covers this) ──
            if self.av_key and pair in config.AV_FOREX_PAIRS:
                try:
                    if timeframe == "1wk":
                        df = self._fetch_av_forex_weekly(pair)
                        source = "alpha_vantage"
                    elif timeframe == "1d":
                        outputsize = "full" if bars > 100 else "compact"
                        df = self._fetch_av_forex_daily(pair, outputsize)
                        source = "alpha_vantage"
                except Exception as e:
                    print(f"[AV] Failed for {pair} {timeframe}: {e}")
                    df = None

            # yfinance fallback for daily/weekly
            if df is None and YF_AVAILABLE:
                yf_symbol = config.YF_SYMBOLS.get(pair, pair)
                try:
                    yf_interval_map = {
                        "1d": ("1d", "2y"),
                        "1wk": ("1wk", "5y"),
                    }
                    yf_tf, yf_period = yf_interval_map.get(timeframe, ("1d", "1y"))
                    df = self._fetch_yf(yf_symbol, yf_tf, yf_period)
                    source = "yfinance"
                except Exception as e:
                    print(f"[YF] Failed for {pair} ({yf_symbol}) {timeframe}: {e}")
                df = None

        if df is None:
            raise ValueError(f"Could not fetch data for {pair} {timeframe} from any source")

        # Trim to approximate bar count
        if len(df) > bars:
            df = df.tail(bars)

        print(f"  ✓ {pair} {timeframe}: {len(df)} bars from {source}")
        return df

    # ─── Multi-Timeframe Fetch ───────────────────────────────
    def fetch_multi_tf(self, pair: str, system: str) -> dict:
        """
        Fetch all required timeframes for a pair+system.
        Returns dict like: {"htf": df, "primary": df, "ltf": df}
        """
        timeframes = get_timeframes(pair, system)
        result = {}

        for tf_key, tf_value in timeframes.items():
            bars = 200 if tf_key == "htf" else 100
            result[tf_key] = self.fetch(pair, tf_value, bars=bars)

        return result

    # ─── Macro Data Fetch ────────────────────────────────────
    def fetch_macro_data(self) -> dict:
        """
        Fetch DXY, US10Y, VIX data for macro context.
        These are only available via yfinance (not forex pairs).
        """
        result = {}

        macro_symbols = {
            "DXY": (config.DXY_SYMBOL, "1d", "3mo"),
            "DXY_1h": (config.DXY_SYMBOL, "1h", "1mo"),
            "US10Y": (config.US10Y_SYMBOL, "1d", "3mo"),
            "VIX": (config.VIX_SYMBOL, "1d", "3mo"),
        }

        for key, (symbol, interval, period) in macro_symbols.items():
            try:
                if YF_AVAILABLE:
                    df = self._fetch_yf(symbol, interval, period)
                    result[key] = df
                    print(f"  ✓ Macro {key}: {len(df)} bars from yfinance")
                else:
                    print(f"  ✗ Macro {key}: yfinance not available")
            except Exception as e:
                print(f"  ✗ Macro {key}: {e}")

        return result
