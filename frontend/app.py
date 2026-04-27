import streamlit as st
from api_client import get_returns, get_volatility, get_backtest
from components import line_chart, multi_line_chart, summary_table

# Sayfa Ayarları - Browser sekmesinde görünecek isim
st.set_page_config(page_title="Volatility Risk Monitor", layout="wide")

# Sidebar - Navigasyon
st.sidebar.title("Volatility Risk Monitor")
page = st.sidebar.radio(
    "Gezinti:",
    ["Ana Sayfa", "Returns (Getiriler)", "Volatility (Oynaklık)", "Risk Metrics", "Backtest"]
)

# Ticker girişi sadece analiz sayfalarında görünsün
ticker = "AAPL"
if page != "Ana Sayfa":
    ticker = st.sidebar.text_input("Hisse Sembolü Giriniz:", value="AAPL")

# --- SAYFA İÇERİKLERİ ---

if page == "Ana Sayfa":
    # Custom CSS
    st.markdown("""
        <style>
        .main-title { font-size: 45px; font-weight: bold; text-align: center; color: #1E3A5F; }
        .sub-title { font-size: 18px; text-align: center; margin-bottom: 40px; color: #555; }
        .card { 
            background-color: #f1f3f5; padding: 20px; border-radius: 10px; 
            border-top: 4px solid #1E3A5F; margin-bottom: 20px; color: #333; min-height: 150px;
        }
        .model-card {
            background-color: #1E3A5F; padding: 12px; border-radius: 8px;
            text-align: center; font-weight: bold; color: white; margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # 1. Başlık ve Açıklama
    st.markdown('<div class="main-title">Volatility Risk Monitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Finansal piyasalarda risk yönetimi ve oynaklık tahmini için geliştirilmiş uçtan uca izleme platformu.</div>', unsafe_allow_html=True)
    st.divider()

    # 2. Ne İşe Yarar?
    st.header("Temel Fonksiyonlar")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="card"><b>Risk Analizi</b><br>Geçmiş veriler üzerinden Value at Risk (VaR) hesaplamaları ve backtest süreçleri ile maruz kalınan riski ölçün.</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card"><b>Volatilite Tahmini</b><br>EWMA ve GARCH gibi istatistiksel modellerle piyasa oynaklığını analiz edin.</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card"><b>Zaman Serisi Analizi</b><br>Hisse senetlerinin günlük logaritmik getirilerini ve kümülatif performanslarını takip edin.</div>', unsafe_allow_html=True)

    # 3. Kullanılan Modeller
    st.header("Analitik Modeller")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.markdown('<div class="model-card">EWMA</div>', unsafe_allow_html=True)
    m_col2.markdown('<div class="model-card">GARCH</div>', unsafe_allow_html=True)
    m_col3.markdown('<div class="model-card">XGBoost</div>', unsafe_allow_html=True)
    m_col4.markdown('<div class="model-card">LSTM</div>', unsafe_allow_html=True)

    # 4. Nasıl Kullanılır?
    st.header("Kullanım Akışı")
    st.info("Sol menüden analiz türünü seçin -> Ticker girin -> Görselleştirilmiş sonuçları analiz edin.")

    # 5. Uyarı
    st.divider()
    st.caption("**Yasal Uyarı:** Bu platform sadece akademik bir projedir ve yatırım tavsiyesi içermez.")

elif page == "Returns (Getiriler)":
    st.title(f"{ticker} - Getiri Analizi")
    df = get_returns(ticker)
    # y="value" 
    
    line_chart(df, x="date", y="log_return", title=f"{ticker} - Günlük Logaritmik Getiriler")
elif page == "Volatility (Oynaklık)":
    st.title(f"{ticker} - Oynaklık Analizi")
    df = get_volatility(ticker)
    multi_line_chart(df, x="date", y_cols=["EWMA", "GARCH", "Forecast"], title=f"{ticker} Volatilite Modelleri Karşılaştırması")

elif page == "Backtest":
    st.title(f"{ticker} - Strateji Backtest")
    df = get_backtest(ticker)
    summary_table(df, title=f"{ticker} Backtest ve VaR İhlal Tablosu")