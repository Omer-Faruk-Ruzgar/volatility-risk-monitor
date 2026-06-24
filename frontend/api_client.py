import requests
import pandas as pd
import numpy as np
import streamlit as st
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform

BACKEND_URL = "http://localhost:8000"

def _get(path: str, params: dict = None):
    try:
        response = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            "Backend'e bağlanılamadı. "
            "`uvicorn backend.main:app --reload` komutunu çalıştırdığınızdan emin olun."
        )
    except requests.exceptions.Timeout:
        raise TimeoutError("Backend yanıt vermedi (30s). Sunucunun çalıştığından emin olun.")
    except requests.exceptions.HTTPError as e:
        # Backend JSON yerine HTML döndürebilir (500 hatalarında), güvenli parse et
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = e.response.text[:300] if e.response.text else str(e)
        raise ValueError(f"Backend hatası ({e.response.status_code}): {detail}")


# 1. get_assets() - Ticker listesi döner
def get_assets() -> list:
    """Kullanılabilir varlıkların listesini döner."""
    data = _get("/api/assets")
    return data.get("tickers", [])


# 2. get_returns(ticker) - Tarih/Değer çiftleri döner
def get_returns(ticker) -> pd.DataFrame:
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


# 5. get_risk_metrics(ticker, method) - VaR + ES zaman serileri döner
def get_risk_metrics(ticker, method="parametric") -> pd.DataFrame:
    """Risk Metrics sayfası için VaR ve ES serilerini döndürür."""
    data = _get("/api/var", params={"ticker": ticker, "method": method})
    returns_data = _get("/api/returns", params={"ticker": ticker})

    var_df = pd.DataFrame({
        "date":           pd.to_datetime(data["dates"]),
        "parametric_var": data["parametric_var"],
        "historical_var": data["historical_var"],
        "es":             data["es"],
    })

    ret_df = pd.DataFrame(returns_data["data"])
    ret_df["date"] = pd.to_datetime(ret_df["date"])
    ret_df = ret_df.rename(columns={"value": "return"})

    merged = pd.merge(ret_df, var_df, on="date")
    active_var = merged["parametric_var"] if method == "parametric" else merged["historical_var"]
    merged["is_breach"] = merged["return"] < active_var

    return merged, data.get("breaches", [])


# 6. get_breach_stats(df) - İhlal istatistikleri hesaplar
def get_breach_stats(df: pd.DataFrame) -> dict:
    """get_backtest() veya get_risk_metrics() sonucundan istatistikler hesaplar."""
    n = len(df)
    breach_col = "is_breach" if "is_breach" in df.columns else "breach"
    n_breaches = int(df[breach_col].sum())
    breach_rate = n_breaches / n if n > 0 else 0.0
    expected_rate = 0.05

    diff = abs(breach_rate - expected_rate)
    if diff < 0.015:
        status = "Geçti"
        status_color = "green"
    else:
        status = "Kaldı"
        status_color = "red"

    return {
        "n_observations": n,
        "breach_count":   n_breaches,
        "breach_rate":    breach_rate,
        "expected_rate":  expected_rate,
        "status":         status,
        "status_color":   status_color,
    }


# 7. get_portfolio_summary(tickers, weights) - Arkadaşlarının Canlı POST İsteği Mantığı
def get_portfolio_summary(tickers: list, weights: list) -> dict:
    """
    Seçilen hisseleri ve ağırlıkları backend'e gönderir.
    Tamamen canlı API'den gelen gerçek verileri kullanır.
    """
    url = f"{BACKEND_URL}/api/portfolio"
    payload = {
        "tickers": tickers,
        "weights": weights
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Backend'den gerçek portföy verileri alınamadı: {e}")


# 8. get_portfolio_analysis(tickers, weights) - Geriye dönük tam uyumluluk köprüsü
def get_portfolio_analysis(tickers: list, weights: list) -> dict:
    """app.py içerisindeki eski veya alternatif çağrıların kırılmasını önler."""
    return get_portfolio_summary(tickers, weights)


# 9. get_all_summaries() - Ana Sayfa Canlı Dashboard Özetleri
@st.cache_data(ttl=300)
def get_all_summaries():
    """11 ticker için volatilite özetlerini çeker ve durum analizi yapar."""
    tickers = get_assets()
    summaries = []
    
    for ticker in tickers:
        try:
            data = _get("/api/volatility", params={"ticker": ticker})
            garch_series = data.get("garch", [])
            
            if len(garch_series) >= 2:
                current_garch = garch_series[-1]
                previous_garch = garch_series[-2]
                avg_garch = sum(garch_series) / len(garch_series)
                
                delta = current_garch - previous_garch
                
                if current_garch > avg_garch * 1.5:
                    status = "Ekstrem"
                elif current_garch > avg_garch * 1.1:
                    status = "Yüksek"
                else:
                    status = "Normal"
                
                summaries.append({
                    "ticker": ticker,
                    "last_garch": current_garch,
                    "delta": delta,
                    "status": status
                })
        except Exception as e:
            print(f"Hata: {ticker} verisi alınamadı. {e}")
            
    return summaries


# 10. get_correlation_matrix(tickers) - Gelişmiş Hiyerarşik Kümeleme (Düzeltildi)
def get_correlation_matrix(tickers):
    """
    Varlıklar arasındaki gerçek korelasyonu hesaplar ve 
    Ward metodu ile sıralar. Terminaldeki ClusterWarning tamamen düzeltilmiştir.
    """
    all_returns = {}
    
    for ticker in tickers:
        try:
            df_ret = get_returns(ticker)
            all_returns[ticker] = df_ret.set_index("date")["log_return"]
        except:
            continue
            
    df_all = pd.DataFrame(all_returns).dropna()
    corr_matrix = df_all.corr()

    if corr_matrix.shape[0] > 1:
        dists = 1 - corr_matrix
        
        # ClusterWarning hatasını önlemek için matrisi simetrik ve yoğunlaştırılmış vektöre çeviriyoruz
        dists_clipped = np.clip(dists.values, 0, 2)
        np.fill_diagonal(dists_clipped, 0)
        condensed_dists = squareform(dists_clipped)
        
        # Hiyerarşik Kümeleme (Ward Metodu)
        linkage_matrix = linkage(condensed_dists, method='ward', optimal_ordering=True)
        new_order = [corr_matrix.columns[i] for i in leaves_list(linkage_matrix)]
        corr_matrix = corr_matrix.reindex(index=new_order, columns=new_order)
        
    return corr_matrix


# ---  ENTEGRE EDİLEN HABER & SENTIMENT ENDPOINT'LERİ ---

def get_news(ticker: str, limit: int = 10) -> dict:
    """Finnhub üzerinden seçili varlığın haber akışını ve duygu skorlarını döner."""
    return _get(f"/api/news/{ticker}", params={"limit": limit})


def get_sentiment_alert(ticker: str) -> dict:
    """Haber duygu skoru ve volatiliteyi birleştirerek kritik alarm durumunu döner."""
    return _get(f"/api/news/sentiment-alert/{ticker}")