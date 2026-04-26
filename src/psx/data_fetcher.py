"""
PSX Data Fetcher
Uses yfinance with the .KA suffix to fetch Karachi Stock Exchange (PSX) data.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta

def fetch_psx_data(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical data for a PSX ticker from Yahoo Finance.
    Automatically appends .KA if not provided.
    
    Args:
        ticker: e.g. "SYS", "OGDC", "HUBC"
        period: e.g. "1mo", "3mo", "6mo", "1y"
        interval: e.g. "1d", "1wk"
    """
    # Ensure PSX suffix is present
    if not ticker.endswith(".KA"):
        symbol = f"{ticker}.KA"
    else:
        symbol = ticker
        
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        
        if df.empty:
            raise ValueError(f"No data returned for {symbol}")
            
        # Clean up multi-index columns if returned by newer yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        return df.dropna()
    except Exception as e:
        print(f"[PSX Data Fetcher] Error fetching {symbol}: {e}")
        return pd.DataFrame()

def fetch_psx_macro() -> dict:
    """
    Fetch relevant macro data for Pakistan.
    Since real-time PKRV/KIBOR is hard to scrape cleanly without custom APIs, 
    we proxy risk with USD/PKR (PKR=X) and Frontier Markets ETF (FM).
    """
    try:
        # Fetch USD/PKR exchange rate
        usdpkr = yf.download("PKR=X", period="1mo", interval="1d", progress=False)
        
        # MSCI Emerging Markets ETF (proxy for EM/Frontier appetite)
        fm_etf = yf.download("EEM", period="1mo", interval="1d", progress=False)
        
        if usdpkr.empty or fm_etf.empty:
            return {"usdpkr": 0, "fm_trend": "unknown"}
            
        if isinstance(usdpkr.columns, pd.MultiIndex):
            usdpkr.columns = usdpkr.columns.droplevel(1)
            fm_etf.columns = fm_etf.columns.droplevel(1)
            
        current_pkr = float(usdpkr["Close"].iloc[-1])
        prev_pkr = float(usdpkr["Close"].iloc[-5]) # 1 week ago
        pkr_change = ((current_pkr - prev_pkr) / prev_pkr) * 100
        
        fm_current = float(fm_etf["Close"].iloc[-1])
        fm_prev = float(fm_etf["Close"].iloc[-5])
        fm_change = ((fm_current - fm_prev) / fm_prev) * 100
        
        return {
            "usdpkr_current": round(current_pkr, 2),
            "usdpkr_weekly_change_pct": round(pkr_change, 2),
            "frontier_markets_weekly_pct": round(fm_change, 2)
        }
    except Exception as e:
        print(f"[PSX Macro Fetcher] Error: {e}")
        return {}

if __name__ == "__main__":
    # Test execution
    df = fetch_psx_data("SYS", period="1mo")
    print("SYS DataFrame Tail:")
    print(df.tail(2))
    
    macro = fetch_psx_macro()
    print("\nMacro Data:")
    print(macro)
