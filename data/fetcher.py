
import os
import yfinance as yf
import pandas as pd

def fetch_data(tickers, period="5y"):
    """
    Yahoo Finance kullanarak belirtilen hisse sembolleri için geçmiş piyasa verilerini çeker.
    
    Parametreler:
    - tickers (list veya str): Hisse/Varlik sembolleri (Örn: 'AAPL' veya ['AAPL', 'MSFT']).
    - period (str): Verinin kapsayacaği zaman araliği (Örn: '1mo', '1y', '5y').
    
    Döndürür:
    - pandas.DataFrame: Geçmiş fiyat verilerini içeren DataFrame veya hata durumunda None.
    """
    try:
        print(f"İnternetten veri çekiliyor... Semboller: {tickers} | Periyot: {period}")
        
        # yfinance kullanarak veriyi indir
        data = yf.download(tickers, period=period)
        
        # Çekilen verinin boş olup olmadığını kontrol et 
        if data.empty:
            print("Uyari: İstenen periyot için veri bulunamadi veya hisse sembolü geçersiz...")
            return None
            
        print("Veri başariyla çekildi!..")
        return data
        
    except Exception as e:
        print(f"Veri çekilirken sistemsel bir hata oluştu: {e}")
        return None

if __name__ == "__main__":
    target_tickers = [
        # Çekirdek Enerji
        'XOM',   # ExxonMobil - büyük petrol üreticisi
        'CVX',   # Chevron - karşılaştırma için
        'USO',   # WTI ham petrol ETF - direkt petrol fiyatı
        'BNO',   # Brent ham petrol ETF - Avrupa/Orta Doğu kıyaslaması
        'XLE',   # Enerji sektörü ETF - genel sektör
        'UNG',   # Doğalgaz ETF - savaş kaynaklı gaz şoku
        # Orta Doğu
        'KSA',   # iShares MSCI Suudi Arabistan ETF - jeopolitik risk proxy
        # Hammadde
        'GLD',   # Altın ETF - çatışma döneminde güvenli liman
        'WEAT',  # Buğday ETF - Ukrayna savaşı gıda şoku
        # Makro / Baseline
        'TLT',   # Uzun vadeli tahvil ETF - riskten kaçış sinyali
        'SPY',   # S&P 500 - piyasa bazı karşılaştırma
    ]
    
    # 10 yıllık geçmiş veriyi çek (Krizleri kapsayacak şekilde)
    portfolio_data = fetch_data(tickers=target_tickers, period="10y")


    
    if portfolio_data is not None:
        # --- GÖREV 1: Ham çıktıyı yerel olarak CSV formatında kaydet ---
        
        # 'data' klasörü içinde 'raw' klasörü yoksa oluştur
        os.makedirs("data/raw", exist_ok=True)
        
        # DataFrame'i bir CSV dosyasına kaydet
        csv_path = "data/raw/raw_portfolio_data.csv"
        portfolio_data.to_csv(csv_path)
        print(f"\n BAŞARILI: Ham veri '{csv_path}' konumuna kaydedildi...")
        
        
        # --- GÖREV 2: Hiçbir hissenin boş veri döndürmediğini doğrula ---
        
        empty_tickers = []
        # İstek atılan her bir hisse için döngü oluştur
        for ticker in target_tickers:
            # Hisseye ait tüm 'Close' (Kapanış) fiyatları NaN (boş) mu diye kontrol et
            if portfolio_data['Close'][ticker].isna().all():
                empty_tickers.append(ticker)
                
        if len(empty_tickers) == 0:
            print(" DOĞRULAMA: Tüm hisselerin verisi var. Boş sütun bulunamadi!..")
        else:
            print(f" UYARI: Aşağidaki hisseler boş veri döndürdü: {empty_tickers}")