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
    return ['AAPL', 'MSFT', 'JPM', 'GLD', 'SPY',
            'GOOGL', 'AMZN', 'BRK-B', 'XOM', 'TLT']