# services.py, iş mantığını içeren katmandır.
# routers.py'deki endpoint'ler veriyi buradan alır.
# Bu dosya, Üye 1'in model fonksiyonlarını çağırır ve
# sonuçları API yanıtı olarak formatlayacaktir.
#
# Şu an için sadece iskelet kodu içeriyor.
# Üye 2'nin veri pipeline'ı hazır olduğunda burası genişletilecek.

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
        "var": -0.032,
        "es": -0.048,
        "breaches": ["2024-01-03"], 
    }