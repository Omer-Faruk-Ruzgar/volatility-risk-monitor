import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from chatbot import render_portfolio_chat

from api_client import (
    get_assets, get_returns, get_volatility,
    get_risk_metrics, get_backtest, get_breach_stats,
    get_portfolio_analysis,
)
from components import line_chart, multi_line_chart, regime_chart, var_breach_chart, summary_table , regime_chart

# Sayfa Ayarları
 
st.set_page_config(page_title="Volatility Risk Monitor", layout="wide")

 
# Ticker listesini önbellekle — her sayfa yenilenişinde tekrar çekilmez

@st.cache_data(ttl=300)
def fetch_assets():
    try:
        return get_assets()
    except Exception:
        return ["XOM", "CVX", "USO", "BNO", "XLE", "UNG", "KSA", "GLD", "WEAT", "TLT", "SPY"]

# Sidebar: sadece sayfa navigasyonu
st.sidebar.title("Volatility Risk Monitor")
page = st.sidebar.radio(
    "Gezinti:",
    ["Ana Sayfa", "Returns", "Volatility", "Risk Metrics", "Backtest", "Portföy"]
)

# Ana Sayfa dışındaki sayfalar için ticker seçici
if page != "Ana Sayfa" and page != "Portföy":
    assets = fetch_assets()
    selected_ticker = st.sidebar.selectbox(
        "Ticker:",
        assets,
        index=0,
        key="selected_ticker"
    )
    
st.sidebar.divider()
st.sidebar.caption("Backend: `uvicorn backend.main:app --reload`")
st.sidebar.caption("Frontend: `streamlit run app.py`")

# Yardımcı: Ticker sekmeleri — analiz sayfaları buradan ticker alır
def ticker_tabs() -> str:
    """
    Tüm ticker'ları sekme olarak gösterir, seçili olanı döndürür.
    Kullanıcı sekmeye tıklayarak geçiş yapar.
    """
    assets = fetch_assets()
    tabs = st.tabs(assets)
    # Hangi sekme aktif? st.tabs doğrudan index dönmez,
    # bu yüzden her sekmeye kendi içeriğini döndürecek şekilde
    # session_state ile izliyoruz.
    for i, tab in enumerate(tabs):
        with tab:
            st.session_state["selected_ticker"] = assets[i]
            yield assets[i], tab
            return  # ilk aktif sekmenin içeriği render edildiğinde dur

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
def render_for_ticker(render_fn):
    ticker = st.session_state.get("selected_ticker", fetch_assets()[0])
    render_fn(ticker)


# Ana Sayfa

if page == "Ana Sayfa":
    # 1. Dashboard için gerekli fonksiyonu api_client'dan import etmeyi unutma (yukarıda yapmadıysan)
    from api_client import get_all_summaries
    from components import ticker_card

    st.markdown("""
        <style>
        .main-title { font-size: 42px; font-weight: bold; text-align: center; color: #1E3A5F; margin-bottom: 8px; }
        .sub-title  { font-size: 17px; text-align: center; color: #555; margin-bottom: 32px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">Volatility Risk Monitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Finansal piyasaların anlık risk durumunu ve oynaklık metriklerini tek bakışta izleyin.</div>', unsafe_allow_html=True)
    
    st.divider()

    # 2. Canlı Ticker Kartları Bölümü
    st.subheader("Piyasa Risk Özeti")
    
    try:
        # 11 ticker için veri çekme işlemi (Spinner ile kullanıcıya bilgi veriyoruz)
        with st.spinner("Piyasa özetleri backend'den çekiliyor, lütfen bekleyin..."):
            summaries = get_all_summaries()

        if summaries:
            # Kartları 4 sütun halinde diziyoruz
            cols = st.columns(4)
            for i, data in enumerate(summaries):
                # Modülo operatörü ile kartları sütunlara dağıtıyoruz
                with cols[i % 4]:
                    ticker_card(
                        ticker=data['ticker'],
                        garch_vol=data['last_garch'],
                        delta=data['delta'],
                        status=data['status']
                    )
        else:
            st.warning("Henüz görüntülenecek veri bulunamadı. Lütfen backend bağlantısını kontrol edin.")
            
    except Exception as e:
        st.error(f"Dashboard yüklenirken bir hata oluştu: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3. Bilgi Paneli (Statik Metinler Yerine Daha Şık Bir İpucu)
    st.info(" **İpucu:** Yukarıdaki kartlar son GARCH volatilitesini gösterir. Detaylı analiz için sol menüden ilgili sekmeye geçiş yapabilirsiniz.")
    
    st.divider()
    st.caption("Bu platform sadece akademik amaçlıdır ve yatırım tavsiyesi içermez. Veriler 5 dakikada bir güncellenir.")


# Returns
elif page == "Returns":
    st.title("Getiri Analizi")

    def render_returns(ticker):
        try:
            with st.spinner(f"{ticker} verileri yükleniyor..."):
                df = get_returns(ticker)

            c1, c2, c3 = st.columns(3)
            c1.metric("Ortalama Günlük Getiri", f"{df['log_return'].mean():.4f}")
            c2.metric("Günlük Volatilite (std)", f"{df['log_return'].std():.4f}")
            c3.metric("Veri Noktası",            f"{len(df):,}")

            st.divider()
            line_chart(df, x="date", y="log_return",
                       title=f"{ticker} — Günlük Logaritmik Getiriler")

            df["cumulative"] = df["log_return"].cumsum()
            line_chart(df, x="date", y="cumulative",
                       title=f"{ticker} — Kümülatif Log Getiri")

        except ConnectionError as e:
            st.error(f" {e}")
        except Exception as e:
            st.error(f"Hata: {e}")

    render_for_ticker(render_returns)


# Volatility
elif page == "Volatility":
    st.title("Oynaklık Analizi")
    st.info("İlk yükleme GARCH ve XGBoost eğitimi nedeniyle 5-10 saniye sürebilir. Sonraki istekler önbellekten gelir.")

    def render_volatility(ticker):
        try:
            with st.spinner(f"{ticker} için volatilite modelleri hesaplanıyor..."):
                df = get_volatility(ticker)

            c1, c2, c3 = st.columns(3)
            c1.metric("EWMA (Son)",     f"{df['EWMA'].iloc[-1]:.4f}")
            c2.metric("GARCH (Son)",    f"{df['GARCH'].iloc[-1]:.4f}")
            c3.metric("Forecast (Son)", f"{df['Forecast'].iloc[-1]:.4f}")

            st.divider()
            multi_line_chart(
                df, x="date",
                y_cols=["EWMA", "GARCH", "Forecast"],
                title=f"{ticker} — Volatilite Modelleri Karşılaştırması (Yıllıklandırılmış)",
            )

            # multi_line_chart'tan sonra:
            st.divider()
            st.subheader(" Tarihsel Olaylar ve Volatilite Rejimleri")
            regime_chart(df, ticker)

            st.subheader("Model Özet İstatistikleri")
            stats = pd.DataFrame({
                "Model":    ["EWMA", "GARCH", "Forecast"],
                "Ortalama": [df["EWMA"].mean(),    df["GARCH"].mean(),    df["Forecast"].mean()],
                "Min":      [df["EWMA"].min(),     df["GARCH"].min(),     df["Forecast"].min()],
                "Max":      [df["EWMA"].max(),     df["GARCH"].max(),     df["Forecast"].max()],
                "Son":      [df["EWMA"].iloc[-1],  df["GARCH"].iloc[-1],  df["Forecast"].iloc[-1]],
            }).round(4)
            st.dataframe(stats, use_container_width=True, hide_index=True)

        except ConnectionError as e:
            st.error(f"{e}")
        except Exception as e:
            st.error(f"Hata: {e}")

    render_for_ticker(render_volatility)


# Risk Metrics
elif page == "Risk Metrics":
    st.title("Risk Metrikleri")

    method = st.radio(
        "VaR Yöntemi:",
        ["parametric", "historical"],
        format_func=lambda x: "Parametrik (Normal Dağılım)" if x == "parametric" else "Tarihsel",
        horizontal=True,
    )

    def render_risk(ticker):
        try:
            with st.spinner(f"{ticker} için VaR ve ES hesaplanıyor..."):
                df, breach_dates = get_risk_metrics(ticker, method=method)

            stats = get_breach_stats(df)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("VaR İhlal Sayısı", stats["breach_count"])
            c2.metric("İhlal Oranı",      f"{stats['breach_rate']:.2%}")
            c3.metric("Beklenen Oran",    f"{stats['expected_rate']:.2%}")
            c4.metric("Model Durumu",     stats["status"])

            st.divider()
            var_breach_chart(df, ticker=ticker, method=method)

            if breach_dates:
                st.subheader(f"Son İhlal Tarihleri (toplam {len(breach_dates)})")
                breach_df = pd.DataFrame({"İhlal Tarihi": breach_dates[-30:][::-1]})
                st.dataframe(breach_df, use_container_width=True, hide_index=True)
            else:
                st.success("Seçili dönemde VaR ihlali bulunmuyor.")

        except ConnectionError as e:
            st.error(f" {e}")
        except Exception as e:
            st.error(f"Hata: {e}")

    render_for_ticker(render_risk)


# Backtest
elif page == "Backtest":
    st.title("VaR Backtest")

    method = st.selectbox(
        "VaR Yöntemi:",
        ["parametric", "historical"],
        format_func=lambda x: "Parametrik" if x == "parametric" else "Tarihsel",
    )

    def render_backtest(ticker):
        try:
            with st.spinner(f"{ticker} için backtest hesaplanıyor..."):
                df = get_backtest(ticker, method=method)

            stats = get_breach_stats(df)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Toplam Gün",   f"{stats['n_observations']:,}")
            c2.metric("İhlal Sayısı", stats["breach_count"])
            c3.metric("İhlal Oranı",  f"{stats['breach_rate']:.2%}")
            c4.metric("Model Durumu", stats["status"])

            st.divider()

            fig = go.Figure()
            colors = ["red" if b else "steelblue" for b in df["breach"]]
            fig.add_trace(go.Bar(
                x=df["date"], y=df["return"],
                name="Günlük Getiri",
                marker_color=colors,
                opacity=0.7,
            ))
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["var"],
                name="VaR Eşiği (%95)",
                line=dict(color="red", width=2, dash="dash"),
            ))
            fig.update_layout(
                title=f"{ticker} — Backtest: Getiri vs VaR (kırmızı = ihlal)",
                xaxis_title="Tarih", yaxis_title="Günlük Getiri",
                bargap=0.1, hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)

            breach_only = df[df["breach"]].copy()
            if not breach_only.empty:
                st.subheader(f"İhlal Günleri (toplam {len(breach_only)})")
                breach_only = breach_only[["date", "return", "var"]].copy()
                breach_only["return"] = breach_only["return"].round(4)
                breach_only["var"]    = breach_only["var"].round(4)
                breach_only["aşım"]  = (breach_only["return"] - breach_only["var"]).round(4)
                breach_only = breach_only.sort_values("date", ascending=False)
                st.dataframe(breach_only, use_container_width=True, hide_index=True)

        except ConnectionError as e:
            st.error(f" {e}")
        except Exception as e:
            st.error(f"Hata: {e}")

    render_for_ticker(render_backtest)


# Portföy
elif page == "Portföy":
    st.title("Portföy Risk Analizi")

    # Varlık Seçimi
    assets = fetch_assets()
    default = ["SPY", "GLD"] if "SPY" in assets and "GLD" in assets else assets[:2]
    selected = st.multiselect("Portföye Varlık Ekleyin:", assets, default=default)

    if not selected:
        st.info("Analiz için en az bir varlık seçin.")
        st.stop()

    # Ağırlık Belirleme
    st.subheader("Varlık Ağırlıkları")
    weights = []
    cols = st.columns(len(selected))
    equal_w = round(100 / len(selected))
    for i, t in enumerate(selected):
        with cols[i]:
            w = st.slider(f"{t} (%)", 0, 100, equal_w, key=f"w_{t}")
            weights.append(w / 100)

    total = sum(weights)
    if abs(total - 1.0) > 1e-6:
        st.error(f"Toplam ağırlık: %{total*100:.0f} — Toplam 100 olmalı!")
        st.stop()

    st.success(f"Toplam Ağırlık: %{total*100:.0f} ✓")

    # Analiz Butonu ve Sonuçlar
    if st.button(" Portföyü Analiz Et", type="primary"):
        try:
            with st.spinner("Gerçek piyasa verileri ve korelasyonlar hesaplanıyor..."):
                # Backend'den risk metriklerini al
                data = get_portfolio_analysis(selected, weights)
                
                # api_client'dan yeni fonksiyonu çağır (Hiyerarşik Matris)
                from api_client import get_correlation_matrix
                corr_matrix = get_correlation_matrix(selected)

            st.divider()
            
            # Risk Metrikleri Widgetları
            c1, c2, c3 = st.columns(3)
            c1.metric("Portföy VaR (%95)", f"{data['VaR']:.2%}")
            c2.metric("Expected Shortfall (ES)", f"{data['ES']:.2%}")
            c3.metric("Çeşitlendirme Etkisi", f"{data['Diversification_Effect']:.2%}")

            # --- Hiyerarşik Korelasyon Matrisi ---
            st.subheader("Hiyerarşik Korelasyon Matrisi")
            st.markdown("*Varlıklar Ward metoduna göre benzerliklerine göre sıralanmıştır.*")
            st.dataframe(
                corr_matrix.style.background_gradient(cmap="RdYlGn_r", axis=None).format("{:.2f}"),
                use_container_width=True
            )

            # --- Otomatik Analiz ve Yorumlar ---
            st.subheader(" Akıllı Portföy Yorumları")
            
            # Matrisin üst üçgenini tara (çiftleri ayıklamak için)
            upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
            pairs = upper_tri.unstack().dropna()
            
            insights_count = 0
            for (var1, var2), corr in pairs.items():
                if corr >= 0.70:
                    st.info(f" **{var1}** ve **{var2}** arasında çok güçlü pozitif korelasyon var ({corr:.2f}). Bu iki varlığın aynı anda düşme riski yüksektir.")
                    insights_count += 1
                elif corr <= -0.40:
                    st.success(f" **{var1}** ve **{var2}** negatif korelasyon gösteriyor ({corr:.2f}). Portföy için harika bir çeşitlendirme kaynağı.")
                    insights_count += 1
            
            if insights_count == 0:
                st.write("Portföydeki varlıklar arasında ekstrem bir bağımlılık tespit edilmedi. Dengeli bir dağılım görünüyor.")

            st.divider()
            st.caption(" **Kritik Not:** Bu matris tarihsel getiri serilerinden hesaplanmıştır. Korelasyon zamanla değişebilir (Correlation Breakdown).")

        except Exception as e:
            st.error(f"Portföy analizi sırasında bir hata oluştu: {e}")

st.divider() # Araya şık bir çizgi çeker

# Şimdilik chatbotu test etmek için sahte (mock) bir özet verisi veriyoruz.
test_summary = {
    "allocation": {"AAPL": 50, "XOM": 50}, 
    "var_95": "-2.5%",
    "volatility": "15.2%",
    "diversification_effect": "+0.5%",
    "high_corr_pairs": "Yok"
}

# Chatbotu ekrana çizdiren fonksiyonumuzu çağırıyoruz
render_portfolio_chat(test_summary)