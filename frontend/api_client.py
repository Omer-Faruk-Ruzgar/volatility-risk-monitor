import pandas as pd
import numpy as np
from datetime import datetime

BACKEND_URL = "http://localhost:8000"

# 1. get_assets() - Ticker listesi döner
def get_assets() -> list:
    """Kullanılabilir varlıkların listesini döner."""
    # TODO: Backend hazır olunca:
    # import requests
    # return requests.get(f"{BACKEND_URL}/assets").json()
    
    return ["AAPL", "MSFT", "TSLA", "BTC-USD", "THYAO", "EREGL"]

# 2. get_returns(ticker, period) - Tarih/Değer çiftleri döner
def get_returns(ticker, period="1Y") -> pd.DataFrame:
    """Hisse senedi getiri verilerini DataFrame olarak döner."""
    # TODO: Backend hazır olunca:
    # import requests
    # response = requests.get(f"{BACKEND_URL}/returns", params={"ticker": ticker})
    # return pd.DataFrame(response.json()) 

    # Mock Data Oluşturma
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=100, freq="B")
    values = np.random.normal(0.001, 0.02, 100).cumsum() 
    
    return pd.DataFrame({"date": dates, "log_return": values})

# 3. get_volatility(ticker) - EWMA, GARCH, Forecast döner
def get_volatility(ticker) -> pd.DataFrame:
    """Volatilite modellerinin sonuçlarını DataFrame olarak döner."""
    # TODO: Backend hazır olunca:
    # import requests
    # response = requests.get(f"{BACKEND_URL}/volatility", params={"ticker": ticker})
    # return pd.DataFrame(response.json())

    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=100, freq="B")
    
    return pd.DataFrame({
        "date": dates,
        "EWMA": np.abs(np.random.normal(0.02, 0.005, 100)),
        "GARCH": np.abs(np.random.normal(0.025, 0.005, 100)),
        "Forecast": np.abs(np.random.normal(0.028, 0.005, 100))
    })

# 4. get_backtest(ticker, method) - Backtest istatistikleri döner
def get_backtest(ticker, method="Historical") -> pd.DataFrame:
    """Backtest sonuçlarını ve VaR eşiklerini DataFrame olarak döner."""
    # TODO: Backend hazır olunca:
    # import requests
    # response = requests.get(f"{BACKEND_URL}/backtest", params={"ticker": ticker, "method": method})
    # return pd.DataFrame(response.json())

    np.random.seed(42) 
    dates = pd.date_range(end=datetime.now(), periods=100, freq="B")
    returns = np.random.normal(0, 0.02, 100)
    var_line = np.full(100, -0.032) # %95 güven aralığı VaR eşiği
    breach = returns < var_line

    return pd.DataFrame({
        "date": dates,
        "return": returns,
        "var": var_line,
        "breach": breach
    })


def get_portfolio_analysis(tickers, weights) -> dict:
    """Seçilen varlıklar ve ağırlıklara göre portföy analizi döner."""
    # TODO: Backend entegrasyonu
    # response = requests.post(f"{BACKEND_URL}/portfolio", json={"tickers": tickers, "weights": weights})
    
    # Mock Data: Gerçekçi portföy sonuçları
    return {
        "VaR": -0.0245,
        "ES": -0.0312,
        "Diversification_Effect": 0.005,
        "Correlation_Matrix": pd.DataFrame(
            np.random.uniform(0.3, 0.8, (len(tickers), len(tickers))),
            index=tickers,
            columns=tickers
        )
    }