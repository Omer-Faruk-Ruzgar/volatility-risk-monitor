# services.py, iş mantığını içeren katmandır.
# routers.py'deki endpoint'ler veriyi buradan alır.
# Bu dosya, Üye 1'in model fonksiyonlarını çağırır ve
# sonuçları API yanıtı olarak formatlayacaktir.
#
# Şu an için sadece iskelet kodu içeriyor.
# Üye 2'nin veri pipeline'ı hazır olduğunda burası genişletilecek.
import time

 
import pandas as pd
from sqlalchemy import create_engine
 
from models.ewma import compute_ewma
from models.garch import garch_volatility
from models.forecaster import train_forecaster, predict_vol
from models.var import compute_var as _compute_var

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
 
    if not db_path.exists():
        raise FileNotFoundError(
            "market.db bulunamadı. Önce `python -m data.pipeline` komutunu çalıştırın."
        )
 
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    df = pd.read_sql(
        "SELECT * FROM log_returns",
        engine,
        index_col="Date",
        parse_dates=["Date"],
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