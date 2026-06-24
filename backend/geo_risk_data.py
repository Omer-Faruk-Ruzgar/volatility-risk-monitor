"""Jeopolitik risk gostergesi icin sabit bolge tanimlari.

Bu dosya sadece veri icerir, is mantigi icermez.
Her bolge; koordinat, filtre anahtar kelimeleri, etkiledigi ticker'lari
ve kisa aciklamasini tanimlar.
"""

RISK_REGIONS = {
    "hormuz": {
        "label": "Hurmuz / Orta Dogu",
        "lat": 26.5,
        "lon": 56.3,
        "keywords": [
            "hormuz",
            "iran",
            "saudi arabia",
            "opec",
            "middle east oil",
            "persian gulf",
            "saudi aramco",
            "gulf war",
        ],
        "tickers": ["KSA", "USO", "BNO", "XOM", "CVX", "XLE", "UNG"],
        "description": "Dunya petrol ticaret hacminin %20'si Hurmuz Bogazi'ndan geciyor. "
                       "Iran gerilimi ve OPEC+ uretim kararlari fiyatlari dogrudan etkiliyor.",
    },
    "black_sea": {
        "label": "Karadeniz / Ukrayna",
        "lat": 46.5,
        "lon": 31.0,
        "keywords": [
            "ukraine",
            "russia ukraine",
            "black sea",
            "ukraine grain",
            "odessa",
            "zelensky",
            "kyiv",
            "russia missile",
        ],
        "tickers": ["WEAT", "BNO", "UNG"],
        "description": "Ukrayna savasi kuresel tahil arzini ve Rus enerji ihracatini etkiliyor. "
                       "WEAT ve BNO dogrudan maruz kalan varliklarin basinda geliyor.",
    },
    "gulf_coast": {
        "label": "ABD Korfez Kiyisi",
        "lat": 29.5,
        "lon": -94.0,
        "keywords": [
            "gulf coast",
            "permian basin",
            "us shale",
            "hurricane gulf",
            "texas oil",
            "us oil production",
            "eia crude",
            "us energy",
        ],
        "tickers": ["USO", "UNG", "XOM", "CVX", "XLE"],
        "description": "ABD'nin en buyuk rafineri kompleksi ve LNG ihracat terminalleri burada. "
                       "Kasirga sezonu ve regulator degisiklikleri enerji fiyatlarini etkiliyor.",
    },
    "venezuela": {
        "label": "Venezuela",
        "lat": 8.0,
        "lon": -66.0,
        "keywords": [
            "venezuela",
            "pdvsa",
            "maduro",
            "caracas",
            "latin america oil",
        ],
        "tickers": ["USO", "XOM", "CVX"],
        "description": "Kanitmis rezervleri bakimindan dunyanin en buyuk uretici adayi. "
                       "ABD yaptirimlari ve altyapi sorunlari uretimi kisitliyor.",
    },
    "south_china_sea": {
        "label": "G. Cin Denizi / Tayvan",
        "lat": 22.0,
        "lon": 120.5,
        "keywords": [
            "taiwan",
            "south china sea",
            "china military",
            "us china",
            "china trade",
            "semiconductor",
            "beijing",
            "china sanctions",
        ],
        "tickers": ["SPY", "GLD", "TLT", "KSA"],
        "description": "Tayvan gerilimi kuresel risk istahlini dusuruyor; GLD ve TLT guvenli liman "
                       "talep gorurken SPY satis baskisiyla karsilasabiliyor.",
    },
    "russia_eu_gas": {
        "label": "Rusya / AB Dogalgaz",
        "lat": 51.0,
        "lon": 23.0,
        "keywords": [
            "gazprom",
            "russia gas",
            "lng europe",
            "nord stream",
            "european energy",
            "russia energy",
            "moscow sanctions",
            "russia",
        ],
        "tickers": ["UNG", "TLT", "SPY"],
        "description": "Avrupa LNG talebindeki degisimler kuresel dogalgaz fiyatlarini etkiliyor. "
                       "UNG bu bolgenin fiyat oynakligina en duyarli varliktir.",
    },
    "libya": {
        "label": "Libya",
        "lat": 27.0,
        "lon": 17.0,
        "keywords": [
            "libya",
            "libyan",
            "tripoli",
            "noc libya",
            "benghazi",
        ],
        "tickers": ["BNO", "USO", "XLE"],
        "description": "Libya hafif-tatli ham petrol Brent sepetini dogrudan etkiliyor. "
                       "Uretim kesintileri ani fiyat artislarina neden olabiliyor.",
    },
    "west_africa": {
        "label": "Bati Afrika / Nijerya",
        "lat": 5.5,
        "lon": 5.0,
        "keywords": [
            "nigeria",
            "nnpc",
            "niger delta",
            "west africa",
            "abuja",
            "nigeria oil",
            "angola oil",
        ],
        "tickers": ["USO", "BNO", "XOM", "CVX"],
        "description": "Nijerya gunluk 1.5 milyon varil uretim kapasitesiyle buyuk OPEC+ uretici. "
                       "Boru hatti sabotajlari ve siyasi belirsizlik arz guvenilirligini etkilemekte.",
    },
}
