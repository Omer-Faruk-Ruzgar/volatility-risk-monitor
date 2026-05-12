import requests
import pandas as pd
import numpy as np
import streamlit as st


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

# 4. get_risk_metrics(ticker, method) - VaR + ES zaman serileri döner
def get_risk_metrics(ticker, method="parametric") -> pd.DataFrame:
    """
    Risk Metrics sayfası için VaR ve ES serilerini döndürür.
    Kolonlar: date, parametric_var, historical_var, es, is_breach (bool)
    """
    data = _get("/api/var", params={"ticker": ticker, "method": method})
    returns_data = _get("/api/returns", params={"ticker": ticker})

    # VaR ve ES serileri
    var_df = pd.DataFrame({
        "date":           pd.to_datetime(data["dates"]),
        "parametric_var": data["parametric_var"],
        "historical_var": data["historical_var"],
        "es":             data["es"],
    })

    # Gerçek getiriler
    ret_df = pd.DataFrame(returns_data["data"])
    ret_df["date"] = pd.to_datetime(ret_df["date"])
    ret_df = ret_df.rename(columns={"value": "return"})

    merged = pd.merge(ret_df, var_df, on="date")

    # Seçilen yönteme göre ihlal işaretle
    active_var = merged["parametric_var"] if method == "parametric" else merged["historical_var"]
    merged["is_breach"] = merged["return"] < active_var

    return merged, data.get("breaches", [])

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


# ==========================================
# İKİNCİ İSSUE İÇİN GÜNCELLENEN FONKSİYON
# ==========================================
def get_portfolio_analysis(tickers: list, weights: list) -> dict:
    """
    Seçilen hisseleri ve portföy ağırlıklarını backend'e POST isteği ile gönderir.
    Backend hazır değilse veya bağlantı koparsa Mock (Sahte) veri döndürür.
    """
    url = f"{BACKEND_URL}/api/portfolio"
    
    # Backend'in beklediği Body (JSON) paketi
    payload = {
        "tickers": tickers,
        "weights": weights
    }
    
    try:
        # POST isteği atıyoruz, cevap vermesi için en fazla 5 saniye bekliyoruz
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status() 
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        # Backend bağlantısı başarısız olursa sistemin çökmemesi için Fallback (Yedek) mekanizması
        try:
            st.toast(f"Backend portföy analizi için henüz hazır değil. Mock veri kullanılıyor.", icon="⚠️")
        except:
            pass # Eğer terminalde vs test ediliyorsa streamlit çökmesin diye pass geçiyoruz
            
        # app.py'nin beklediği formatta sahte veri hazırlıyoruz
        mock_allocations = {ticker: float(weight * 100) for ticker, weight in zip(tickers, weights)}
        
        # Sahte korelasyon matrisi
        corr_matrix = pd.DataFrame(
            np.eye(len(tickers)),
            index=tickers,
            columns=tickers,
        )
        
        return {
            "allocation": mock_allocations,
            "var_95": -2.8,
            "volatility": 16.4,
            "diversification_effect": 0.9,
            "high_corr_pairs": "Yok",
            "VaR": -2.8,
            "ES": -3.5,
            "Diversification_Effect": 0.9,
            "Correlation_Matrix": corr_matrix,
        }
# ==========================================


#  ANA SAYFA DASHBOARD VERİSİ

@st.cache_data(ttl=300)  # Veriyi 300 saniye boyunca önbelleğe al
def get_all_summaries():
    """
    11 ticker için volatilite özetlerini çeker.
    Dashboard kartları için GARCH değerlerini ve değişimleri hesaplar.
    """
    tickers = get_assets()  # Backend'den tüm ticker listesini alma
    summaries = []
    
    # Kullanıcıya yüklenme bilgisini bir spinner ile gösterme
    for ticker in tickers:
        try:
            # Her ticker için volatilite verisini çek
            data = _get("/api/volatility", params={"ticker": ticker})
            garch_series = data.get("garch", [])
            
            if len(garch_series) >= 2:
                current_garch = garch_series[-1]
                previous_garch = garch_series[-2]
                avg_garch = sum(garch_series) / len(garch_series)
                
                # Değişim (Delta) hesapla
                delta = current_garch - previous_garch
                
                # Durum (Status) Belirle
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
            # Bir ticker'da hata olursa tüm dashboard çökmesin, o kartı atla
            print(f"Hata: {ticker} verisi alınamadı. {e}")
            
    return summaries

from scipy.cluster.hierarchy import linkage, leaves_list, optimal_leaf_ordering

def get_correlation_matrix(tickers):
    """
    Varlıklar arasındaki gerçek korelasyonu hesaplar ve 
    hiyerarşik kümeleme (Ward metodu) ile sıralar.
    """
    all_returns = {}
    
    # 1. Her ticker için verileri çek ve birleştir
    for ticker in tickers:
        try:
            df_ret = get_returns(ticker)
            all_returns[ticker] = df_ret.set_index("date")["log_return"]
        except:
            continue
            
    df_all = pd.DataFrame(all_returns).dropna()
    corr_matrix = df_all.corr()

    # 2. Hiyerarşik Kümeleme (Hudson & Thames - Ward Metodu)
    if len(tickers) > 1:
        # Uzaklık matrisi (1 - corr)
        dists = 1 - corr_matrix
        linkage_matrix = linkage(dists, method='ward', optimal_ordering=True)
        # Yeni sıralamayı al
        new_order = [corr_matrix.columns[i] for i in leaves_list(linkage_matrix)]
        corr_matrix = corr_matrix.reindex(index=new_order, columns=new_order)
        
    return corr_matrix