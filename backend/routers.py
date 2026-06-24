# routers.py, tüm API endpoint'lerini içeren dosyadır.
# Bir endpoint, frontend'in veri almak için çağırdığı bir URL adresidir.
# Örnek: GET /api/assets : mevcut hisse senedi listesini döndürür.
# 
# Bu dosya main.py'e import edilir ve /api prefix'i ile kaydedilir.
# Yani burada yazdığın @router.get('/assets') aslında /api/assets olur.

from fastapi import APIRouter, HTTPException


 # schemas.py'da tanımladığımız modeller
from backend.schemas import VaRResponse , VolatilityResponse, ReturnsResponse , NewsResponse , PortfolioSummaryResponse , SentimentAlertResponse, StressTestResponse, GeoRiskResponse


from backend import services

from typing import List
from fastapi import Body


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
    try:
        return services.get_returns(ticker)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  


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
    try:
        return services.get_volatility(ticker)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # bu satırı ekle

#  ÖNBELLEK  ENDPOINTLERİ 

@router.get("/cache-status")
def get_cache_status():
    """Önbellekteki anahtarlari ve toplam öğe sayisini döndürür"""
    return services.get_cache_status()

@router.delete("/cache")
def clear_cache():
    """ önbelleği temizler"""
    return services.clear_cache()


# Finnhub üzerinden hisse senedine ait güncel haberleri getirir
@router.get("/news/{ticker}", response_model=NewsResponse)
def get_company_news(ticker: str, limit: int = 10):
    return services.get_news(ticker, limit)     



@router.post("/portfolio", response_model=PortfolioSummaryResponse)
def portfolio_endpoint(tickers: List[str] = Body(...), weights: List[float] = Body(...)):
    if len(tickers) < 2:
        raise HTTPException(status_code=422, detail="Portföy analizi için en az 2 varlık gereklidir.")
    if len(tickers) != len(weights):
        raise HTTPException(status_code=422, detail="Ticker ve ağırlık sayısı eşleşmiyor.")
    if abs(sum(weights) - 1.0) > 0.01:
        raise HTTPException(status_code=422, detail=f"Ağırlıkların toplamı 1.0 olmalıdır (şu an: {sum(weights):.4f}).")
    return services.get_portfolio_summary(tickers, weights)


@router.get("/news/sentiment-alert/{ticker}", response_model=SentimentAlertResponse)
def sentiment_alert(ticker: str):
    return services.get_sentiment_alert(ticker)


@router.post("/stress-test", response_model=StressTestResponse)
def stress_test_endpoint(
    tickers:    List[str]   = Body(...),
    weights:    List[float] = Body(...),
    start_date: str         = Body(...),
    end_date:   str         = Body(...),
):
    """
    Seçilen portföyün belirtilen tarih aralığındaki tarihsel getiri şoklarını simüle eder.
    """
    if len(tickers) < 1:
        raise HTTPException(status_code=422, detail="En az 1 varlık gereklidir.")
    if len(tickers) != len(weights):
        raise HTTPException(status_code=422, detail="Ticker ve ağırlık sayısı eşleşmiyor.")
    try:
        return services.run_stress_test(tickers, weights, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/geo-risk", response_model=GeoRiskResponse)
def geo_risk_endpoint():
    """Jeopolitik risk bolgelerinin guncel gerilim skorlarini dondurur."""
    try:
        return {"regions": services.get_geo_risk()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))