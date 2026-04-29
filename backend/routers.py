# routers.py, tüm API endpoint'lerini içeren dosyadır.
# Bir endpoint, frontend'in veri almak için çağırdığı bir URL adresidir.
# Örnek: GET /api/assets : mevcut hisse senedi listesini döndürür.
# 
# Bu dosya main.py'e import edilir ve /api prefix'i ile kaydedilir.
# Yani burada yazdığın @router.get('/assets') aslında /api/assets olur.

from fastapi import APIRouter, HTTPException

from backend.schemas import VaRResponse , VolatilityResponse, ReturnResponse  # schemas.py'da tanımladığımız modeller
from backend import services

# APIRouter örneği oluşturuyoruz.
# Bu, endpoint'leri main.py'den ayrı bir dosyada tanımlamamızı sağlar.
# Kodun daha düzenli ve okunabilir olması için böyle yapıyoruz.
router= APIRouter()

# /assets Endpoint 
# Bu endpoint, sistemdeki mevcut hisse senedi listesini döndürür.
# Frontend bu listeyi kullanarak kullanıcıya hisse senedi seçtirtr.
# Şu an için liste sabit kodlanmıştır (hardcoded).
# 2. haftada Üye 2'nin veritabanına bağlanacağız.

@router.get('/assets')
def get_assets():
    # TODO: market.db'den cekezegiz
    return {'tickers': ['XOM', 'CVX', 'USO', 'BNO', 'XLE',
            'UNG', 'KSA', 'GLD', 'WEAT', 'TLT', 'SPY']}

@router.get("/returns", response_model=ReturnsResponse)
def returns_endpoint(ticker: str):
    """Bir ticker'ın tüm log getiri serisini döndürür."""
    try:
        return services.get_returns(ticker)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/var", response_model=VaRResponse)
def var_endpoint(
    ticker: str,
    method: str = "parametric",   # "parametric" veya "historical"
    confidence: float = 0.95,
):
    """
    Verilen ticker için VaR döndürür.
    - method: 'parametric' (normal dağılım varsayımı) veya 'historical' (gerçek dönüş verisi)
    """
    try:
        return services.get_var(ticker, method, confidence)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/es", response_model=VaRResponse)
def es_endpoint(
    ticker: str,
    method: str = "parametric",
    confidence: float = 0.95,
):
    """
    Verilen ticker için Expected Shortfall döndürür.
    VaR ile aynı hesaplamadan geliyor; sadece 'es' alanına odaklanır.
    Şimdilik tam VaR response'u döndürüyoruz. Member 4 isterse sadece 'es' alanını kullanır.
    """
    try:
        return services.get_var(ticker, method, confidence)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/volatility", response_model=VolatilityResponse)
def volatility_endpoint(ticker: str):
    return services.get_volatility(ticker)

# --- ÖNBELLEK YÖNETİM ENDPOINT'LERİ (Issue #29) ---

@router.get("/cache-status")
def get_cache_status():
    """Önbellekteki anahtarlari ve toplam öğe sayisini döndürür"""
    return services.get_cache_status()

@router.delete("/cache")
def clear_cache():
    """ önbelleği temizler"""
    return services.clear_cache()