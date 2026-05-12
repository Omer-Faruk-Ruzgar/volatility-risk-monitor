import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
import argparse  
from data.fetcher import fetch_data
from data.cleaner import clean, compute_returns

def run_pipeline(update=False):  # update parametresini ekledik
    """
    Veri çekme, temizleme ve veritabanina kaydetme adimlarini sirasiyla çaliştiran ana fonksiyon.
    """
    print(f" Pipeline {'Güncelleme' if update else 'Kurulum'} Modunda Başlatiliyor...\n")

    # 1. AŞAMA: AYARLAR VE BAĞLANTI
    target_tickers = [
        'XOM', 'CVX', 'USO', 'BNO', 'XLE', 'UNG', 
        'KSA', 'GLD', 'WEAT', 'TLT', 'SPY'
    ]
    
    # Dosya yollarını güvenli yöntemle belirliyoruz
    data_dir = Path(__file__).parent.resolve()
    db_path = data_dir / 'market.db'
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")

    # 2. AŞAMA: VERİ ÇEKME (Fetcher)
    if update:
        print(" Sadece eksik veriler kontrol ediliyor...")
        try:
            # market.db'deki en son tarihi sorgula
            last_date_query = "SELECT MAX(Date) FROM log_returns"
            last_date = pd.read_sql(last_date_query, engine).iloc[0, 0]
            
            # Son tarihten 1 gün sonrasını başlangıç yap
            start_date = (pd.to_datetime(last_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            
            print(f" {start_date} tarihinden itibaren veriler çekiliyor...")
            raw_data = fetch_data(tickers=target_tickers, start=start_date)
            
        except Exception as e:
            print(f" Veritabani okunurken hata oluştu...")
            print(f" Sifirdan kurulum moduna geçiliyor... Detay: {e}")
            raw_data = fetch_data(tickers=target_tickers, period="10y")
            update = False # Hata alırsak kurulum moduna zorla çekiyoruz
    else:
        print(" Yahoo Finance üzerinden 10 yillik veriler çekiliyor...")
        raw_data = fetch_data(tickers=target_tickers, period="10y")
    
    # Veri gelmediyse işlemi durdur
    if raw_data is None or raw_data.empty:
        print(" Sistem güncel veya veri çekilemedi. İşlem sonlandirildi...")
        return

    # Sadece Kapanış (Close) fiyatlarını al
    if 'Close' in raw_data.columns.levels[0]:
        prices = raw_data['Close']
    else:
        prices = raw_data

    # Tarih indeksini düzenle
    prices.index = pd.to_datetime(prices.index)

    # 3. AŞAMA: VERİ TEMİZLEME VE HESAPLAMA (Cleaner)
    print(" Veriler temizleniyor ve logaritmik getiriler hesaplaniyor...")
    cleaned_prices = clean(prices)
    final_data = compute_returns(cleaned_prices)

    # 4. AŞAMA: VERİTABANINA KAYDETME (SQLAlchemy)
    if update:
        # Mevcut verilerin altına ekle (append)
        print(" Yeni veriler market.db tablosuna ekleniyor...")
        final_data.to_sql('log_returns', con=engine, if_exists='append', index=True)
    else:
        # Tabloyu sil ve baştan yarat (replace)
        print(" Veriler market.db dosyasina sifirdan yaziliyor...")
        final_data.to_sql('log_returns', con=engine, if_exists='replace', index=True)
    
    print(f"\n TAMAMLANDI : '{db_path.name}' başariyla güncellendi!")

if __name__ == "__main__":
    # Terminal komutlarını yönetmek için argparse ekliyoruz
    parser = argparse.ArgumentParser(description="Volatility Risk Monitor ETL Pipeline")
    parser.add_argument('--update', action='store_true', help="Sadece son kayittan itibaren güncelleme yapar")
    
    args = parser.parse_args()

    # Fonksiyonu gelen --update komutuna göre tetikliyoruz
    run_pipeline(update=args.update)