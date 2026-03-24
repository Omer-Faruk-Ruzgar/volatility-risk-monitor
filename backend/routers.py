# routers.py, tüm API endpoint'lerini içeren dosyadır.
# Bir endpoint, frontend'in veri almak için çağırdığı bir URL adresidir.
# Örnek: GET /api/assets : mevcut hisse senedi listesini döndürür.
# 
# Bu dosya main.py'e import edilir ve /api prefix'i ile kaydedilir.
# Yani burada yazdığın @router.get('/assets') aslında /api/assets olur.

from fastapi import APIRouter

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
    # TODO: 2. haftada bu listeyi veritabanından çekeceğiz
    return {'tickers': ['AAPL', 'MSFT', 'JPM', 'GLD', 'SPY',
                        'GOOGL', 'AMZN', 'BRK-B', 'XOM', 'TLT']}