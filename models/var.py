"""VaR ve Expected Shortfall hesaplamaları."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

TRADING_DAYS = 252


def _clean_returns(returns: pd.Series) -> pd.Series:
    """Eksik değerleri atılmış sayısal getiri serisi döndürür."""
    if returns is None or len(returns) == 0:
        return pd.Series(dtype=float)
    return pd.Series(returns, dtype="float64").dropna()


def parametric_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Normal dağılım varsayımıyla tek dönemlik parametrik VaR hesaplar."""
    returns = _clean_returns(returns)
    if returns.empty:
        return np.nan

    mu = returns.mean()
    sigma = returns.std(ddof=1)
    z = stats.norm.ppf(1.0 - confidence)

    return float(mu + z * sigma)


def historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Geçmiş getiri dağılımından tek dönemlik tarihsel VaR hesaplar."""
    returns = _clean_returns(returns)
    if returns.empty:
        return np.nan

    return float(np.quantile(returns, 1.0 - confidence))


def parametric_es(returns: pd.Series, confidence: float = 0.95) -> float:
    """Normal dağılım varsayımıyla parametrik Expected Shortfall hesaplar."""
    returns = _clean_returns(returns)
    if returns.empty:
        return np.nan

    mu = returns.mean()
    sigma = returns.std(ddof=1)
    z = stats.norm.ppf(1.0 - confidence)

    return float(mu - sigma * stats.norm.pdf(z) / (1.0 - confidence))


def historical_es(returns: pd.Series, confidence: float = 0.95) -> float:
    """Tarihsel VaR eşiğinin altında kalan getirilerin ortalamasıyla ES hesaplar."""
    returns = _clean_returns(returns)
    if returns.empty:
        return np.nan

    threshold = historical_var(returns, confidence)
    tail_losses = returns[returns <= threshold]

    if tail_losses.empty:
        return threshold

    return float(tail_losses.mean())


def rolling_parametric_var(
    returns: pd.Series,
    confidence: float = 0.95,
    window: int = TRADING_DAYS,
) -> pd.Series:
    """Rolling pencereyle parametrik VaR serisi hesaplar."""
    rolling_var = returns.rolling(window=window).apply(
        lambda x: parametric_var(pd.Series(x), confidence),
        raw=False,
    )
    rolling_var.name = "parametric_var"
    return rolling_var


def rolling_historical_var(
    returns: pd.Series,
    confidence: float = 0.95,
    window: int = TRADING_DAYS,
) -> pd.Series:
    """Rolling pencereyle tarihsel VaR serisi hesaplar."""
    rolling_var = returns.rolling(window=window).apply(
        lambda x: historical_var(pd.Series(x), confidence),
        raw=False,
    )
    rolling_var.name = "historical_var"
    return rolling_var


def rolling_es(
    returns: pd.Series,
    confidence: float = 0.95,
    window: int = TRADING_DAYS,
    method: str = "historical",
) -> pd.Series:
    """Seçilen yönteme göre rolling Expected Shortfall serisi hesaplar."""
    if method not in {"parametric", "historical"}:
        raise ValueError("method must be 'parametric' or 'historical'")

    es_func = parametric_es if method == "parametric" else historical_es
    es_series = returns.rolling(window=window).apply(
        lambda x: es_func(pd.Series(x), confidence),
        raw=False,
    )
    es_series.name = f"es_{method}"
    return es_series


def find_breaches(
    returns: pd.Series,
    var_series: pd.Series,
) -> pd.DatetimeIndex:
    """Gerçekleşen getirinin VaR eşiğinin altına düştüğü tarihleri döndürür."""
    aligned = pd.concat([returns, var_series], axis=1).dropna()
    aligned.columns = ["returns", "var"]

    return aligned.index[aligned["returns"] < aligned["var"]]


def compute_var(
    returns: pd.Series,
    confidence: float = 0.95,
    method: str = "parametric",
    window: int = TRADING_DAYS,
) -> dict:
    """Seçilen yöntem için son VaR/ES değerlerini ve rolling serileri döndürür."""
    if method not in {"parametric", "historical"}:
        raise ValueError("method must be 'parametric' or 'historical'")

    returns = _clean_returns(returns)

    p_var_series = rolling_parametric_var(returns, confidence, window)
    h_var_series = rolling_historical_var(returns, confidence, window)
    es_series = rolling_es(returns, confidence, window, method)

    active_var = p_var_series if method == "parametric" else h_var_series
    breach_dates = find_breaches(returns, active_var)

    # Rolling hesaplamaların başındaki boş satırları birlikte temizliyoruz.
    valid_mask = p_var_series.notna() & h_var_series.notna() & es_series.notna()
    valid_returns = returns[valid_mask]
    p_var_valid = p_var_series[valid_mask]
    h_var_valid = h_var_series[valid_mask]
    es_valid = es_series[valid_mask]

    if valid_returns.empty:
        return {
            "var": np.nan,
            "es": np.nan,
            "dates": [],
            "parametric_var": [],
            "historical_var": [],
            "es_series": [],
            "breaches": [],
        }

    latest_var = p_var_valid.iloc[-1] if method == "parametric" else h_var_valid.iloc[-1]

    return {
        "var": float(latest_var),
        "es": float(es_valid.iloc[-1]),
        "dates": [date.strftime("%Y-%m-%d") for date in valid_returns.index],
        "parametric_var": p_var_valid.tolist(),
        "historical_var": h_var_valid.tolist(),
        "es_series": es_valid.tolist(),
        "breaches": [date.strftime("%Y-%m-%d") for date in breach_dates],
    }


if __name__ == "__main__":
    import yfinance as yf

    target_tickers = [
        "XOM", "CVX", "USO", "BNO", "XLE",
        "UNG", "KSA", "GLD", "WEAT", "TLT", "SPY",
    ]
    confidence = 0.95

    print("2016-2026 arası ticker verileri indiriliyor...\n")
    raw = yf.download(
        target_tickers,
        start="2016-04-01",
        end="2026-04-01",
        progress=False,
        auto_adjust=True,
    )
    prices = raw["Close"]

    rows = []
    for ticker in target_tickers:
        try:
            price_series = prices[ticker].dropna()
            log_returns = np.log(price_series / price_series.shift(1)).dropna()
            log_returns.name = ticker

            result = compute_var(
                log_returns,
                confidence=confidence,
                method="historical",
                window=TRADING_DAYS,
            )

            total_days = len(result["dates"])
            breach_count = len(result["breaches"])
            breach_rate = breach_count / total_days if total_days else 0.0

            rows.append({
                "Ticker": ticker,
                "Param VaR (95%)": f"{parametric_var(log_returns, confidence):.4f}",
                "Hist VaR (95%)": f"{historical_var(log_returns, confidence):.4f}",
                "Param ES": f"{parametric_es(log_returns, confidence):.4f}",
                "Hist ES": f"{historical_es(log_returns, confidence):.4f}",
                "Breaches": breach_count,
                "Breach Rate": f"{breach_rate:.3f}",
                "Near Target": "yes" if abs(breach_rate - 0.05) < 0.015 else "no",
            })
        except Exception as exc:
            rows.append({
                "Ticker": ticker,
                "Param VaR (95%)": f"FAIL: {exc}",
                "Hist VaR (95%)": "-",
                "Param ES": "-",
                "Hist ES": "-",
                "Breaches": "-",
                "Breach Rate": "-",
                "Near Target": "-",
            })

    summary = pd.DataFrame(rows)
    print(summary.to_string(index=False))
    print(f"\nGüven düzeyi: {confidence:.2f}")
    print(f"Rolling pencere: {TRADING_DAYS} işlem günü")
