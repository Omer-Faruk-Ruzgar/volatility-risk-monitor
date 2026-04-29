"""VaR modelleri için backtesting yardımcı fonksiyonları."""

import numpy as np
import pandas as pd
from scipy import stats

from __future__ import annotations


TRADING_DAYS = 252

def _align_returns_and_var(returns: pd.Series, var_series: pd.Series) -> pd.DataFrame:
    """Getiri ve VaR serilerini aynı tarihler üzerinde hizalar."""
    aligned = pd.concat([returns, var_series], axis=1).dropna()
    aligned.columns = ["returns", "var"]
    return aligned


def count_breaches(returns: pd.Series, var_series: pd.Series) -> int:
    """Gerçekleşen getirinin VaR eşiğinin altında kaldığı günleri sayar."""
    aligned = _align_returns_and_var(returns, var_series)
    return int((aligned["returns"] < aligned["var"]).sum())


def breach_rate(returns: pd.Series, var_series: pd.Series) -> float:
    """VaR ihlali gerçekleşen gözlemlerin toplam gözlemlere oranını hesaplar."""
    aligned = _align_returns_and_var(returns, var_series)

    if aligned.empty:
        return 0.0

    return float((aligned["returns"] < aligned["var"]).mean())


def kupiec_pof_test(
    n_breaches: int,
    n_observations: int,
    confidence: float = 0.95,
) -> dict:
    """Run Kupiec's Proportion of Failures test for VaR exceptions."""
    if n_observations <= 0:
        return {
            "lr_statistic": 0.0,
            "p_value": 1.0,
            "result": "fail",
            "interpretation": "Geçerli gözlem olmadığı için test çalıştırılamadı.",
        }

    expected_rate = 1.0 - confidence
    observed_rate = n_breaches / n_observations

    # Log hesabında 0 ve 1 uç değerleri sorun çıkarabileceği için oranı sınırlıyoruz.
    eps = 1e-10
    observed_rate = np.clip(observed_rate, eps, 1.0 - eps)

    lr_statistic = 2.0 * (
        n_breaches * np.log(observed_rate / expected_rate)
        + (n_observations - n_breaches)
        * np.log((1.0 - observed_rate) / (1.0 - expected_rate))
    )
    p_value = float(1.0 - stats.chi2.cdf(lr_statistic, df=1))
    passed = p_value > 0.05

    if passed:
        interpretation = (
            f"Geçti: p={p_value:.4f}. İhlal oranı "
            f"({n_breaches}/{n_observations} = {observed_rate:.2%}) beklenen oranla "
            f"({expected_rate:.2%}) uyumlu görünüyor."
        )
    else:
        direction = "üstünde" if observed_rate > expected_rate else "altında"
        interpretation = (
            f"Kaldı: p={p_value:.4f}. İhlal oranı "
            f"({n_breaches}/{n_observations} = {observed_rate:.2%}) beklenen oranın "
            f"({expected_rate:.2%}) {direction}."
        )

    return {
        "lr_statistic": float(lr_statistic),
        "p_value": p_value,
        "result": "pass" if passed else "fail",
        "interpretation": interpretation,
    }


def vol_to_var(
    vol_series: pd.Series,
    returns: pd.Series | None = None,
    confidence: float = 0.95,
) -> pd.Series:
    """Yıllıklandırılmış volatilite serisini günlük parametrik VaR serisine çevirir."""
    daily_vol = vol_series / np.sqrt(TRADING_DAYS)
    z_score = stats.norm.ppf(1.0 - confidence)

    var_series = z_score * daily_vol
    var_series.name = "var_from_vol"
    return var_series


def run_backtest(
    returns: pd.Series,
    vol_series: pd.Series,
    confidence: float = 0.95,
    method: str = "ewma",
) -> dict:
    """Volatilite serisini VaR'a çevirip seçilen model için backtest çalıştırır."""
    var_series = vol_to_var(vol_series, returns, confidence)
    aligned = _align_returns_and_var(returns, var_series)

    if aligned.empty:
        return {
            "method": method,
            "breach_count": 0,
            "breach_rate": 0.0,
            "kupiec_statistic": 0.0,
            "kupiec_p_value": 1.0,
            "result": "fail",
        }

    n_breaches = int((aligned["returns"] < aligned["var"]).sum())
    b_rate = float(n_breaches / len(aligned))
    kupiec = kupiec_pof_test(n_breaches, len(aligned), confidence)

    return {
        "method": method,
        "breach_count": n_breaches,
        "breach_rate": b_rate,
        "kupiec_statistic": kupiec["lr_statistic"],
        "kupiec_p_value": kupiec["p_value"],
        "result": kupiec["result"],
        "_interpretation": kupiec["interpretation"],
    }


def compare_methods(
    returns: pd.Series,
    vol_dict: dict[str, pd.Series],
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Birden fazla volatilite modelinin VaR backtest sonuçlarını karşılaştırır."""
    rows = []

    for method_name, vol_series in vol_dict.items():
        result = run_backtest(returns, vol_series, confidence, method=method_name)
        rows.append(
            {
                "method": method_name,
                "breach_count": result["breach_count"],
                "breach_rate": result["breach_rate"],
                "kupiec_lr": result["kupiec_statistic"],
                "kupiec_p_value": result["kupiec_p_value"],
                "result": result["result"],
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    import yfinance as yf

    from models.ewma import compute_ewma

    target_tickers = [
        "XOM", "CVX", "USO", "BNO", "XLE",
        "UNG", "KSA", "GLD", "WEAT", "TLT", "SPY",
    ]
    confidence = 0.95

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
        try:
            series = prices[ticker].dropna()
            log_returns = np.log(series / series.shift(1)).dropna()
            log_returns.name = ticker

            ewma_vol = compute_ewma(log_returns, span=30)
            result = run_backtest(log_returns, ewma_vol, confidence, method="ewma")

            results.append(
                {
                    "ticker": ticker,
                    "breach_count": result["breach_count"],
                    "breach_rate": round(result["breach_rate"], 4),
                    "target_rate_ok": abs(result["breach_rate"] - 0.05) < 0.015,
                    "kupiec_lr": round(result["kupiec_statistic"], 4),
                    "kupiec_p_value": round(result["kupiec_p_value"], 4),
                    "result": result["result"],
                }
            )
        except Exception as exc:
            results.append(
                {
                    "ticker": ticker,
                    "breach_count": None,
                    "breach_rate": None,
                    "target_rate_ok": None,
                    "kupiec_lr": None,
                    "kupiec_p_value": None,
                    "result": f"error: {exc}",
                }
            )

    summary = pd.DataFrame(results)
    print(summary.to_string(index=False))

    spy_result = summary[summary["ticker"] == "SPY"]
    if not spy_result.empty:
        print("\nSPY kontrolü")
        print(f"breach_rate: {spy_result['breach_rate'].values[0]}")
        print(f"kupiec_p_value: {spy_result['kupiec_p_value'].values[0]}")
        print(f"result: {spy_result['result'].values[0]}")

    print("\n" + "-" * 60)
    print("Yontemlerin karsilastirilmasi (SPY icin)")
    print("-" * 60)

    from models.garch import garch_volatility
    from models.forecaster import train_forecaster, predict_vol
    spy_prices = prices["SPY"].dropna()
    spy_returns = np.log(spy_prices / spy_prices.shift(1)).dropna()
    spy_returns.name = "SPY"

    ewma_vol = compute_ewma(spy_returns, span = 30)
    garch_vol = garch_volatility(spy_returns)
    model, _, _ = train_forecaster(spy_returns)
    xgb_vol = predict_vol(model, spy_returns)

    vol_dict = {
        "ewma": ewma_vol,
        "garch": garch_vol,
        "forecast": xgb_vol,

    }

    comparison_df = compare_methods(spy_returns, vol_dict, confidence)
    print(comparison_df.to_string(index=False))
