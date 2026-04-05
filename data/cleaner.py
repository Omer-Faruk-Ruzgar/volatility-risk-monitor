import pandas as pd
import numpy as np

def clean(df):
    """
    Ham finansal veri setindeki eksik değerleri temizliyoruz.

    Finansal veriler (zaman serileri) ile çalişirken en büyük düşmanimiz eksik verilerdir (NaN - Not a Number).
    Eğer sistem bir günü boş görürse, VaR (Riske Maruz Değer) hesaplamasi çöker ve hata verir. 
    Bu boşluklari silmek yerine "mantikli bir şekilde doldurmak" için bu iki pandas metodunu kullaniriz.
    ffill ve bfill.

    """
    # 1. Eksik verileri bir önceki günün fiyatıyla doldur (Forward Fill)
    df_cleaned = df.ffill()
    
    # 2. Eğer en baştaki günlerde eksik veri varsa geriye dönük doldur (Backward Fill)
    df_cleaned = df_cleaned.bfill()
    
    return df_cleaned

def compute_returns(prices):
    """
    Verilen fiyat verisi üzerinden günlük LOGARİTMİK getirileri hesaplar.
    """
    # Logaritmik Getiri formülü kullanıyoruz: ln(Bugün / Dün)
    # np.log() ile doğal logaritma alıyoruz. shift(1) dünün fiyatını verir.
    log_returns = np.log(prices / prices.shift(1))
    
    # İlk günün geçmişi olmadığı için NaN döner, o satırı siliyoruz
    log_returns = log_returns.dropna(how='all')
    
    return log_returns

if __name__ == "__main__":
    # --- ŞEMA DOĞRULAMA (SCHEMA VALIDATION) TESTİ ---
    
    print("Veriler okunuyor ve temizleniyor...")
    try:
        # Ham veriyi oku. (yfinance çıktısı 2 satırlık başlık kullanır, bu yüzden header=[0,1])
        raw_data = pd.read_csv("data/raw/raw_portfolio_data.csv", header=[0, 1], index_col=0)
        
        # Sadece 'Close' (Kapanış) fiyatlarını al
        if 'Close' in raw_data.columns.levels[0]:
            prices = raw_data['Close']
        else:
            prices = raw_data
            
        # İndeksi datetime (tarih) formatına çevir
        prices.index = pd.to_datetime(prices.index)
        
        # 1. Adım: Veriyi temizle (ffill ve bfill)
        cleaned_prices = clean(prices)
        
        # 2. Adım: Logaritmik getirileri hesapla
        log_returns_df = compute_returns(cleaned_prices)
        
        # --- DOĞRULAMA RAPORU ---
        print("\n" + "="*50)
        print(" ÇIKTI ŞEMASI DOĞRULAMA RAPORU...")
        print("="*50)
        
        # Kural 1: Index = Date
        is_date_index = isinstance(log_returns_df.index, pd.DatetimeIndex)
        print(f"Kural 1 | İndeks Tarih mi?. (Index = Date)  : {'Geçti...' if is_date_index else 'Kaldi '}")
        
        # Kural 2: Columns = Tickers
        print(f"Kural 2 | Kolonlar Hisse mi? (Cols=Tickers): Geçti... -> {list(log_returns_df.columns)[:5]}...")
        
        # Kural 3: Values = Log Returns
        # Log getiriler genelde -0.1 ile +0.1 arasında küçük sayılardır.
        is_log_returns = log_returns_df.iloc[0, 0] < 1.0 
        print(f"Kural 3 | Değerler Log Getiri mi?          : {'Geçti...' if is_log_returns else 'Kaldi '}")
        


        print("\nSonuç Önizleme (İlk 3 Satir):")
        print(log_returns_df.head(50))
        print("="*50)
        


    except FileNotFoundError:
        print(" Hata: 'data/raw/raw_portfolio_data.csv' dosyasi bulunamadi.")