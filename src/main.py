from data_fetcher import DataFetcher
from analyzer import QuantitativeAnalyzer
from ai_engine import AIEngine
import json

def run_trading_system(symbol: str):
    print(f"--- Starting Quantitative Analysis for {symbol} ---")
    
    # 1. Fetch Data
    fetcher = DataFetcher(symbol)
    try:
        data = fetcher.fetch_data(interval="1d", period="3mo")
    except Exception as e:
        print(f"Data fetch error: {e}")
        return

    # 2. Analyze Quantitative Metrics
    analyzer = QuantitativeAnalyzer(data)
    analyzer.run_full_analysis()
    metrics = analyzer.get_latest_metrics()
    
    print("\n[Latest Quantitative Metrics]")
    print(json.dumps(metrics, indent=2))
    
    # 3. AI Evaluation
    engine = AIEngine()
    print("\n[Requesting AI Evaluation...]")
    decision = engine.evaluate_trade(metrics)
    
    print("\n[AI Trading Decision]")
    print(decision)

if __name__ == "__main__":
    # Example for Gold. Note: yfinance symbol for Gold is GC=F. EURUSD=X for Forex.
    # XAUUSD=X is often used for spot gold against USD.
    symbols = ["GC=F", "DX-Y.NYB", "EURUSD=X"]
    
    for sym in symbols:
        run_trading_system(sym)
        print("="*60)
