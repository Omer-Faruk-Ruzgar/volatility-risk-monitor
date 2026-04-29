"""
XGBoost-based next-day volatility forecaster.
Uses lagged returns and rolling volatility as features.
"""

import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# Annualisation constant - keep in sync with garch.py
# Change only here (and in garch.py) if you update the assumption later
TRADING_DAYS = 252


 
# Feature Engineering

def build_features(returns: pd.Series, lags: int = 5) -> pd.DataFrame:
    """
    Bir log-getiri (log-return) serisinden özellik (feature) matrisi oluşturur.

    Oluşturulan özellikler:
        ret_lag_1 ... ret_lag_{lags}       : gecikmeli getiriler (lagged returns)
        sq_ret_lag_1 ... sq_ret_lag_{lags} : squared lagged returns (volatilite şokları için bir proxy)
        rolling_vol_5          : 5 günlük hareketli standard sapma - rolling std
        rolling_vol_21         : 21 günlük rolling std
        rolling_vol_63         : 63 günlük rolling std (yaklaşık 3 aylık)
        target                 : bir sonraki günün mutlak return'ü (gerçekleştirilmiş vol için proxy)

    Parametreler
    returns : pd.Series
        Günlük log getiriler. İndeks mutlaka DatetimeIndex olmalıdır.
    lags : int
        Kaç adet gecikmeli getiri özelliği oluşturulacağı.

    Returns
    df : pd.DataFrame
        F'target' sütununu içeren özellik matrisi. NaN içeren satırlar çıkarılmıştır.
    """
    df = pd.DataFrame(index=returns.index)

    for i in range(1, lags + 1):
        df[f"ret_lag_{i}"] = returns.shift(i)

    for i in range(1, lags + 1):
        df[f"sq_ret_lag_{i}"] = (returns.shift(i)) ** 2

    for window in [5, 21, 63]:
        df[f"rolling_vol_{window}"] = returns.rolling(window).std()

    # Bir sonraki günün mutlak getirisi (|return|), 
    # gerçekleşmiş volatilite (realised volatility) için bir yaklaşım (proxy) olarak kullanılır.
    df["target"] = returns.rolling(5).std().shift(-5) * np.sqrt(252)

    df.dropna(inplace=True)
    return df


# TRAINING

def train_forecaster(
    returns: pd.Series,
    lags: int = 5,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple:
    """
    Bir sonraki günün volatilitesini tahmin etmek için bir XGBoost modeli eğitir.

    Parametreler
    returns : pd.Series
        Günlük log getiriler.
    lags : int
        Gecikmeli özelliklerin sayısı. Varsayılan değer 5.
    test_size : float
        Değerlendirme için ayrılacak veri oranı. Varsayılan değer 0.2.
    random_state : int
        Tekrarlanabilirlik için kullanılan rastgelelik değeri.

    Dönen değer
    model : XGBRegressor
    metrics : dict
        rmse_train, rmse_test, rmse_naive, improvement (%), feature_names
    df : pd.DataFrame
        Tam özellik matrisi (notebook içindeki grafikler için).
    """
    df = build_features(returns, lags=lags)

    feature_cols = [c for c in df.columns if c != "target"]
    X = df[feature_cols].values
    y = df["target"].values

    # Time-series aware split - Zamansal sıralama korunur, veri karıştırılmaz (shuffle yapılmaz).
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    model = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=random_state,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_train, y_train)

    rmse_train = mean_squared_error(y_train, model.predict(X_train)) ** 0.5
    rmse_test  = mean_squared_error(y_test,  model.predict(X_test))  ** 0.5

    # Naive (basit) referans model:
    # Dünün getirisi, bugünün tahmini olarak kullanılır.
    naive_pred = df["ret_lag_1"].iloc[split_idx:].abs().values
    rmse_naive = mean_squared_error(y_test, naive_pred) ** 0.5

    improvement = (rmse_naive - rmse_test) / rmse_naive * 100

    metrics = {
        "rmse_train": rmse_train,
        "rmse_test": rmse_test,
        "rmse_naive": rmse_naive,
        "improvement": improvement,
        "feature_names": feature_cols,
    }

    return model, metrics, df


# TAHMIN BOLUMU

def predict_vol(
    model: XGBRegressor,
    returns: pd.Series,
    lags: int = 5,
    annualise: bool = True,
) -> pd.Series:
    """
    Tüm getiri serisi için in-sample volatilite tahminleri üretir.

    Parametreler

    model : XGBRegressor
        train_forecaster() fonksiyonundan elde edilen eğitilmiş model.
    returns : pd.Series
        Getiri serisi (eğitimde kullanılan seriyle aynı olabilir ya da tahmin için yeni bir seri olabilir).
    lags : int
        Eğitim sırasında kullanılan değerle aynı olmalıdır. Varsayılan değer 5.
    annualise : bool
        Günlük tahmini sqrt(TRADING_DAYS) ile çarparak yıllıklandırır. Varsayılan değer True.

    Dönen değer:
    vol_forecast : pd.Series
    """

    df = build_features(returns, lags=lags)
    feature_cols = [c for c in df.columns if c != "target"]
    preds = model.predict(df[feature_cols].values)

    vol_forecast = pd.Series(preds, index=df.index, name="xgb_vol_forecast")

    if annualise:
        vol_forecast = vol_forecast * np.sqrt(TRADING_DAYS)

    return vol_forecast


def predict_next_day(
    model: XGBRegressor,
    returns: pd.Series,
    lags: int = 5,
    annualise: bool = True,
) -> float:
    """"
    BİR SONrakii işlem günü için volatilite tahmini yapar (tek bir değer).
    Member 3'ün services.py dosyasında /volatility endpoint'i için kullanılır.

    Parametreler:
    model : XGBRegressor
        Eğitilmiş model.
    returns : pd.Series
        Son dönem getiri serisi (hareketli özelliklerin hesaplanabilmesi için en az 63 satır gerekli).
    lags : int
        Eğitimde kullanılan değerle aynı olmalıdır. Varsayılan değer 5.
    annualise : bool
        Varsayılan değer True'dur.

    Dönen değer:
    float
        Bir sonraki gün için tek bir volatilite tahmini değeri.
"""
    df = build_features(returns, lags=lags)
    feature_cols = [c for c in df.columns if c != "target"]
    X_latest = df[feature_cols].iloc[[-1]].values
    pred = float(model.predict(X_latest)[0])

    if annualise:
        pred = pred * np.sqrt(TRADING_DAYS)

    return pred



# Smoke test -
# Çalıştırmak için: python -m models.forecaster
# Trains and evaluates on every project ticker, prints summary table.
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

            model, metrics, _ = train_forecaster(log_ret)
            next_day = predict_next_day(model, log_ret)

            beat_target = metrics["improvement"] > 10

            results_summary.append({
                "Ticker":        ticker,
                "Obs":           len(log_ret),
                "RMSE Test":     f"{metrics['rmse_test']:.6f}",
                "RMSE Naive":    f"{metrics['rmse_naive']:.6f}",
                "Improvement":   f"{metrics['improvement']:.1f}%",
                "Next-day Vol":  f"{next_day:.4f}",
                "Beats >10%":    "YES" if beat_target else "NO",
            })
        except Exception as e:
            results_summary.append({
                "Ticker":       ticker,
                "Obs":          "-",
                "RMSE Test":    "-",
                "RMSE Naive":   "-",
                "Improvement":  "-",
                "Next-day Vol": "-",
                "Beats >10%":   f"FAIL: {e}",
            })

    summary_df = pd.DataFrame(results_summary)
    print(summary_df.to_string(index=False))
    print(f"\nAnnualisation constant used: sqrt({TRADING_DAYS})")
    print("To change later: set TRADING_DAYS at the top of forecaster.py (and garch.py)")