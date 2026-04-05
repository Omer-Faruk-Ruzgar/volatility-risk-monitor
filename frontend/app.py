import streamlit as st
from api_client import get_returns, get_volatility, get_backtest
from components import line_chart, multi_line_chart, summary_table

# Sayfa Ayarları
st.set_page_config(page_title="Skorix Finansal Analiz", layout="wide")

# Sidebar - Ticker ve Navigasyon
st.sidebar.title("Skorix Kontrol Paneli")
ticker = st.sidebar.text_input("Hisse Sembolü Giriniz:", value="AAPL")

page = st.sidebar.radio(
    "Analiz Türü Seçin:",
    ["Returns (Getiriler)", "Volatility (Oynaklık)", "Risk Metrics", "Backtest"]
)

# --- SAYFA İÇERİKLERİ ---

if page == "Returns (Getiriler)":
    st.title(f"{ticker} - Getiri Analizi")
    # API'den veriyi alıyoruz
    df = get_returns(ticker)
    # Component kullanarak tekli grafik çiziyoruz
    line_chart(df, x="date", y="value", title=f"{ticker} - Günlük Log Returns")

elif page == "Volatility (Oynaklık)":
    st.title(f"{ticker} - Oynaklık Analizi")
    # API'den veriyi alıyoruz
    df = get_volatility(ticker)
    # Component kullanarak çoklu grafik çiziyoruz (EWMA, GARCH, Forecast)
    multi_line_chart(df, x="date", y_cols=["EWMA", "GARCH", "Forecast"], title=f"{ticker} Volatilite Karşılaştırması")

elif page == "Risk Metrics":
    st.title(f"{ticker} - Risk Metrikleri")
    st.info("Bu sayfa bir sonraki aşamada tamamlanacak.")

elif page == "Backtest":
    st.title(f"{ticker} - Strateji Testi")
    # API'den veriyi alıyoruz
    df = get_backtest(ticker)
    # Component kullanarak tabloyu gösteriyoruz
    summary_table(df, title=f"{ticker} Backtest Sonuç Tablosu")