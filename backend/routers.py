# routers.py, tüm API endpoint'lerini içeren dosyadır.
# Bir endpoint, frontend'in veri almak için çağırdığı bir URL adresidir.
# Örnek: GET /api/assets : mevcut hisse senedi listesini döndürür.
# 
# Bu dosya main.py'e import edilir ve /api prefix'i ile kaydedilir.
# Yani burada yazdığın @router.get('/assets') aslında /api/assets olur.

from fastapi import APIRouter
from backend.schemas import VaRResponse  # schemas.py'da tanımladığımız model

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
    return services.get_var(ticker, method, confidence)


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
    return services.get_var(ticker, method, confidence)