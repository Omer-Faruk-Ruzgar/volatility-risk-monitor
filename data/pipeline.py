import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

#  fonksiyonları içeri aktarıyoruz
from fetcher import fetch_data
from cleaner import clean, compute_returns

def run_pipeline():
    """
    Veri çekme, temizleme ve veritabanina kaydetme adimlarini sirasiyla çaliştiran ana fonksiyon.
    """
    print(" Pipeline başlatiliyor...\n")

    # 1. AŞAMA: VERİ ÇEKME (Fetcher)
    target_tickers = ['AAPL', 'MSFT', 'JPM', 'GLD', 'SPY', 'GOOGL', 'AMZN', 'BRK-B', 'XOM', 'TLT']
    print(" Yahoo Finance üzerinden ham veriler çekiliyor...")
    raw_data = fetch_data(tickers=target_tickers, period="5y")
    
    if raw_data is None or raw_data.empty:
        print(" Hata: Veri çekilemedi. İşlem iptal ediliyor...")
        return

    # Sadece Kapanış (Close) fiyatlarını al
    if 'Close' in raw_data.columns.levels[0]:
        prices = raw_data['Close']
    else:
        prices = raw_data

    # Tarih indeksini düzenle
    prices.index = pd.to_datetime(prices.index)

    # 2. AŞAMA: VERİ TEMİZLEME VE HESAPLAMA (Cleaner)
    print(" Veriler temizleniyor ve logaritmik getiriler hesaplaniyor...")
    cleaned_prices = clean(prices)
    final_data = compute_returns(cleaned_prices)


    # 3. AŞAMA: VERİTABANINA KAYDETME (SQLAlchemy)
    print(" Veriler SQLAlchemy kullanilarak market.db'ye kaydediliyor...")
    
    
    # pipeline.py'nin bulunduğu 'data' klasörünü bul ve içine 'market.db' yi yerleştir
    data_dir = Path(__file__).parent.resolve()
    db_path = data_dir / 'market.db'
    
    # Motoru (engine) bu kesin yol ile oluştur
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
   
    
    # Pandas kullanarak DataFrame'i tek satırda SQL tablosuna yazdır.
    final_data.to_sql('log_returns', con=engine, if_exists='replace', index=True)
    
    print(f"\n TAMAMLANDI : Bütün veriler başariyla '{db_path.name}' dosyasina yazildi!")

if __name__ == "__main__":
    run_pipeline()