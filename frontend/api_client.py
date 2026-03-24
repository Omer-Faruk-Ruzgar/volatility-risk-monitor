import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 1. get_assets() - Ticker listesi döner
def get_assets():
    """Kullanıcının seçebileceği sembol listesini döner."""
    return ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "AAPL", "TSLA"]

# 2. get_returns(ticker, period) - Tarih/Değer çiftleri döner
def get_returns(ticker, period="1Y"):
    """Seçilen periyotta fiyat/getiri verisi döner."""
    dates = pd.date_range(end=datetime.now(), periods=100).strftime('%Y-%m-%d').tolist()
    values = np.cumsum(np.random.normal(0, 0.02, 100)).tolist() # Sahte getiri verisi
    return {"dates": dates, "values": values}

# 3. get_volatility(ticker) - EWMA, GARCH, Forecast döner
def get_volatility(ticker):
    """Volatilite modellerinin sonuçlarını döner."""
    return {
        "EWMA": 0.025,
        "GARCH": 0.028,
        "Forecast": 0.030
    }

# 4. get_backtest(ticker, method) - Backtest istatistikleri döner
def get_backtest(ticker, method="Historical"):
    """Backtest sonuçlarını ve istatistiklerini döner."""
    return {
        "Total Return": "%15.4",
        "Max Drawdown": "-%5.2",
        "Sharpe Ratio": 1.95,
        "Success": True
    }
