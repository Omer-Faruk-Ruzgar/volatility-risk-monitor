# main.py, backend uygulamasının başlangıç noktasıdır.
# `uvicorn backend.main:app --reload` komutunu çalıştırdığında,
# uvicorn bu dosyayı okur ve sunucuyu başlatır.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import router
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
from apscheduler.schedulers.background import BackgroundScheduler
from data.pipeline import run_pipeline

# FastAPI uygulama örneğini oluşturuyoruz.
# title ve version, /docs adresindeki otomatik dokümantasyonda görünür.
app = FastAPI(title='Volatility Platform API', version='1.0')

# CORS Ayarları
# CORS (Cross-Origin Resource Sharing), tarayıcıların uyguladığı bir güvenlik
# özelliğidir. Frontend'imiz localhost:8501'de (Streamlit), backend'imiz ise
# localhost:8000'de (FastAPI) çalışır. Tarayıcı, farklı portları farklı
# kaynak olarak gördüğü için aralarındaki istekleri varsayılan olarak engeller.
# Bu middleware, tarayıcıya "localhost:8501'den gelen isteklere izin ver" der.

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:8501'],  # sadece Streamlit uygulamamıza izin ver
    allow_methods=['*'],                      # GET, POST vb. tüm metodlara izin ver
    allow_headers=['*'],                      # tüm header'lara izin ver
)

# Router Kaydı
# Router'lar, ilgili endpoint'leri bir arada gruplar.
# routers.py'den router'ı import edip burada prefix ile kaydediyoruz.
# prefix = '/api' demek, routers.py'deki tüm route'lar /api ile başlar.
# Örnek: @router.get('/assets') GET /api/assets olur.
app.include_router(router, prefix = '/api')



#  APSCHEDULER VE API ENDPOINT İÇİN EKLENMİŞTİR


# Zamanlayıcı (APScheduler) Ayarları
scheduler = BackgroundScheduler(timezone="UTC")

@app.on_event("startup")
def start_scheduler():
    """Uygulama ayağa kalktiğinda zamanlayiciyi başlatir."""
    
    # Yaz saati: NYSE 21:00 UTC kapanır, 21:30'da güncelle
    scheduler.add_job(
        lambda: run_pipeline(update=True),
        'cron', hour=21, minute=30,
        month='3-11',      # Mart-Kasım arası
        id='update_summer'
    )

    # Kış saati: NYSE 22:00 UTC kapanır, 22:30'da güncelle
    scheduler.add_job(
        lambda: run_pipeline(update=True),
        'cron', hour=22, minute=30,
        month='11,12,1,2', # Kasım-Şubat arası
        id='update_winter'
    )
    
    scheduler.start()
    print("APScheduler aktif: Yaz/Kiş saati görevleri arka planda dinleniyor...")


# Data Status Endpoint'i
@app.get("/api/data-status")
def get_data_status():
    """ JSON formatinda durum raporu döndüren Endpoint."""
    
    # GÜVENLİ DOSYA YOLU BULMA:
    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / 'data' / 'market.db'
    
    try:
        engine = create_engine(f"sqlite:///{db_path.as_posix()}")
        
        # Son tarihi çek ve sadece ilk 10 karakterini al (Örn: "2026-04-27")
        raw_date = str(pd.read_sql("SELECT MAX(Date) FROM log_returns", engine).iloc[0, 0])
        last_update = raw_date[:10]
        total_rows = pd.read_sql("SELECT COUNT(*) FROM log_returns", engine).iloc[0, 0]
        
        columns = pd.read_sql("PRAGMA table_info(log_returns)", engine)['name'].tolist()
        tickers_count = len([col for col in columns if col != 'Date'])
        
    except Exception as e:
        last_update = "Bulunamadi..."
        total_rows = 0
        tickers_count = 0

    next_run = None
    summer_job = scheduler.get_job('update_summer')
    winter_job = scheduler.get_job('update_winter')
    
    if summer_job and summer_job.next_run_time:
        next_run = summer_job.next_run_time
    if winter_job and winter_job.next_run_time:
        if next_run is None or winter_job.next_run_time < next_run:
            next_run = winter_job.next_run_time

    return {
        "last_update": f"{last_update}T21:30:00Z" if last_update != "Bulunamadi..." else None,
        "total_rows": int(total_rows),
        "tickers": int(tickers_count),
        "next_scheduled": next_run.strftime("%Y-%m-%dT%H:%M:%SZ") if next_run else None
    }