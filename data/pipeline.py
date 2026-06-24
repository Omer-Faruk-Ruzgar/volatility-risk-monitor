import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
import argparse
import logging
import sys
from data.fetcher import fetch_data
from data.cleaner import clean, compute_returns

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def run_pipeline(update=False):
    """
    Veri çekme, temizleme ve veritabanina kaydetme adimlarini sirasiyla çaliştiran ana fonksiyon.
    """
    log.info("Pipeline %s modunda baslatiliyor.", "Guncelleme" if update else "Kurulum")

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
        log.info("Eksik veriler kontrol ediliyor...")
        try:
            last_date = pd.read_sql("SELECT MAX(Date) FROM log_returns", engine).iloc[0, 0]
            start_date = (pd.to_datetime(last_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            log.info("%s tarihinden itibaren veriler cekiliyor...", start_date)
            raw_data = fetch_data(tickers=target_tickers, start=start_date)
        except Exception as e:
            log.error("Veritabani okunurken hata: %s -- sifirdan kurulum moduna geciliyor.", e)
            raw_data = fetch_data(tickers=target_tickers, period="10y")
            update = False
    else:
        log.info("Yahoo Finance uzerinden 10 yillik veriler cekiliyor...")
        raw_data = fetch_data(tickers=target_tickers, period="10y")

    if raw_data is None or raw_data.empty:
        log.warning("Veri cekilemedi veya sistem zaten guncel. Islem sonlandirildi.")
        return

    # Sadece Kapanış (Close) fiyatlarını al
    if hasattr(raw_data.columns, "levels") and "Close" in raw_data.columns.levels[0]:
        prices = raw_data["Close"]
    else:
        prices = raw_data

    prices.index = pd.to_datetime(prices.index)

    # 3. AŞAMA: VERİ TEMİZLEME VE HESAPLAMA (Cleaner)
    log.info("Veriler temizleniyor ve logaritmik getiriler hesaplaniyor...")
    cleaned_prices = clean(prices)
    final_data = compute_returns(cleaned_prices)

    # 4. AŞAMA: VERİTABANINA KAYDETME (SQLAlchemy)
    if update:
        log.info("Yeni veriler market.db tablosuna ekleniyor (%d satir)...", len(final_data))
        final_data.to_sql("log_returns", con=engine, if_exists="append", index=True)
    else:
        log.info("Veriler market.db dosyasina sifirdan yaziliyor (%d satir)...", len(final_data))
        final_data.to_sql("log_returns", con=engine, if_exists="replace", index=True)

    log.info("TAMAMLANDI: '%s' basariyla guncellendi.", db_path.name)

if __name__ == "__main__":
    # Terminal komutlarını yönetmek için argparse ekliyoruz
    parser = argparse.ArgumentParser(description="Volatility Risk Monitor ETL Pipeline")
    parser.add_argument('--update', action='store_true', help="Sadece son kayittan itibaren güncelleme yapar")
    
    args = parser.parse_args()

    # Fonksiyonu gelen --update komutuna göre tetikliyoruz
    run_pipeline(update=args.update)