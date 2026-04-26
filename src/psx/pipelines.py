"""
PSX Specific Pipelines
Runs the Multi-Agent orchestrator for PSX daily and weekly evaluations.
"""
from datetime import datetime, timezone
import time
from src.psx.data_fetcher import fetch_psx_data, fetch_psx_macro
from src.psx.news_scraper import fetch_psx_news
from src.psx.agents import PSXAgents
from src.indicators import calculate_all_indicators
from src.telegram_notifier import TelegramNotifier
from src.supabase_store import SupabaseStore
from src import config

PSX_TICKERS = ["SYS.KA", "OGDC.KA", "HUBC.KA", "MEBL.KA"] # Hardcoded for now

def run_psx_pipeline(pipeline_type: str, dry_run: bool = False):
    """
    Run the multi-agent pipeline for PSX.
    pipeline_type can be 'psx-daily' or 'psx-weekly'
    """
    print(f"\n" + "=" * 60)
    print(f"📋 QUANT DESK — PSX MULTI-AGENT PIPELINE ({pipeline_type.upper()})")
    print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    notifier = TelegramNotifier()
    store = SupabaseStore()
    
    # 1. Fetch Global/Local Macro
    print("\n[1/5] Fetching Macro Data...")
    macro_data = fetch_psx_macro()
    macro_agent_out = PSXAgents.run_macro_agent(macro_data)
    print(f"  Macro Agent: {macro_agent_out[:80]}...")

    # 2. Fetch News & Sentiment
    print("\n[2/5] Fetching PSX News & Sentiment...")
    news_items = fetch_psx_news(lookback_days=7 if pipeline_type == 'psx-weekly' else 2)
    sentiment_agent_out = PSXAgents.run_sentiment_agent(news_items)
    print(f"  Sentiment Agent: {sentiment_agent_out[:80]}...")

    # 3. Analyze Tickers via Quant, Risk, and Synthesizer Agents
    print("\n[3/5] Processing PSX Tickers...")
    current_hour = datetime.now(timezone.utc).hour
    
    results = []
    
    for ticker in PSX_TICKERS:
        print(f"\n--- {ticker} ---")
        try:
            # Data
            df = fetch_psx_data(ticker, period="6mo", interval="1d" if pipeline_type == "psx-daily" else "1wk")
            if df.empty:
                print(f"  ✗ No data for {ticker}")
                continue
                
            # Quant metrics
            params = {
                "atr_period": 14, "adx_period": 14, "rsi_period": 14,
                "bb_period": 20, "bb_std": 2, "vol_sma_period": 20,
                "zscore_period": 20, "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
                "lr_period": 20, "obv_slope_period": 10, "roc_period": 10
            }
            metrics = calculate_all_indicators(df, params, current_hour)
            
            # Agent Pipeline
            quant_out = PSXAgents.run_quant_agent(ticker, metrics)
            print(f"  Quant Agent Complete.")
            
            risk_out = PSXAgents.run_risk_agent(ticker, metrics['current_price'], metrics.get('atr_raw', 0.0))
            print(f"  Risk Agent Complete.")
            
            synth_out = PSXAgents.run_synthesizer_agent(ticker, macro_agent_out, sentiment_agent_out, quant_out, risk_out)
            print(f"  Synthesizer: Verdict={synth_out.get('verdict')} Prob={synth_out.get('probability')}%")
            
            results.append({
                "pair": ticker, # Using pair key for telegram notifier compatibility
                "score": synth_out.get('probability', 0), # Mapping prob to score
                "verdict": synth_out.get('verdict', 'NO_TRADE'),
                "bias": synth_out.get('bias', 'LONG'),
                "ai_analysis": f"Synthesizer: {synth_out.get('synthesis_reasoning', '')}",
                "metrics_summary": {
                    "rsi": metrics.get("rsi"),
                    "atr_percent": metrics.get("atr_percent"),
                    "zscore": metrics.get("zscore")
                }
            })
            
            if not dry_run:
                store.store_session_analysis(
                    pair=f"PSX_{ticker}",
                    session=pipeline_type,
                    metrics=metrics,
                    composite_score=synth_out.get('probability', 0),
                    macro_context={"macro": macro_agent_out, "sentiment": sentiment_agent_out},
                    ai_analysis=synth_out.get('synthesis_reasoning', ''),
                    ai_verdict=synth_out.get('verdict', 'NO_TRADE'),
                    ai_conditions=",".join([quant_out[:50], risk_out[:50]]),
                    price_at_analysis=metrics["current_price"]
                )
                
        except Exception as e:
            print(f"  ✗ Error on {ticker}: {e}")
            
        time.sleep(5)  # Rate limiting between tickers
        
    # 4. Telegram Notification
    print("\n[4/5] Sending Telegram Notifications...")
    if not dry_run and results:
        macro_combined = f"🌍 MACRO REGIME:\n{macro_agent_out}\n\n📰 SENTIMENT:\n{sentiment_agent_out}"
        notifier.send_pre_session_briefing(
            pipeline_type, macro_combined, results
        )
    elif dry_run:
        print("  [DRY RUN] Skipping Telegram")
        
    if pipeline_type == "psx-weekly" and not dry_run:
        print("\n[5/5] Auto-cleaning weekly PSX Database entries...")
        store.cleanup_psx_data()
        
    print("\n[✓] PSX Pipeline Complete!")
    return results
