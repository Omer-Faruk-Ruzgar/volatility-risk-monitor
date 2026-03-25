# schemas.py, API'nin istek ve yanıt veri yapılarını tanımlar.
# Pydantic modelleri kullanılarak her endpoint'in tam olarak hangi veriyi
# döndüreceği burada belirlenir.
#
# Bu dosya Üye 4 ile yapılan bir sözleşme gibidir.
# Üye 4, dashboard'u bu yapılara göre inşa eder.
# Bu dosyayı değiştirmeden önce mutlaka Üye 4'e haber ver.

from pydantic import BaseModel
from typing import List

# Temel Veri Yapıları

# Tek bir tarih-değer çifti
# Örnek: {"date": "2024-01-15", "value": -0.012}
class ReturnPoint(BaseModel):
    date: str    # tarih, "YYYY-MM-DD" formatında
    value: float # o güne ait log getiri değeri

# Endpoint Yanıt Modelleri

# returns{ticker} endpoint'inin döndürdüğü veri yapısı
# Örnek: {"ticker": "AAPL", "data": [{"date": "...", "value": ...}, ...]}
class ReturnsResponse(BaseModel):
    ticker: str              # hisse senedi sembolü, örn: "AAPL"
    data: List[ReturnPoint]  # tarih-getiri çiftlerinin listesi

# volatility{ticker} endpoint'inin döndürdüğü veri yapısı
# Üç farklı volatilite tahmin yöntemini aynı anda döndürür
class VolatilityResponse(BaseModel):
    ticker: str           # hisse senedi sembolü
    dates: List[str]      # tarih listesi, tüm seriler bu tarihleri paylaşır
    ewma: List[float]     # EWMA yöntemiyle hesaplanan volatilite değerleri
    garch: List[float]    # GARCH(1,1) yöntemiyle hesaplanan volatilite değerleri
    forecast: List[float] # XGBoost modeliyle tahmin edilen volatilite değerleri

# var{ticker} endpoint'inin döndürdüğü veri yapısı
# VaR = Value at Risk
# ES  = Expected Shortfall
class VaRResponse(BaseModel):
    ticker: str                  # hisse senedi sembolü
    dates: List[str]             # tarih listesi
    parametric_var: List[float]  # normal dağılım varsayımıyla hesaplanan VaR
    historical_var: List[float]  # geçmiş veriye dayalı hesaplanan VaR
    es: List[float]              # VaR'ı aşan günlerdeki ortalama kayıp
    breaches: List[str]          # gerçek kaybın VaR'ı aştığı günlerin tarihleri

# backtest{ticker} endpoint'inin döndürdüğü veri yapısı
# Backtesting, VaR modelinin geçmişteki doğruluğunu ölçer
class BacktestResponse(BaseModel):
    ticker: str              # hisse senedi sembolü
    method: str              # kullanılan volatilite yöntemi: 'ewma', 'garch' veya 'forecast'
    breach_count: int        # VaR'ın aşıldığı toplam gün sayısı
    breach_rate: float       # aşım oranı (breach_count / toplam gün sayısı)
    kupiec_statistic: float  # Kupiec testinin istatistik değeri
    kupiec_p_value: float    # p-değeri > 0.05 ise model kabul edilebilir demektir
    result: str              # test sonucu: 'pass' (geçti) veya 'fail' (kaldı)