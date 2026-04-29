"""
GARCH(1,1) volatility estimator using the arch library
Fits the model on historical log returns and outputs conditional volatility.

"""

import pandas as pd
import numpy as np
from arch import arch_model

TRADING_DAYS = 252

def fit_garch(returns:pd.Series, p: int = 1, q: int =1) -> object:
    """
    Ham return serisini alır, üzerine bir GARCH(1,1) modeli kurar ve eğitir. 

    Parametreler:
    retunrs: pd:series
        Günlük log returnleri (örnek olarak cleaner.py). NaNs verilerinin olmaması gerekiyor.
    p: int
        GARCH lag order - model kurulumunda 1 olarak atandı. Ama değiştirilip sonuçlar incelenebilir
    q: int 
        ARCH lag order

    Dönen değer:
    result: arch ModelResult object
        Fitted model sonucu. 

    
    """
    # arch Sonuçlarının daha stabil durması için 100 ile çarpılıyor.
    scaled = returns * 100

    model = arch_model(
        scaled,
        vol = "Garch",
        p=p,
        q=q,
        mean="Constant",
        dist="normal",
    )

    result = model.fit(disp = "off", show_warning= False)
    
    return result

def garch_volatility(returns: pd.Series, annualise: bool = True) -> pd.Series:
    """
    fit_garch'ı çağırır sonrasında modelin her gün için ürettiği koşulluğu volatiliteyi (conditional volatility) alır 
    ve bir pd.Series olarak döndürür. Yani "geçmişe dönük, her gün için volatilite neydi?" sorusunu yanıtlıyor.

    "Koşullu volatilite (conditional volatility)" ne demek?:
    GARCH, volatilitenin sabit olmadığını varsayar. Dün volatilite yüksekse bugün de yüksektir.
    Her gün için o güne kadarki bilgiyi koşul olarak kullanıp volatilite hesabı yapıyor.

    Parametreler:
    returns: pd.Series
        Günlük log return serileri. (DatetimeIndex)
    annualise: bool
        True dönerse günlük volatiliteyi sqrt(TRADING_DAYS) ile çarpma işlemi uyguluyoruz.

    Dönen değer:
    vol: pd:series
        return serisi indexine göre hesaplanan conditional volatility.
    """
    result = fit_garch(returns)
    cond_vol = result.conditional_volatility / 100  # tekrar yüzdeden desimale dönüştürüyoruz

    if annualise:
        cond_vol = cond_vol * np.sqrt(TRADING_DAYS)

    cond_vol.name = "garch_vol"
    return cond_vol

def garch_forecast(returns: pd.Series, horizon: int = 5) -> pd.DataFrame:
    """
    Önümüzdeki N günde volatilite tahmini ne olur? sorusunu yanıtlar. fit_garch'ı çağırır
    ama bu sefer geleceğe bakar.

    Parametreler:
    returns: pd.Series
    horizon: int
        Tahmin yürütülecek gün sayısı (iş günü). 5 günlük ayarlandı şimdilik.

    Dönen değer:
    forecast.df: pd.DataFrame
        Colonları:
            h.1 ... h.{horizon}: Her adımda ortaya çıkan tahmin
            vol_forecast: yıla yayılmış volatilite tahminleri
    """
    result = fit_garch(returns)
    forecasts = result.forecast(horizon = horizon, reindex = False)
    var_df = forecasts.variance / (100 ** 2)

    vol_forecast = np.sqrt(var_df.values.flatten()) * np.sqrt(TRADING_DAYS)
    forecast_df = pd.DataFrame(
        {
            **{f"h.{i+1}": var_df.values.flatten()[i] for i in range(horizon)},
            "vol_forecast": vol_forecast,
        }
    )
    return forecast_df

"""
SMOKE TESTİ:
çalıştırmak için: python -m models.garch
"""

if __name__ == "__main__":
    import yfinance as yf
 
    TARGET_TICKERS = [
        "XOM",   # ExxonMobil
        "CVX",   # Chevron
        "USO",   # WTI ham petrol ETF
        "BNO",   # Brent ham petrol ETF
        "XLE",   # Enerji sektoru ETF
        "UNG",   # Dogalgaz ETF
        "KSA",   # Suudi Arabistan ETF
        "GLD",   # Altin ETF
        "WEAT",  # Bugday ETF
        "TLT",   # Uzun vadeli tahvil ETF
        "SPY",   # S&P 500 baseline
    ]
 
    print("Downloading data for all tickers (2016-2026) ...\n")
    raw = yf.download(
        TARGET_TICKERS,
        start="2016-04-01",
        end="2026-04-01",
        progress=False,
        auto_adjust=True,
    )
    prices = raw["Close"]
 
    results_summary = []
 
    for ticker in TARGET_TICKERS:
        try:
            series = prices[ticker].dropna()
            log_ret = np.log(series / series.shift(1)).dropna()
            log_ret.name = ticker
 
            vol = garch_volatility(log_ret)
            fc = garch_forecast(log_ret, horizon=5)
 
            results_summary.append({
                "Ticker": ticker,
                "Obs": len(log_ret),
                "Avg GARCH Vol (ann.)": f"{vol.mean():.4f}",
                "Latest GARCH Vol":     f"{vol.iloc[-1]:.4f}",
                "1-day Forecast":       f"{fc['vol_forecast'].iloc[0]:.4f}",
                "Status": "OK",
            })
        except Exception as e:
            results_summary.append({
                "Ticker": ticker,
                "Obs": "-",
                "Avg GARCH Vol (ann.)": "-",
                "Latest GARCH Vol":     "-",
                "1-day Forecast":       "-",
                "Status": f"FAIL: {e}",
            })
 
    summary_df = pd.DataFrame(results_summary)
    print(summary_df.to_string(index=False))
    print(f"\nAnnualisation constant used: sqrt({TRADING_DAYS})")
    print("To change later: set TRADING_DAYS at the top of garch.py")

