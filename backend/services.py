# services.py, iş mantığını içeren katmandır.
# routers.py'deki endpoint'ler veriyi buradan alır.
# Bu dosya, Üye 1'in model fonksiyonlarını çağırır ve
# sonuçları API yanıtı olarak formatlayacaktir.
#
# Şu an için sadece iskelet kodu içeriyor.
# Üye 2'nin veri pipeline'ı hazır olduğunda burası genişletilecek.
import time

#  ÖNBELLEK SİSTEMİ 
_cache = {}        # Verileri saklayacağımız  sözlük
CACHE_TTL = 3600   # Veri ömrü  1 saat (saniye)




def list_tickers() -> list:
    # Sistemdeki mevcut hisse senedi listesini döndürür.
    # TODO: 2. haftada bu listeyi veritabanından çekeceğiz.
    return ['XOM', 'CVX', 'USO', 'BNO', 'XLE',
            'UNG', 'KSA', 'GLD', 'WEAT', 'TLT', 'SPY']

def get_var(ticker: str, method: str, confidence: float = 0.95) -> dict:
    """
    VaR (Value at Risk) ve Expected Shortfall hesaplar.

    ŞUANLIK MOCK: var.py hazır olmadığı için sabit değer döndürüyor.
    var.py hazır olunca Member 1 haber edecek. O zaman:
      1. Dosyanın başına şunu eklemek gerekiyor:  from models.var import compute_var
      2. Mock bloğu silip, yerine şunu yaz:  return compute_var(ticker, method, confidence)
    """

    # Mock data - yapı doğru, değerler geçici


    return {
        "ticker": ticker,
        "method": method,
        "confidence": confidence,
        "dates": ["2024-01-01", "2024-01-02"],
        "parametric_var": [-0.032, -0.032],
        "historical_var": [-0.032, -0.032],
        "es": [-0.048, -0.048],
        "breaches": ["2024-01-03"] 
    }


    """
    return {
        "ticker": ticker,
        "method": method,
        "confidence": confidence,
        "var": -0.032,
        "es": -0.048,
        "breaches": ["2024-01-03"], 
        }
        """
    
def get_volatility(ticker: str ) -> dict: #Mock data 
    cache_key = f"{ticker}_volatility"

    #  Önbellek kontrolu
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return data

    #  Mock data 
    sonuc = {
        "ticker": ticker,
        "dates": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
        "ewma": [0.012, 0.013, 0.014, 0.015],
        "garch": [0.011, 0.012, 0.015, 0.016],
        "forecast": [0.010, 0.011, 0.012, 0.013]
    }

    #  Önbelleğe kaydet
    _cache[cache_key] = (time.time(), sonuc)
    return sonuc
    
  
def get_cache_status() -> dict:
    # Önbellekte hangi hisseler var ve kaç tane

    return {
        "cached_keys": list(_cache.keys()),
        "total_items": len(_cache)
    }

def clear_cache() -> dict: #onbellegi  temizler
    
    _cache.clear()
    return {"message": "Onbellek basariyla temizlendi"}