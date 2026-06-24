"""Jeopolitik risk gostergesi icin sabit bolge tanimlari.

Bu dosya sadece veri icerir, is mantigi icermez.
Her bolge; koordinat, filtre anahtar kelimeleri ve etkiledigi ticker'lari tanimlar.
"""

RISK_REGIONS = {
    "hormuz": {
        "label": "Hurmuz / Orta Dogu",
        "lat": 26.5,
        "lon": 56.3,
        "keywords": [
            "Strait of Hormuz",
            "Saudi Arabia oil",
            "Iran sanctions",
            "OPEC",
            "Middle East oil",
        ],
        "tickers": ["KSA", "USO", "BNO", "XOM", "CVX", "XLE", "UNG"],
    },
    "black_sea": {
        "label": "Karadeniz / Ukrayna",
        "lat": 46.5,
        "lon": 31.0,
        "keywords": [
            "Ukraine grain",
            "Black Sea shipping",
            "Russia oil sanctions",
            "Russia energy",
            "Ukraine war",
        ],
        "tickers": ["WEAT", "BNO", "UNG"],
    },
    "gulf_coast": {
        "label": "ABD Korfez Kiyisi",
        "lat": 29.5,
        "lon": -94.0,
        "keywords": [
            "Gulf Coast refinery",
            "Permian Basin",
            "US shale production",
            "Hurricane Gulf",
            "Texas oil",
        ],
        "tickers": ["USO", "UNG", "XOM", "CVX", "XLE"],
    },
    "venezuela": {
        "label": "Venezuela",
        "lat": 8.0,
        "lon": -66.0,
        "keywords": [
            "Venezuela oil",
            "Venezuela sanctions",
            "PDVSA",
            "Venezuela production",
        ],
        "tickers": ["USO", "XOM", "CVX"],
    },
}
