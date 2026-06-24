# services.py, iş mantığını içeren katmandır.
# routers.py'deki endpoint'ler veriyi buradan alır.
# Bu dosya, Üye 1'in model fonksiyonlarını çağırır ve
# sonuçları API yanıtı olarak formatlayacaktir.
#
# Şu an için sadece iskelet kodu içeriyor.
# Üye 2'nin veri pipeline'ı hazır olduğunda burası genişletilecek.
import time
import os 
import requests
from pathlib import Path
from datetime  import datetime , timedelta 

import pandas as pd
from sqlalchemy import create_engine
import numpy as np
 
from models.ewma import compute_ewma
from models.garch import garch_volatility
from models.forecaster import train_forecaster, predict_vol
from models.var import compute_var as _compute_var
from models.var import compute_correlation, compute_portfolio_volatility
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from models.sentiment import score_region
from backend.geo_risk_data import RISK_REGIONS 

#  ÖNBELLEK SİSTEMİ 
_cache = {}        # Verileri saklayacağımız  sözlük
CACHE_TTL = 3600   # Veri ömrü  1 saat (saniye)

# Veritabanindan getiri verisi yükleme
def _load_returns(ticker: str) -> pd.Series:
    """
    market.db'den tek bir ticker'ın log getiri serisini yükler.
 
    Raises:
        FileNotFoundError - market.db henüz oluşturulmamışsa
        ValueError        - ticker veritabanında yoksa
    """
    db_path = Path(__file__).resolve().parent.parent / "data" / "market.db"
 
    if not db_path.exists() or db_path.stat().st_size == 0:
        raise FileNotFoundError(
            "market.db bulunamadı. Önce `python -m data.pipeline` komutunu çalıştırın."
        )
 
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    
    try:
        df = pd.read_sql(
            "SELECT * FROM log_returns",
            engine,
            index_col="Date",
            parse_dates=["Date"],
        )
    except Exception:
        raise FileNotFoundError(
            "market.db içinde 'log_returns' tablosu bulunamadı. "
            "Önce python -m data.pipeline komutunu çalıştırın."
        )

    if ticker not in df.columns:
        raise ValueError(
            f"'{ticker}' veritabanında bulunamadı. "
            f"Mevcut ticker'lar: {list(df.columns)}"
        )

    return df[ticker].dropna()
 

def get_returns(ticker: str) -> dict:
    """
    Bir ticker'ın tüm log getiri serisini döndürür. ReturnsResponse (routers.py içinde)
      şemasına uygun formattadır.
    """
    cache_key = f"{ticker}_returns"
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return data
 
    returns = _load_returns(ticker)
 
    output = {
        "ticker": ticker,
        "data": [
            {"date": d.strftime("%Y-%m-%d"), "value": float(v)}
            for d, v in returns.items()
        ],
    }
 
    _cache[cache_key] = (time.time(), output)
    return output
 

def list_tickers() -> list:
    # Sistemdeki mevcut hisse senedi listesini döndürür.
    # TODO: 2. haftada bu listeyi veritabanından çekeceğiz.
    return ['XOM', 'CVX', 'USO', 'BNO', 'XLE',
            'UNG', 'KSA', 'GLD', 'WEAT', 'TLT', 'SPY']

def get_var(ticker: str, method: str, confidence: float = 0.95) -> dict:
    """
    VaR (Value at Risk) ve Expected Shortfall hesaplar.
    models/var.py'deki compute_var fonksiyonunu kullanır.
    """
    cache_key = f"{ticker}_var_{method}_{confidence}"
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return data
 
    returns = _load_returns(ticker)
    result  = _compute_var(returns, confidence=confidence, method=method)
 
    output = {
        "ticker":ticker,
        "dates":result["dates"],
        "parametric_var": result["parametric_var"],
        "historical_var": result["historical_var"],
        "es":result["es_series"],
        "breaches": result["breaches"],
    }
 
    _cache[cache_key] = (time.time(), output)
    return output
    
def get_volatility(ticker: str ) -> dict: #Mock data 
    cache_key = f"{ticker}_volatility"

    #  Önbellek kontrolu
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return data
    returns = _load_returns(ticker)
 
    ewma_vol  = compute_ewma(returns, span=30)
    garch_vol = garch_volatility(returns)
 
    model, _, _ = train_forecaster(returns)
    xgb_vol = predict_vol(model, returns, annualise=True)
 
    # Tüm serileri ortak tarihlerde hizala
    import pandas as pd
    combined = pd.DataFrame({
        "ewma":ewma_vol,
        "garch": garch_vol,
        "forecast": xgb_vol,
    }).dropna()
 
    output = {
        "ticker": ticker,
        "dates":[d.strftime("%Y-%m-%d") for d in combined.index],
        "ewma": combined["ewma"].tolist(),
        "garch": combined["garch"].tolist(),
        "forecast": combined["forecast"].tolist(),
    }

    #  Önbelleğe kaydet
    _cache[cache_key] = (time.time(), output)
    return output
    
  
def get_cache_status() -> dict:
    # Önbellekte hangi hisseler var ve kaç tane

    return {
        "cached_keys": list(_cache.keys()),
        "total_items": len(_cache)
    }

def clear_cache() -> dict: #onbellegi  temizler
    
    _cache.clear()
    return {"message": "Onbellek basariyla temizlendi"}


# FINNHUB HABER FONKSİYONU
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")



def get_news(ticker: str, limit: int = 10) -> dict:
    # Finnhub API'den son 7 günlük hisse haberlerini çeker
    if not FINNHUB_API_KEY:
        print("UYARI: FINNHUB_API_KEY bulunamadı. Haberler yüklenemez.")
        return {"ticker": ticker, "news": [], "aggregate_sentiment": 0.0, "sentiment_trend": "stable"}

    # Tarihleri hesapla
    to_date = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Finnhub API hatası: {ticker} için HTTP {response.status_code}")
            return {"ticker": ticker, "news": [], "aggregate_sentiment": 0.0, "sentiment_trend": "stable"}
        if response.status_code == 200:
            all_news = response.json()
            news_list = all_news[:limit] 
            
            analyzer = SentimentIntensityAnalyzer() 
            formatted_news = []
            total_compound = 0.0 # Ortalama hesabı için toplam skoru tutma

            for item in news_list:
                headline = item.get("headline", "")
                
                
                sentiment_dict = analyzer.polarity_scores(headline)
                compound = sentiment_dict['compound']
                
                # Skora göre etiket üret
                if compound > 0.05:
                    label = "positive"
                elif compound < -0.05:
                    label = "negative"
                else:
                    label = "neutral"
                    
                total_compound += compound

                
                formatted_news.append({
                    "headline": headline,
                    "source": item.get("source"),
                    "datetime": item.get("datetime"),
                    "url": item.get("url"),
                    "compound_score": compound,
                    "sentiment_label": label
                })
            
            #Tüm haberlerin ortalama skorunu hesapla
            aggregate_sentiment = 0.0
            if len(formatted_news) > 0:
                aggregate_sentiment = total_compound / len(formatted_news)
            
            #  Ortalamaya göre trend belirle
            if aggregate_sentiment > 0.05:
                trend = "improving"
            elif aggregate_sentiment < -0.05:
                trend = "deteriorating"
            else:
                trend = "stable"

            #  Yeni şablona uygun yanıt döndür
            return {
                "ticker": ticker, 
                "news": formatted_news,
                "aggregate_sentiment": round(aggregate_sentiment, 3),
                "sentiment_trend": trend
            }
            
    except Exception as e:
        print(f"Haber çekme hatası: {e}")

    return {
        "ticker": ticker, 
        "news": [],
        "aggregate_sentiment": 0.0,
        "sentiment_trend": "stable"
    }


def get_portfolio_summary(tickers: list, weights: list) -> dict:
    from models.var import compute_correlation, compute_portfolio_volatility

    ticker_vars = {}
    ticker_vols = {}
    ticker_es   = {}

    for ticker in tickers:
        var_data = get_var(ticker, method="parametric")
        vol_data = get_volatility(ticker)
        ticker_vars[ticker] = var_data["parametric_var"][-1]
        ticker_es[ticker]   = var_data["es"][-1]
        ticker_vols[ticker] = vol_data["garch"][-1]

    # DataFrame oluştur — korelasyon ve portföy vol için gerekli
    returns_dict = {ticker: _load_returns(ticker) for ticker in tickers}
    returns_df   = pd.DataFrame(returns_dict).dropna()

    corr_matrix = compute_correlation(returns_df)
    port_vol    = compute_portfolio_volatility(returns_df, weights)

    # Ağırlıklı portföy VaR ve ES
    w             = np.array(weights)
    portfolio_var = float(w @ np.array([ticker_vars[t] for t in tickers]))
    portfolio_es  = float(w @ np.array([ticker_es[t]   for t in tickers]))

    # Çeşitlendirme etkisi
    weighted_avg_vol      = float(w @ np.array([ticker_vols[t] for t in tickers]))
    diversification_effect = weighted_avg_vol - port_vol

    # Yüksek korelasyonlu çiftler
    high_corr_pairs = []
    cols = corr_matrix.columns.tolist()
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            corr_val = corr_matrix.iloc[i, j]
            if abs(corr_val) >= 0.70:
                high_corr_pairs.append({
                    "a": cols[i],
                    "b": cols[j],
                    "corr": round(float(corr_val), 3)
                })

    return {
        "tickers":                tickers,
        "weights":                weights,
        "portfolio_var":          portfolio_var,
        "portfolio_es":           portfolio_es,
        "portfolio_vol":          port_vol,
        "diversification_effect": diversification_effect,
        "ticker_vars":            ticker_vars,
        "ticker_vols":            ticker_vols,
        "correlation_matrix":     corr_matrix.round(3).to_dict(),
        "high_corr_pairs":        high_corr_pairs,
    }

def run_stress_test(tickers: list, weights: list, start_date: str, end_date: str) -> dict:
    """
    Seçilen tarih aralığındaki tarihsel getiri şoklarını portföy ağırlıklarına uygular.
    Kümülatif kayıp, max drawdown, en kötü gün ve varlık katkılarını döndürür.
    """
    # Veri olan ticker'ları yükle (bazıları ilgili dönemde olmayabilir)
    returns_dict = {}
    valid_tickers = []
    valid_weights = []
    for ticker, weight in zip(tickers, weights):
        try:
            series = _load_returns(ticker)
            returns_dict[ticker] = series
            valid_tickers.append(ticker)
            valid_weights.append(weight)
        except Exception:
            continue

    if not valid_tickers:
        raise ValueError("Seçili varlıklar için veritabanında veri bulunamadı.")

    returns_df = pd.DataFrame(returns_dict).dropna()

    start = pd.to_datetime(start_date)
    end   = pd.to_datetime(end_date)
    crisis_df = returns_df[(returns_df.index >= start) & (returns_df.index <= end)]

    if crisis_df.empty:
        raise ValueError(
            f"Seçilen tarih aralığında ({start_date} → {end_date}) bu varlıklar için "
            "veri bulunamadı. Veritabanındaki tarih aralığını kontrol edin."
        )

    # Ağırlıkları normalleştir (dışarıda kalan ticker'lar için)
    w = np.array(valid_weights, dtype=float)
    w = w / w.sum()

    # Günlük portföy log getirileri
    port_returns = (crisis_df[valid_tickers] * w).sum(axis=1).values

    # Kümülatif değer serisi (1'den başlar)
    cum_vals = np.exp(np.cumsum(port_returns))
    cumulative_return = float(cum_vals[-1] - 1)

    # Maksimum drawdown
    rolling_max = np.maximum.accumulate(cum_vals)
    drawdowns = (cum_vals - rolling_max) / rolling_max
    max_drawdown = float(drawdowns.min())

    worst_day = float(port_returns.min())
    best_day  = float(port_returns.max())

    # Kriz dönemi %5 VaR (günlük)
    var_during_crisis = float(np.percentile(port_returns, 5))

    # Günlük veri (grafik için)
    daily_returns = [
        {
            "date":       d.strftime("%Y-%m-%d"),
            "return":     round(float(r) * 100, 4),
            "cumulative": round(float(cv - 1) * 100, 4),
        }
        for d, r, cv in zip(crisis_df.index, port_returns, cum_vals)
    ]

    # Varlık katkıları (ağırlıklı kümülatif getiri, yüzde)
    ticker_contributions = {}
    for i, ticker in enumerate(valid_tickers):
        ticker_cum = float(np.exp(np.sum(crisis_df[ticker].values)) - 1)
        ticker_contributions[ticker] = round(ticker_cum * w[i] * 100, 2)

    # Baz dönem karşılaştırması: kriz öncesi aynı uzunlukta pencere
    n_days = len(crisis_df)
    baseline_end_dt   = start - pd.Timedelta(days=1)
    baseline_start_dt = baseline_end_dt - pd.Timedelta(days=int(n_days * 1.7))
    baseline_df = returns_df[
        (returns_df.index >= baseline_start_dt) & (returns_df.index <= baseline_end_dt)
    ].iloc[-n_days:]

    baseline_cumulative = None
    if len(baseline_df) >= max(1, n_days // 2):
        base_returns = (baseline_df[valid_tickers] * w).sum(axis=1).values
        baseline_cumulative = round(float(np.exp(np.sum(base_returns)) - 1) * 100, 2)

    return {
        "tickers":                    valid_tickers,
        "weights":                    w.tolist(),
        "start_date":                 start_date,
        "end_date":                   end_date,
        "n_trading_days":             n_days,
        "portfolio_cumulative_return": round(cumulative_return * 100, 2),
        "max_drawdown":               round(max_drawdown * 100, 2),
        "worst_day":                  round(worst_day * 100, 2),
        "best_day":                   round(best_day * 100, 2),
        "var_during_crisis":          round(var_during_crisis * 100, 2),
        "daily_returns":              daily_returns,
        "ticker_contributions":       ticker_contributions,
        "baseline_cumulative_return": baseline_cumulative,
    }


def get_sentiment_alert(ticker: str) -> dict:
    #  Haber verilerini al Son 15 haber
    news_data = get_news(ticker, limit=15)
    
    # Negatif haberleri say ve ortalama skoru al
    negative_news_count = 0
    for item in news_data.get("news", []):
        if item.get("sentiment_label") == "negative":
            negative_news_count += 1
            
    aggregate_score = news_data.get("aggregate_sentiment", 0.0)

    # Volatilite Verisini Al GARCH Fonksiyonu
    vol_data = get_volatility(ticker)
    garch_series = vol_data.get("garch", [])
    
    if len(garch_series) > 0:
        current_vol = garch_series[-1] # En güncel GARCH değeri
        
        # Tarihi yüzdelik hesaplama 
        import pandas as pd
        vol_series_pd = pd.Series(garch_series)
        vol_percentile = (vol_series_pd <= current_vol).mean() * 100.0
    else:
        current_vol = 0.0
        vol_percentile = 0.0
    
    #Kurallar
    is_high_volatility = vol_percentile > 75.0
    has_many_negative_news = negative_news_count >= 3
    
    # Eğer hem volatilite yüksekse HEM DE negatif haber 3 veya daha fazlaysa alarm ver
    should_warn = bool(is_high_volatility and has_many_negative_news)
    
    # Sebep
    if should_warn:
        reason = "Kritik: Yüksek volatilite ve yoğun negatif haber akışı!"
    elif is_high_volatility:
        reason = "Uyarı: Volatilite yüksek ancak haber akışı stabil."
    elif has_many_negative_news:
        reason = "Uyarı: Negatif haberler artıyor, volatilite şu an normal."
    else:
        reason = "Piyasa koşulları normal."

    return {
        "ticker": ticker,
        "should_warn": should_warn,
        "reason": reason,
        "sentiment_score": aggregate_score,
        "current_vol": round(current_vol, 5),
        "vol_percentile": round(vol_percentile, 2),
        "negative_news_count": negative_news_count
    }


def _get_general_news(limit: int = 100) -> list:
    """
    Finnhub genel piyasa haberlerini cekmek icin kullanilan ozel fonksiyon.
    Ticker'a ozgu degil, genel haber akisi: /api/v1/news?category=general
    Tek API cagriyla tum bolge filtrelerinin kaynagini olusturur.
    """
    if not FINNHUB_API_KEY:
        return []
    url = (
        f"https://finnhub.io/api/v1/news"
        f"?category=general&minId=0&token={FINNHUB_API_KEY}"
    )
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Finnhub genel haber API hatasi: HTTP {response.status_code}")
            return []
        return response.json()[:limit]
    except Exception as e:
        print(f"Genel haber cekilemedi: {e}")
        return []


def get_geo_risk() -> dict:
    """
    Her risk bolgesi icin guncel gerilim skorunu hesaplar.
    Tek bir Finnhub genel haber cagrisindan keyword filtresiyle bolge bazli
    VADER skoru uretir. Cache TTL 7200 saniye (2 saat).
    """
    cache_key = "geo_risk_all"
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if time.time() - ts < 7200:
            return data

    all_news = _get_general_news(limit=100)
    all_headlines = [
        item.get("headline", "")
        for item in all_news
        if item.get("headline")
    ]

    results = {}
    for region_id, region in RISK_REGIONS.items():
        keywords_lower = [kw.lower() for kw in region["keywords"]]
        region_headlines = [
            h for h in all_headlines
            if any(kw in h.lower() for kw in keywords_lower)
        ]
        score = score_region(region_headlines)
        results[region_id] = {
            "label":         region["label"],
            "lat":           region["lat"],
            "lon":           region["lon"],
            "score":         score,
            "tickers":       region["tickers"],
            "headline_count": len(region_headlines),
        }

    _cache[cache_key] = (time.time(), results)
    return results
