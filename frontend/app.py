import streamlit as st

# 1. Sayfa Yapılandırması
st.set_page_config(page_title="Volatility Risk Monitor", layout="wide")

# 2. Sidebar - Ticker Selector (İstenen yeni madde)
st.sidebar.title("🔍 Ayarlar")
ticker = st.sidebar.text_input("Hisse/Kripto Sembolü Girin:", value="BTC-USD")

st.sidebar.markdown("---")

# 3. Sidebar - Navigation (Tam olarak istenen 4 sayfa ismi)
st.sidebar.title("📊 Navigasyon")
menu = ["Returns", "Volatility", "Risk Metrics", "Backtest"]
choice = st.sidebar.selectbox("Sayfa Seçin:", menu)

# 4. Sayfa İçerikleri (Placeholder - Sadece Başlıklar)
if choice == "Returns":
    st.title("📈 Returns (Getiriler)")
    st.write(f"{ticker} için getiri analizi burada yer alacak.")

elif choice == "Volatility":
    st.title("📉 Volatility (Oynaklık)")
    st.write(f"{ticker} için volatilite hesaplamaları.")

elif choice == "Risk Metrics":
    st.title("⚖️ Risk Metrics (Risk Metrikleri)")
    st.write("VaR ve Sharpe oranları.")

elif choice == "Backtest":
    st.title("🔄 Backtest")
    st.write("Strateji test sonuçları.")