import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from api_client import (
    get_assets, get_returns, get_volatility,
    get_risk_metrics, get_backtest, get_breach_stats,
    get_portfolio_analysis,
)
from components import line_chart, multi_line_chart, var_breach_chart, summary_table

# Sayfa Ayarları
 
st.set_page_config(page_title="Volatility Risk Monitor", layout="wide")

 
# Ticker listesini önbellekle — her sayfa yenilenişinde tekrar çekilmez

@st.cache_data(ttl=300)
def fetch_assets():
    try:
        return get_assets()
    except Exception:
        return ["XOM", "CVX", "USO", "BNO", "XLE", "UNG", "KSA", "GLD", "WEAT", "TLT", "SPY"]

# Sidebar — sadece sayfa navigasyonu
st.sidebar.title("Volatility Risk Monitor")
page = st.sidebar.radio(
    "Gezinti:",
    ["Ana Sayfa", "Returns", "Volatility", "Risk Metrics", "Backtest", "Portföy"]
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


def render_with_tabs(render_fn):
    """
    Ticker sekmelerini çizer; aktif sekmenin içinde render_fn(ticker) çağırır.
    """
    assets = fetch_assets()
    # Önceki seçimi koru
    if "selected_ticker" not in st.session_state:
        st.session_state["selected_ticker"] = assets[0]

    tabs = st.tabs(assets)
    for i, tab in enumerate(tabs):
        with tab:
            render_fn(assets[i])


# Ana Sayfa
if page == "Ana Sayfa":
    st.markdown("""
        <style>
        .main-title { font-size: 42px; font-weight: bold; text-align: center; color: #1E3A5F; margin-bottom: 8px; }
        .sub-title  { font-size: 17px; text-align: center; color: #555; margin-bottom: 32px; }
        .card {
            background: #f1f3f5; padding: 20px; border-radius: 10px;
            border-top: 4px solid #1E3A5F; color: #333; min-height: 130px;
        }
        .model-card {
            background: #1E3A5F; padding: 12px; border-radius: 8px;
            text-align: center; font-weight: bold; color: white;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">Volatility Risk Monitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Finansal piyasalarda risk yönetimi ve oynaklık tahmini için uçtan uca izleme platformu.</div>', unsafe_allow_html=True)
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="card"><b> Risk Analizi</b><br><br>Rolling VaR ve Expected Shortfall hesaplamaları ile portföy riskini ölçün. Kupiec testi ile model doğruluğunu sınayın.</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card"><b> Volatilite Tahmini</b><br><br>EWMA, GARCH(1,1) ve XGBoost modelleriyle piyasa oynaklığını tahmin edin ve karşılaştırın.</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card"><b> Portföy Analizi</b><br><br>Birden fazla varlık seçin, ağırlık atayın ve portföy düzeyinde risk metriklerinizi görün.</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Analitik Modeller")
    m1, m2, m3 = st.columns(3)
    m1.markdown('<div class="model-card">EWMA</div>', unsafe_allow_html=True)
    m2.markdown('<div class="model-card">GARCH(1,1)</div>', unsafe_allow_html=True)
    m3.markdown('<div class="model-card">XGBoost</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Sol menüden analiz türünü seçin → Ticker sekmesine tıklayın → Sonuçları inceleyin.")
    st.divider()
    st.caption("Bu platform sadece akademik amaçlıdır ve yatırım tavsiyesi içermez.")


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
            st.error(f"🔌 {e}")
        except Exception as e:
            st.error(f"Hata: {e}")

    render_with_tabs(render_returns)


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
            st.error(f"🔌 {e}")
        except Exception as e:
            st.error(f"Hata: {e}")

    render_with_tabs(render_volatility)


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

    render_with_tabs(render_risk)


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

    render_with_tabs(render_backtest)


# Portföy
elif page == "Portföy":
    st.title("Portföy Risk Analizi")

    assets = fetch_assets()
    default = ["SPY", "GLD"] if "SPY" in assets and "GLD" in assets else assets[:2]
    selected = st.multiselect("Portföye Varlık Ekleyin:", assets, default=default)

    if not selected:
        st.info("Analiz için en az bir varlık seçin.")
        st.stop()

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

    if st.button(" Portföyü Analiz Et", type="primary"):
        try:
            with st.spinner("Portföy analizi hesaplanıyor..."):
                data = get_portfolio_analysis(selected, weights)

            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Portföy VaR (%95)",      f"{data['VaR']:.2%}")
            c2.metric("Expected Shortfall (ES)", f"{data['ES']:.2%}")
            c3.metric("Çeşitlendirme Etkisi",   f"{data['Diversification_Effect']:.2%}")

            st.subheader("Korelasyon Matrisi")
            st.dataframe(
                data["Correlation_Matrix"].style.background_gradient(cmap="RdYlGn_r", axis=None),
                use_container_width=True,
            )

        except ConnectionError as e:
            st.error(f" {e}")
        except Exception as e:
            st.error(f"Hata: {e}")

