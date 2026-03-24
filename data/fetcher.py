import os
import yfinance as yf
import pandas as pd

def fetch_data(tickers, period="5y"):
    """
    Yahoo Finance üzerinden belirtilen sembollerin piyasa verilerini çeker.
    
    Parametreler:
    - tickers (list veya str): Hisse/Varlik sembolleri (Örn: 'AAPL' veya ['AAPL', 'MSFT'])
    - period (str): Verinin kapsayacaği zaman araliği (Örn: '1mo', '1y', '5y')
    
    Döndürür:
    - pandas.DataFrame: Fiyat geçmişini içeren tablo veya hata durumunda None.
    """
    try:
        print(f"İnternetten veri çekiliyor... Semboller: {tickers} | Periyot: {period}")
        
        # yfinance ile toplu veri indirme işlemi
        data = yf.download(tickers, period=period)
        
        # Gelen verinin boş olup olmadığını kontrol et (savunmacı programlama)
        if data.empty:
            print("Uyari: İstenen periyotta veri bulunamadi veya sembol hatali.")
            return None
            
        print("Veri başariyla indirildi!")
        return data
        
    except Exception as e:
        print(f"Veri çekilirken sistemsel bir hata oluştu: {e}")
        return None
    

    
    # İşletim sistemi işlemleri için (klasör oluşturma)
# (yfinance ve pandas importları ve fetch_data fonksiyonun yukarıda kalacak)

if __name__ == "__main__":
    target_tickers = ['AAPL', 'MSFT', 'JPM', 'GLD', 'SPY', 'GOOGL', 'AMZN', 'BRK-B', 'XOM', 'TLT']
    
    # Veriyi çek
    portfolio_data = fetch_data(tickers=target_tickers, period="5y")
    
    if portfolio_data is not None:
        # --- GÖREV 1: Veriyi data/raw içine CSV olarak kaydet ---
        
        # 1. data klasörü içinde raw adında bir klasör oluştur (yoksa)
        os.makedirs("data/raw", exist_ok=True)
        
        # 2. Veriyi CSV formatında kaydet
        csv_yolu = "data/raw/ham_portfoy_verisi.csv"
        portfolio_data.to_csv(csv_yolu)
        print(f"\n✅ BAŞARILI: Ham veri '{csv_yolu}' dosyasına kaydedildi.")
        
        
        # --- GÖREV 2: Boş dönen hisse kontrolü ---
        
        bos_hisseler = []
        # Çektiğimiz her bir hisse senedi kodu için dön:
        for hisse in target_tickers:
            # Kapanış ('Close') fiyatlarının tamamı boş (NaN) mu diye kontrol et
            if portfolio_data['Close'][hisse].isna().all():
                bos_hisseler.append(hisse)
                
        if len(bos_hisseler) == 0:
            print("✅ KONTROL: Tüm hisse senetleri dolu. Boş dönen veri yok!")
        else:
            print(f"❌ UYARI: Liderine haber ver! Şu hisselerde sorun var: {bos_hisseler}")