import streamlit as st
from api_client import get_returns, get_volatility, get_backtest, get_assets, get_portfolio_analysis
from components import line_chart, multi_line_chart, summary_table

# Sayfa Ayarları - Browser sekmesinde görünecek isim
st.set_page_config(page_title="Volatility Risk Monitor", layout="wide")

# Sidebar - Navigasyon
st.sidebar.title("Volatility Risk Monitor")
page = st.sidebar.radio(
    "Gezinti:",
    ["Ana Sayfa", "Returns (Getiriler)", "Volatility (Oynaklık)","Portföy Yönetimi", "Risk Metrics", "Backtest"]
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

elif page == "Portföy Yönetimi":
    st.title("Portföy Risk Analizi")
    
    # 1. Ticker Seçimi
    assets = get_assets()
    selected_tickers = st.multiselect("Portföye Varlık Ekleyin:", assets, default=["AAPL", "MSFT"])
    
    if selected_tickers:
        st.subheader("Varlık Ağırlıkları")
        weights = []
        cols = st.columns(len(selected_tickers))
        
        for i, ticker in enumerate(selected_tickers):
            with cols[i]:
                weight = st.slider(f"{ticker} (%)", 0, 100, 50) / 100
                weights.append(weight)
        
        total_weight = sum(weights)
        
        # 2. Ağırlık Kontrol Göstergesi
        if abs(total_weight - 1.0) < 1e-9:
            st.success(f"Toplam Ağırlık: %{total_weight*100:.0f}")
            if st.button("Portföyü Analiz Et"):
                data = get_portfolio_analysis(selected_tickers, weights)
                
                # 3. Metrik Kartları
                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("Portföy VaR (%95)", f"{data['VaR']:.2%}")
                c2.metric("Expected Shortfall (ES)", f"{data['ES']:.2%}")
                c3.metric("Çeşitlendirme Etkisi", f"+{data['Diversification_Effect']:.2%}")
                
                # 4. Isı Haritası (Korelasyon Matrisi)
                st.subheader("Korelasyon Matrisi")
                st.dataframe(data['Correlation_Matrix'].style.background_gradient(cmap='Blues'), use_container_width=True)
        else:
            st.error(f"Toplam Ağırlık: %{total_weight*100:.0f}  (Toplam 100 olmalı!)")
    else:
        st.info("Lütfen analiz için en az bir varlık seçin.")