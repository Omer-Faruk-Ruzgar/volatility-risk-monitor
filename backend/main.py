# main.py, backend uygulamasının başlangıç noktasıdır.
# `uvicorn backend.main:app --reload` komutunu çalıştırdığında,
# uvicorn bu dosyayı okur ve sunucuyu başlatır.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import router

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

# Health Endpoint
# /health, sunucunun çalışıp çalışmadığını kontrol eden basit bir endpoint'tir.
# Hiçbir iş mantığı içermez, sadece {"status": "ok"} döndürür.
# Bir şeyler çalışmıyorsa ilk kontrol edilecek yer burasıdır:
# curl http://localhost:8000/health
# Eğer bu başarısız olursa backend çalışmıyor demektir.
# Eğer bu çalışıyorsa ama diğer endpoint'ler çalışmıyorsa sorun endpoint'tedir diyebiliriz.
@app.get('/health')
def health():
    return {'status': 'ok'}