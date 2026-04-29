import request
import pandas as pd
import numpy as np

BACKEND_URL = "http://localhost:8000"

def _get(path: str, params: dict = None):
    """Hata yönetimi ile GET isteği atar."""
    try:
        response = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            "Backend'e bağlanılamadı. "
            "`uvicorn backend.main:app --reload` komutunu çalıştırdığınızdan emin olun."
        )
    except requests.exceptions.HTTPError as e:
        raise ValueError(f"Backend hatası: {e.response.json().get('detail', str(e))}")

# 1. get_assets() - Ticker listesi döner
def get_assets() -> list:
    """Kullanılabilir varlıkların listesini döner."""
    data = _get("/api/assets")
    return data.get("tickers", [])

# 2. get_returns(ticker, period) - Tarih/Değer çiftleri döner
def get_returns(ticker, period="1Y") -> pd.DataFrame:
    """Hisse senedi getiri verilerini DataFrame olarak döner."""
    data = _get("/api/returns", params={"ticker": ticker})
    df = pd.DataFrame(data["data"])

    df["date"] = pd.to_datetime(df["date"])
    df = df.rename(columns={"value": "log_return"})
    return df
    
# 3. get_volatility(ticker) - EWMA, GARCH, Forecast döner
def get_volatility(ticker) -> pd.DataFrame:
    """Volatilite modellerinin sonuçlarını DataFrame olarak döner."""
    data = _get("/api/volatility", params={"ticker": ticker})
    df = pd.DataFrame({
        "date": pd.to_datetime(data["dates"]),
        "EWMA": data["ewma"],
        "GARCH": data["garch"],
        "Forecast": data["forecast"],
    })
    return df

# 4. get_backtest(ticker, method) - Backtest istatistikleri döner
def get_backtest(ticker, method="Historical") -> pd.DataFrame:
    """Backtest sonuçlarını ve VaR eşiklerini DataFrame olarak döner."""
    var_data     = _get("/api/var",     params={"ticker": ticker, "method": method})
    returns_data = _get("/api/returns", params={"ticker": ticker})
 
    var_df = pd.DataFrame({
        "date": pd.to_datetime(var_data["dates"]),
        "var":  var_data["parametric_var"] if method == "parametric"
                else var_data["historical_var"],
    })
 
    ret_df = pd.DataFrame(returns_data["data"])
    ret_df["date"] = pd.to_datetime(ret_df["date"])
    ret_df = ret_df.rename(columns={"value": "return"})
 
    merged = pd.merge(ret_df, var_df, on="date")
    merged["breach"] = merged["return"] < merged["var"]
    return merged


def get_portfolio_analysis(tickers, weights) -> dict:
    """Seçilen varlıklar ve ağırlıklara göre portföy analizi döner."""
    # Her ticker için VaR çek, ağırlıklı portföy VaR'ı hesapla
    import numpy as np
    portfolio_var = 0.0
    portfolio_es  = 0.0
 
    for ticker, weight in zip(tickers, weights):
        try:
            data = _get("/api/var", params={"ticker": ticker})
            if data["parametric_var"]:
                portfolio_var += weight * data["parametric_var"][-1]
                portfolio_es  += weight * data["es"][-1]
        except Exception:
            pass
 
    corr_matrix = pd.DataFrame(
        np.eye(len(tickers)),   # Gerçek korelasyon /portfolio endpoint'inde hesaplanacak
        index=tickers,
        columns=tickers,
    )
 
    return {
        "VaR": portfolio_var,
        "ES": portfolio_es,
        "Diversification_Effect": 0.0,
        "Correlation_Matrix": corr_matrix,
    }