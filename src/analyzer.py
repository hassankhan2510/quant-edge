import pandas as pd
from ta.volatility import AverageTrueRange
from ta.trend import ADXIndicator, SMAIndicator
from ta.volume import VolumePriceTrendIndicator

class QuantitativeAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self.df = data.copy()

    def calculate_atr(self, period=14):
        atr = AverageTrueRange(high=self.df['High'], low=self.df['Low'], close=self.df['Close'], window=period)
        self.df['ATR'] = atr.average_true_range()
    
    def calculate_trend_strength(self, period=14):
        adx = ADXIndicator(high=self.df['High'], low=self.df['Low'], close=self.df['Close'], window=period)
        self.df['ADX'] = adx.adx()
    
    def calculate_volume_delta(self, period=20):
        if 'Volume' not in self.df.columns or self.df['Volume'].sum() == 0:
            self.df['Vol_SMA'] = 1
            self.df['Vol_Expansion'] = 1
            return
            
        sma_volume = SMAIndicator(close=self.df['Volume'], window=period)
        self.df['Vol_SMA'] = sma_volume.sma_indicator()
        # Avoid division by zero
        self.df['Vol_Expansion'] = self.df['Volume'] / self.df['Vol_SMA'].replace(0, 1)

    def calculate_momentum_shift(self):
        # Using a simple ROC (Rate of Change) for momentum
        self.df['Momentum'] = self.df['Close'] / self.df['Close'].shift(1) - 1

    def run_full_analysis(self):
        self.calculate_atr()
        self.calculate_trend_strength()
        self.calculate_volume_delta()
        self.calculate_momentum_shift()
        self.df.dropna(inplace=True)
        return self.df

    def get_latest_metrics(self) -> dict:
        if self.df.empty:
            raise ValueError("Not enough data to calculate quantitative metrics. DataFrame is empty after dropping NaNs.")
            
        latest = self.df.iloc[-1]
        
        # Determine Volatility Regime Based on ATR
        atr_pct = (latest['ATR'] / latest['Close']) * 100
        volatility_regime = "High" if atr_pct > 1.5 else ("Low" if atr_pct < 0.5 else "Normal")

        return {
            "atr": round(latest['ATR'], 4),
            "volatility_regime": volatility_regime,
            "adx": round(latest['ADX'], 2),
            "trend_strength": "Strong" if latest['ADX'] > 25 else "Weak",
            "volume_expansion_ratio": round(latest['Vol_Expansion'], 2),
            "momentum": round(latest['Momentum'], 4)
        }
