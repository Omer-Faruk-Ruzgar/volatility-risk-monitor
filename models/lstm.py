"""LSTM tabanlı volatilite tahmin yardımcıları."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

try:
    import tensorflow as tf
    from tensorflow.keras.callbacks import EarlyStopping
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.optimizers import Adam
except ImportError as exc:
    raise ImportError(
        "TensorFlow bulunamadı. Yüklemek için:\n"
        "  pip install tensorflow\n"
        "GPU ortamı için:\n"
        "  pip install tensorflow[and-cuda]"
    ) from exc

TRADING_DAYS = 252
N_FEATURES = 4


def _build_feature_matrix(returns: pd.Series) -> pd.DataFrame:
    """Getiri serisinden LSTM için kullanılacak özellik matrisini üretir."""
    df = pd.DataFrame(index=returns.index)
    df["return"] = returns
    df["sq_return"] = returns**2

    # Günlük ölçekte kısa ve orta vadeli volatilite göstergeleri.
    df["rv_5"] = returns.rolling(5).std()
    df["rv_21"] = returns.rolling(21).std()

    return df.dropna()


def build_sequences(
    returns: pd.Series,
    lookback: int = 30,
) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    """LSTM için X, y ve tarih dizilerini oluşturur."""
    feat_df = _build_feature_matrix(returns)
    feat_values = feat_df.values.astype(np.float32)
    aligned_returns = returns.loc[feat_df.index]

    X_list, y_list, date_list = [], [], []

    for i in range(lookback, len(feat_values)):
        X_list.append(feat_values[i - lookback : i])
        y_list.append(abs(aligned_returns.iloc[i]))
        date_list.append(feat_df.index[i])

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.float32)
    dates = pd.DatetimeIndex(date_list)

    return X, y, dates


def _build_model(lookback: int, units: int = 64) -> Sequential:
    """İki katmanlı LSTM modelini kurar ve derler."""
    model = Sequential(
        [
            LSTM(
                units,
                input_shape=(lookback, N_FEATURES), return_sequences=True, name="lstm_1",
            ),
            Dropout(0.2, name="dropout_1"),
            LSTM(
                units // 2,
                return_sequences=False,
                name="lstm_2",
            ),
            Dropout(0.2, name="dropout_2"),
            Dense(1, activation="linear", name="output"),
        ]
    )

    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss="mse",
        metrics=["mae"],
    )
    return model


def train_lstm(
    returns: pd.Series,
    lookback: int = 30,
    epochs: int = 50,
    units: int = 64,
    test_size: float = 0.2,
    verbose: int = 0,
) -> tuple:
    """LSTM modelini kronolojik train/test ayrimiyla egitir."""
    X, y, _ = build_sequences(returns, lookback)

    if len(X) == 0:
        raise ValueError("LSTM egitimi icin yeterli veri yok.")

    split_idx = int(len(X) * (1.0 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    if len(X_train) == 0 or len(X_test) == 0:
        raise ValueError("Train/test ayrimi için yeterli sekans olusmadi.")

    model = _build_model(lookback=lookback, units=units)

    # Validation kaybı uzun süre iyileşmezse eğitimi erken durdurur.
    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=10,
        restore_best_weights=True,
        verbose=0,
    )

    history = model.fit(
        X_train,
        y_train,
        validation_split=0.1,
        epochs=epochs,
        batch_size=32,
        callbacks=[early_stop],
        shuffle=False,
        verbose=verbose,
    )

    train_preds = model.predict(X_train, verbose=0).flatten()
    test_preds = model.predict(X_test, verbose=0).flatten()

    rmse_train = float(np.sqrt(np.mean((y_train - train_preds) ** 2)))
    rmse_test = float(np.sqrt(np.mean((y_test - test_preds) ** 2)))

    # Basit referans: bir önceki günün mutlak getirisi.
    naive_preds = np.abs(returns.values)[-(len(y_test) + 1) : -1]
    naive_preds = naive_preds[-len(y_test) :]
    rmse_naive = float(np.sqrt(np.mean((y_test - naive_preds) ** 2)))

    improvement = (rmse_naive - rmse_test) / rmse_naive * 100 if rmse_naive else 0.0

    metrics = {
        "rmse_train": rmse_train,
        "rmse_test": rmse_test,
        "rmse_naive": rmse_naive,
        "improvement": improvement,
        "n_params": model.count_params(),
        "epochs_run": len(history.history["loss"]),
    }

    return model, metrics, history
  

def predict_lstm(
    model,
    returns: pd.Series,
    lookback: int = 30,
    annualise: bool = True,
) -> pd.Series:
    """Tüm seri için LSTM volatilite tahmini üretir."""
    X, _, dates = build_sequences(returns, lookback)

    if len(X) == 0:
        return pd.Series(dtype=float, name="lstm_vol_forecast")

    preds = model.predict(X, verbose=0).flatten()
    vol_series = pd.Series(preds, index=dates, name="lstm_vol_forecast")

    if annualise:
        vol_series = vol_series * np.sqrt(TRADING_DAYS)

    return vol_series


def predict_next_day_lstm(
    model,
    returns: pd.Series,
    lookback: int = 30,
    annualise: bool = True,
) -> float:
    """Bir sonraki işlem günü için tek volatilite tahmini döndürür."""
    feat_df = _build_feature_matrix(returns)

    if len(feat_df) < lookback:
        raise ValueError(
            f"Yeterli veri yok. En az {lookback + 21} gunluk getiri serisi gerekli."
        )

    X_latest = feat_df.values[-lookback:].astype(np.float32)
    X_latest = X_latest[np.newaxis, :, :]

    pred = float(model.predict(X_latest, verbose=0)[0, 0])

    if annualise:
        pred *= np.sqrt(TRADING_DAYS)

    return pred


if __name__ == "__main__":
    import yfinance as yf

    from models.forecaster import train_forecaster

    # TensorFlow çıktılarını test çalışması sırasında sessizleştirir.
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    tf.get_logger().setLevel("ERROR")

    target_tickers = [
        "XOM", "CVX", "USO", "BNO","XLE",
        "UNG","KSA","GLD","WEAT","TLT","SPY",
    ]
    lookback = 30
    epochs = 50

    print("Ticker verileri indiriliyor (2016-2026)...\n")
    raw = yf.download(
        target_tickers,
        start="2016-04-01",
        end="2026-04-01",
        progress=False,
        auto_adjust=True,
    )
    prices = raw["Close"]

    results = []

    for ticker in target_tickers:
        print(f"{ticker} eğitiliyor...", end=" ", flush=True)

        try:
            price_series = prices[ticker].dropna()
            log_returns = np.log(price_series / price_series.shift(1)).dropna()
            log_returns.name = ticker

            lstm_model, lstm_metrics, _ = train_lstm(
                log_returns,
                lookback=lookback,
                epochs=epochs,
                units=64,
                verbose=0,
            )
            lstm_next_day = predict_next_day_lstm(lstm_model, log_returns, lookback)

            _, xgb_metrics, _ = train_forecaster(log_returns)

            print(
                f"LSTM RMSE={lstm_metrics['rmse_test']:.6f} | "
                f"XGB RMSE={xgb_metrics['rmse_test']:.6f} | "
                f"Epochs={lstm_metrics['epochs_run']}"
            )

            results.append(
                {
                    "ticker": ticker,
                    "lstm_rmse_test": round(lstm_metrics["rmse_test"], 6),
                    "xgb_rmse_test": round(xgb_metrics["rmse_test"], 6),
                    "naive_rmse": round(lstm_metrics["rmse_naive"], 6),
                    "lstm_improvement": f"{lstm_metrics['improvement']:.1f}%",
                    "xgb_improvement": f"{xgb_metrics['improvement']:.1f}%",
                    "lstm_beats_xgb": lstm_metrics["rmse_test"] < xgb_metrics["rmse_test"],
                    "lstm_next_day_vol": round(lstm_next_day, 4),
                    "epochs_run": lstm_metrics["epochs_run"],
                    "n_params": lstm_metrics["n_params"],
                }
            )

        except Exception as exc:
            print(f"HATA: {exc}")
            results.append(
                {
                    "ticker": ticker,
                    "lstm_rmse_test": None,
                    "xgb_rmse_test": None,
                    "naive_rmse": None,
                    "lstm_improvement": None,
                    "xgb_improvement": None,
                    "lstm_beats_xgb": None,
                    "lstm_next_day_vol": None,
                    "epochs_run": None,
                    "n_params": None,
                }
            )

    summary_df = pd.DataFrame(results)

    print("\n" + "=" * 80)
    print("LSTM vs XGBoost karşılaştırması")
    print("=" * 80)
    print(summary_df.to_string(index=False))

    valid = summary_df.dropna(subset=["lstm_rmse_test", "xgb_rmse_test"])
    lstm_wins = valid["lstm_beats_xgb"].sum()

    print(f"\nLSTM, {len(valid)} tickerdan {lstm_wins} tanesinde XGBoost'u geçti.")
    print(f"Yilliklandirma sabiti: sqrt({TRADING_DAYS})")
    print(f"Lookback: {lookback} gün | Max epochs: {epochs}")

    os.makedirs("experiments", exist_ok=True)
    csv_path = "experiments/lstm_results.csv"
    summary_df.to_csv(csv_path, index=False)
    print(f"\nSonuçlar kaydedildi: {csv_path}")
