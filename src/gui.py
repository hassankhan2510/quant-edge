import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import json
from data_fetcher import DataFetcher
from analyzer import QuantitativeAnalyzer
from ai_engine import AIEngine

class TradingSystemGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Quantitative AI Trading System")
        self.root.geometry("900x600")
        self.root.configure(padx=20, pady=20)
        
        # Stylings
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", font=("Helvetica", 11))
        style.configure("TButton", font=("Helvetica", 11, "bold"))
        
        # Title
        title_label = ttk.Label(root, text="Institutional AI Trading Framework", font=("Helvetica", 18, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Input Frame
        input_frame = ttk.Frame(root)
        input_frame.pack(fill=tk.X)
        
        ttk.Label(input_frame, text="Symbol (e.g., GC=F, EURUSD=X, DX-Y.NYB):").pack(side=tk.LEFT, padx=(0, 10))
        self.symbol_entry = ttk.Entry(input_frame, font=("Helvetica", 12), width=15)
        self.symbol_entry.insert(0, "GC=F")
        self.symbol_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        self.run_button = ttk.Button(input_frame, text="Run Analysis", command=self.start_analysis)
        self.run_button.pack(side=tk.LEFT)
        
        # Status Label
        self.status_label = ttk.Label(root, text="Status: Ready", font=("Helvetica", 10, "italic"), foreground="gray")
        self.status_label.pack(pady=10, fill=tk.X)
        
        # Results Frame
        results_frame = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Metrics Output
        metrics_frame = ttk.LabelFrame(results_frame, text="Quantitative Metrics")
        results_frame.add(metrics_frame, weight=1)
        
        self.metrics_text = scrolledtext.ScrolledText(metrics_frame, wrap=tk.WORD, font=("Courier", 10))
        self.metrics_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # AI Output
        ai_frame = ttk.LabelFrame(results_frame, text="AI Decision Engine")
        results_frame.add(ai_frame, weight=2)
        
        self.ai_text = scrolledtext.ScrolledText(ai_frame, wrap=tk.WORD, font=("Courier", 10))
        self.ai_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def update_status(self, message, color="black"):
        self.status_label.config(text=f"Status: {message}", foreground=color)

    def start_analysis(self):
        symbol = self.symbol_entry.get().strip()
        if not symbol:
            self.update_status("Please enter a valid symbol.", "red")
            return
            
        self.run_button.config(state=tk.DISABLED)
        self.update_status(f"Fetching data and analyzing {symbol}...", "blue")
        self.metrics_text.delete(1.0, tk.END)
        self.ai_text.delete(1.0, tk.END)
        
        # Run in separate thread to prevent GUI from freezing
        threading.Thread(target=self.run_pipeline, args=(symbol,), daemon=True).start()

    def run_pipeline(self, symbol):
        try:
            # 1. Fetch Data
            fetcher = DataFetcher(symbol)
            data = fetcher.fetch_data(interval="1d", period="3mo")
            
            # 2. Analyze
            self.update_status("Calculating quantitative metrics...", "blue")
            analyzer = QuantitativeAnalyzer(data)
            analyzer.run_full_analysis()
            metrics = analyzer.get_latest_metrics()
            
            # Update Metrics UI
            metrics_str = json.dumps(metrics, indent=4)
            self.root.after(0, self.metrics_text.insert, tk.END, metrics_str)
            
            # 3. AI Evaluation
            self.update_status("Requesting institutional AI evaluation (Groq)...", "blue")
            engine = AIEngine()
            decision = engine.evaluate_trade(metrics)
            
            # Update AI UI
            self.root.after(0, self.ai_text.insert, tk.END, decision)
            
            self.update_status(f"Analysis complete for {symbol}.", "green")
            
        except Exception as e:
            self.root.after(0, self.ai_text.insert, tk.END, f"Error: {str(e)}")
            self.update_status(f"An error occurred.", "red")
        finally:
            self.root.after(0, self.run_button.config, {'state': tk.NORMAL})

if __name__ == "__main__":
    root = tk.Tk()
    app = TradingSystemGUI(root)
    root.mainloop()