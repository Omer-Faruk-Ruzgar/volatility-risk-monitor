import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import io
from dotenv import load_dotenv

# .env Dosyasını Yükle (Chatbot için API anahtarları)
load_dotenv()

# Chatbot Entegrasyonları
from chatbot import render_portfolio_chat, generate_portfolio_summary

# API İstemcisi Importları (Tüm fonksiyonlar toplandı)
from api_client import (
    get_assets, get_returns, get_volatility,
    get_risk_metrics, get_backtest, get_breach_stats,
    get_portfolio_summary, get_all_summaries, get_correlation_matrix,
    get_news, get_sentiment_alert, get_data_status, run_stress_test,
    get_geo_risk,
)

# Profesyonel Görsel Bileşenler
from components import (
    line_chart, multi_line_chart, regime_chart,
    var_breach_chart, summary_table, ticker_card,
    news_card, sentiment_alert_banner, geo_risk_map,
    OPEC_EVENTS, _OPEC_COLORS,
)

# Sayfa Ayarları
st.set_page_config(page_title="Volatility Risk Monitor", layout="wide")

# Global CSS - tüm sayfalarda yüklenir
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap');

/* Gövde ve genel metin - Inter */
html, body, [class*="st-"], .stMarkdown p, .stCaption,
label, .stRadio label, .stSelectbox label,
.stMultiSelect label, .stNumberInput label,
.stTextInput label, div[data-testid="stSidebarContent"] {
    font-family: 'Inter', sans-serif !important;
}

/* Sayfa ve bölüm başlıkları - Space Grotesk */
h1, h2, h3,
.stSidebar h1,
div[data-testid="stSidebarContent"] .stMarkdown h1,
div[data-testid="stSidebarContent"] .stMarkdown h2 {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -0.02em;
}

/* Sayısal metrik değerleri - IBM Plex Mono */
div[data-testid="stMetricValue"],
div[data-testid="stMetricDelta"],
.stDataFrame td,
code, pre {
    font-family: 'IBM Plex Mono', monospace !important;
}

/* Material Symbols ikon fontu - [class*="st-"] override'ından koru
   Streamlit 1.55 "Material Symbols Rounded" kullanir, font local static/media klasöründen gelir */
span[data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] span,
[data-testid="stExpandSidebarButton"] span {
    font-family: 'Material Symbols Rounded' !important;
}

</style>
""", unsafe_allow_html=True)

TICKER_NAMES = {
    "XOM":  "ExxonMobil",
    "CVX":  "Chevron",
    "USO":  "US Oil Fund ETF",
    "BNO":  "Brent Oil ETF",
    "XLE":  "Energy Select ETF",
    "UNG":  "Natural Gas ETF",
    "KSA":  "Saudi Arabia ETF",
    "GLD":  "Gold ETF",
    "WEAT": "Wheat ETF",
    "TLT":  "20Y Treasury ETF",
    "SPY":  "S&P 500 ETF",
}

def ticker_label(t: str) -> str:
    return f"{TICKER_NAMES.get(t, t)} ({t})"

# Ticker listesini önbellekle, her sayfa yenilenişinde tekrar çekilmez
@st.cache_data(ttl=300)
def fetch_assets():
    try:
        return get_assets()
    except Exception:
        return ["XOM", "CVX", "USO", "BNO", "XLE", "UNG", "KSA", "GLD", "WEAT", "TLT", "SPY"]

# Sidebar Navigasyonu
st.sidebar.title("Volatility Risk Monitor")
page = st.sidebar.radio(
    "Gezinti:",
    ["Ana Sayfa", "Returns", "Volatility", "Risk Metrics", "Backtest", "Portföy", "Kriz Simülasyonu"]
)

# Ana Sayfa dışındaki sayfalar için ticker seçici
if page != "Ana Sayfa" and page != "Portföy" and page != "Kriz Simülasyonu":
    assets = fetch_assets()
    selected_ticker = st.sidebar.selectbox(
        "Ticker:",
        assets,
        format_func=ticker_label,
        index=0,
        key="selected_ticker"
    )
    
st.sidebar.divider()

# Veri güncelleme durumu
try:
    status = get_data_status()
    last_raw = status.get("last_update")
    next_raw = status.get("next_scheduled")

    if last_raw:
        last_dt = last_raw[:10]  # "2026-06-20T21:30:00Z" → "2026-06-20"
        st.sidebar.success(f"Son güncelleme: **{last_dt}**")
    else:
        st.sidebar.warning("Veri bulunamadı.")

    if next_raw:
        next_dt = next_raw.replace("T", " ").replace("Z", " UTC")[:19] + " UTC"
        st.sidebar.caption(f"Sonraki güncelleme: {next_dt}")
except Exception:
    st.sidebar.caption("Veri durumu alınamadı.")

st.sidebar.divider()
st.sidebar.caption("Backend: `uvicorn backend.main:app --reload`")
st.sidebar.caption("Frontend: `streamlit run app.py`")


def to_excel_bytes(sheets: dict) -> bytes:
    """{'Sayfa Adı': dataframe} sözlüğünü çok sayfalı Excel byte'ına dönüştürür."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return buf.getvalue()


_PERIOD_DAYS = {"1A": 30, "3A": 90, "6A": 180, "1Y": 365, "Tümü": None}

def apply_date_filter(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Grafik üstüne tarih aralığı seçici ekler, seçime göre filtrelenmiş df döner."""
    choice = st.segmented_control(
        "Tarih Aralığı:",
        list(_PERIOD_DAYS.keys()),
        default="1Y",
        key=f"period_{key}",
    )
    days = _PERIOD_DAYS.get(choice)
    if days is not None:
        cutoff = df["date"].max() - pd.Timedelta(days=days)
        df = df[df["date"] >= cutoff].copy()
    return df


# Yardımcı: Ticker sekmeleri, analiz sayfaları buradan ticker alır
def ticker_tabs():
    """Tüm ticker'ları sekme olarak gösterir, seçili olanı döndürür."""
    assets = fetch_assets()
    tabs = st.tabs([ticker_label(t) for t in assets])
    for i, tab in enumerate(tabs):
        with tab:
            st.session_state["selected_ticker"] = assets[i]
            yield assets[i], tab
            return  # ilk aktif sekmenin içeriği render edildiğinde dur

def render_for_ticker(render_fn):
    ticker = st.session_state.get("selected_ticker", fetch_assets()[0])
    render_fn(ticker)


# --- SAYFA: ANA SAYFA (DASHBOARD) ---
if page == "Ana Sayfa":
    st.markdown("""
        <style>
        .main-title { font-size: 42px; font-weight: 700; text-align: center; color: #E8A33D; margin-bottom: 8px; font-family: 'Space Grotesk', sans-serif; letter-spacing: -0.02em; }
        .sub-title  { font-size: 17px; text-align: center; color: #8A9BB5; margin-bottom: 32px; font-family: 'Inter', sans-serif; }
        .stApp::before {
            content: "";
            position: fixed;
            bottom: -5%;
            right: -8%;
            width: 35%;
            height: 35%;
            z-index: 0;
            pointer-events: none;
            background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 220"><defs><linearGradient id="lg1" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="%23E8A33D"/><stop offset="1" stop-color="%231D9E75"/></linearGradient></defs><path d="M10,170 C60,120 100,200 150,140 C200,80 230,160 270,110" fill="none" stroke="url(%23lg1)" stroke-width="2" opacity="0.28"/><path d="M0,200 C50,160 100,220 150,170 C200,120 240,190 280,150" fill="none" stroke="url(%23lg1)" stroke-width="2" opacity="0.18"/></svg>');
            background-repeat: no-repeat;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">Volatility Risk Monitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Finansal piyasaların anlık risk durumunu ve oynaklık metriklerini tek bakışta izleyin.</div>', unsafe_allow_html=True)
    
    st.divider()

    # Canlı Ticker Kartları Bölümü
    st.subheader("Piyasa Risk Özeti")
    
    try:
        with st.spinner("Piyasa özetleri yükleniyor..."):
            summaries = get_all_summaries()

        if summaries:
            cols = st.columns(4)
            for i, data in enumerate(summaries):
                with cols[i % 4]:
                    ticker_card(
                        ticker=data['ticker'],
                        garch_vol=data['last_garch'],
                        delta=data['delta'],
                        status=data['status']
                    )
        else:
            st.warning("Henüz görüntülenecek veri bulunamadı. Veri pipeline'ının çalıştığından emin olun.")

    except ConnectionError:
        st.error("Backend'e bağlanılamadı.")
        st.code("uvicorn backend.main:app --reload", language="bash")
        st.caption("Yukarıdaki komutu çalıştırıp sayfayı yenileyin.")
    except TimeoutError:
        st.error("Backend yanıt vermedi (zaman aşımı). Sunucunun başlatıldığından emin olun.")
    except Exception as e:
        st.error(f"Dashboard yüklenirken bir hata oluştu: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.info(" **İpucu:** Yukarıdaki kartlar son GARCH volatilitesini gösterir. Detaylı analiz için sol menüden ilgili sekmeye geçiş yapabilirsiniz.")
    
    # JEOPOLITİK RİSK HARİTASI
    st.divider()
    st.subheader("Jeopolitik Risk Gostergesi")
    st.caption(
        "Finnhub haber akisindan VADER duygu analizi ile hesaplanan bolgesel gerilim skoru. "
        "Buyuk ve kirmizi daireler yuksek riski gosteriyor."
    )
    try:
        with st.spinner("Bolgesel gerilim skorlari hesaplaniyor..."):
            geo_regions = get_geo_risk()
        geo_risk_map(geo_regions)
    except ConnectionError:
        st.warning("Jeopolitik risk haritasi yüklenemedi. Backend baglantisini kontrol edin.")
    except Exception as e:
        st.warning(f"Jeopolitik risk gostergesi yuklenemedi: {e}")

    # HABER AKIŞI VE DUYGU ANALİZİ (SENTIMENT)
    st.divider()
    st.subheader("Piyasa Duygu Analizi ve Haber Akışı")
    
    # Genel Piyasa Alarmı (Sentiment Alert)
    try:
        alert_data = get_sentiment_alert("SPY")
        sentiment_alert_banner(alert_data)
    except Exception:
        pass # Backend henüz hazır değilse sessizce geç

    # Ticker Bazlı Haber Kartları
    col_sel, col_empty = st.columns([1, 3])
    with col_sel:
        news_ticker = st.selectbox("Hisse Haberlerini İncele:", fetch_assets(), format_func=ticker_label, index=0)
    
    try:
        with st.spinner(f"{ticker_label(news_ticker)} haberleri analiz ediliyor..."):
            news_data = get_news(news_ticker, limit=5)
            
        c_news, c_sent = st.columns([2, 1])
        
        with c_news:
            news_list = news_data.get('news', [])
            if news_list:
                for item in news_list:
                    news_card(item)
            else:
                st.info(f"{news_ticker} için güncel haber akışı bulunamadı.")
        
        with c_sent:
            st.markdown(f"**{news_ticker} Duygu Özeti**")
            agg_sentiment = news_data.get('aggregate_sentiment', 0)
            st.metric("Toplamsal Skor", f"{agg_sentiment:.2f}", 
                      delta="Pozitif" if agg_sentiment > 0 else "Negatif",
                      delta_color="normal")
            
            if news_data.get('sentiment_trend'):
                st.caption("Duygu Analizi Trendi")
                trend = news_data.get('sentiment_trend', 'stable')
                trend_colors = {"improving": "🟢", "stable": "🟡", "deteriorating": "🔴"}
                st.caption(f"Trend: {trend_colors.get(trend, '⚪')} {trend.capitalize()}")
            else:
                st.info("Bu varlık için yeterli haber trendi bulunamadı.")
                
    except Exception as e:
        st.error(f"Haberler yüklenirken bir hata oluştu. Backend bağlantısını kontrol edin.")

    st.divider()
    st.caption("Bu platform sadece akademik amaçlıdır ve yatırım tavsiyesi içermez. Veriler her işlem günü piyasa kapanışından sonra otomatik olarak güncellenir.")


# --- SAYFA: RETURNS ---
elif page == "Returns":
    st.title("Getiri Analizi")

    def render_returns(ticker):
        try:
            with st.spinner(f"{ticker_label(ticker)} verileri yükleniyor..."):
                df = get_returns(ticker)

            df = apply_date_filter(df, key=f"ret_{ticker}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Ortalama Günlük Getiri", f"{df['log_return'].mean():.4f}")
            c2.metric("Günlük Volatilite (std)", f"{df['log_return'].std():.4f}")
            c3.metric("Veri Noktası",            f"{len(df):,}")

            st.divider()
            line_chart(df, x="date", y="log_return", title=f"{ticker} - Günlük Logaritmik Getiriler")

            df["cumulative"] = df["log_return"].cumsum()
            line_chart(df, x="date", y="cumulative", title=f"{ticker} - Kümülatif Log Getiri")

            st.divider()
            excel = to_excel_bytes({"Getiriler": df.rename(columns={"date": "Tarih", "log_return": "Log Getiri", "cumulative": "Kümülatif"})})
            st.download_button("Excel İndir", data=excel, file_name=f"{ticker}_getiriler.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except ConnectionError as e:
            st.error(str(e))
            st.code("uvicorn backend.main:app --reload", language="bash")
        except TimeoutError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Hata: {e}")

    render_for_ticker(render_returns)


# --- SAYFA: VOLATILITY ---
elif page == "Volatility":
    st.title("Oynaklık Analizi")
    st.info("İlk yükleme GARCH ve XGBoost eğitimi nedeniyle 5-10 saniye sürebilir. Sonraki istekler önbellekten gelir.")

    def render_volatility(ticker):
        try:
            with st.spinner(f"{ticker_label(ticker)} için volatilite modelleri hesaplanıyor..."):
                df = get_volatility(ticker)

            # Son değerleri filtrelemeden önce al (her zaman güncel kalır)
            last_ewma     = df['EWMA'].iloc[-1]
            last_garch    = df['GARCH'].iloc[-1]
            last_forecast = df['Forecast'].iloc[-1]

            df = apply_date_filter(df, key=f"vol_{ticker}")

            c1, c2, c3 = st.columns(3)
            c1.metric("EWMA (Son)",     f"{last_ewma:.4f}")
            c2.metric("GARCH (Son)",    f"{last_garch:.4f}")
            c3.metric("Forecast (Son)", f"{last_forecast:.4f}")

            st.divider()
            multi_line_chart(
                df, x="date",
                y_cols=["EWMA", "GARCH", "Forecast"],
                title=f"{ticker} - Volatilite Modelleri Karşılaştırması (Yıllıklandırılmış)",
            )

            st.divider()
            c_title, c_toggle = st.columns([4, 1])
            c_title.subheader("Tarihsel Olaylar ve Volatilite Rejimleri")
            show_opec = c_toggle.checkbox("OPEC Kararları", value=True, key=f"opec_{ticker}")
            regime_chart(df, ticker, show_opec=show_opec)

            # OPEC detay tablosu
            if show_opec:
                with st.expander("OPEC Karar Detayları"):
                    type_labels = {"cut": "Kesinti", "increase": "Artış", "collapse": "Çöküş/Kriz"}
                    opec_df = pd.DataFrame([
                        {
                            "Tarih":  e["date"],
                            "Tür":    type_labels.get(e["type"], e["type"]),
                            "Karar":  e["detail"],
                        }
                        for e in OPEC_EVENTS
                    ])
                    st.dataframe(
                        opec_df.style.apply(
                            lambda col: [
                                f"color: {_OPEC_COLORS.get({'Kesinti':'cut','Artış':'increase','Çöküş/Kriz':'collapse'}.get(v,'cut'), '#F1EFE8')}"
                                for v in col
                            ] if col.name == "Tür" else [""] * len(col),
                            axis=0,
                        ),
                        hide_index=True,
                        use_container_width=True,
                    )

            st.subheader("Model Özet İstatistikleri")
            stats = pd.DataFrame({
                "Model":    ["EWMA", "GARCH", "Forecast"],
                "Ortalama": [df["EWMA"].mean(),    df["GARCH"].mean(),    df["Forecast"].mean()],
                "Min":      [df["EWMA"].min(),     df["GARCH"].min(),     df["Forecast"].min()],
                "Max":      [df["EWMA"].max(),     df["GARCH"].max(),     df["Forecast"].max()],
                "Son":      [df["EWMA"].iloc[-1],  df["GARCH"].iloc[-1],  df["Forecast"].iloc[-1]],
            }).round(4)
            st.dataframe(stats, width='stretch', hide_index=True)

            st.divider()
            export_df = df.rename(columns={"date": "Tarih", "EWMA": "EWMA", "GARCH": "GARCH", "Forecast": "XGBoost Forecast"})
            excel = to_excel_bytes({"Volatilite": export_df, "Özet İstatistikler": stats})
            st.download_button("Excel İndir", data=excel, file_name=f"{ticker}_volatilite.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except ConnectionError as e:
            st.error(str(e))
            st.code("uvicorn backend.main:app --reload", language="bash")
        except TimeoutError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Hata: {e}")

    render_for_ticker(render_volatility)


# --- SAYFA: RISK METRICS ---
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
            with st.spinner(f"{ticker_label(ticker)} için VaR ve ES hesaplanıyor..."):
                df, breach_dates = get_risk_metrics(ticker, method=method)

            df = apply_date_filter(df, key=f"risk_{ticker}_{method}")
            stats = get_breach_stats(df)

            # breach_dates'i de aynı aralıkla kırp
            if breach_dates:
                min_date = df["date"].min()
                breach_dates = [d for d in breach_dates if pd.Timestamp(d) >= min_date]

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
                st.dataframe(breach_df, width='stretch', hide_index=True)
            else:
                st.success("Seçili dönemde VaR ihlali bulunmuyor.")

            st.divider()
            export_df = df.rename(columns={"date": "Tarih", "return": "Getiri", "var": "VaR (%95)", "es": "ES", "is_breach": "İhlal"})
            excel = to_excel_bytes({"Risk Metrikleri": export_df})
            st.download_button("Excel İndir", data=excel, file_name=f"{ticker}_risk_metrikleri.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except ConnectionError as e:
            st.error(str(e))
            st.code("uvicorn backend.main:app --reload", language="bash")
        except TimeoutError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Hata: {e}")

    render_for_ticker(render_risk)


# --- SAYFA: BACKTEST ---
elif page == "Backtest":
    st.title("VaR Backtest")

    method = st.selectbox(
        "VaR Yöntemi:",
        ["parametric", "historical"],
        format_func=lambda x: "Parametrik" if x == "parametric" else "Tarihsel",
    )

    def render_backtest(ticker):
        try:
            with st.spinner(f"{ticker_label(ticker)} için backtest hesaplanıyor..."):
                df = get_backtest(ticker, method=method)

            df = apply_date_filter(df, key=f"bt_{ticker}_{method}")
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
                title=f"{ticker} - Backtest: Getiri vs VaR (kırmızı = ihlal)",
                xaxis_title="Tarih", yaxis_title="Günlük Getiri",
                bargap=0.1, hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, width='stretch')

            breach_only = df[df["breach"]].copy()
            if not breach_only.empty:
                st.subheader(f"İhlal Günleri (toplam {len(breach_only)})")
                breach_only = breach_only[["date", "return", "var"]].copy()
                breach_only["return"] = breach_only["return"].round(4)
                breach_only["var"]    = breach_only["var"].round(4)
                breach_only["aşım"]  = (breach_only["return"] - breach_only["var"]).round(4)
                breach_only = breach_only.sort_values("date", ascending=False)
                st.dataframe(breach_only, width='stretch', hide_index=True)

            st.divider()
            export_df = df.rename(columns={"date": "Tarih", "return": "Getiri", "var": "VaR (%95)", "breach": "İhlal"})
            excel = to_excel_bytes({"Backtest": export_df, "İhlal Günleri": breach_only if not breach_only.empty else pd.DataFrame()})
            st.download_button("Excel İndir", data=excel, file_name=f"{ticker}_backtest.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except ConnectionError as e:
            st.error(str(e))
            st.code("uvicorn backend.main:app --reload", language="bash")
        except TimeoutError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Hata: {e}")

    render_for_ticker(render_backtest)


# --- SAYFA: PORTFÖY ( AKILLI SİSTEM + AI CHATBOT ENTEGRELİ) ---
elif page == "Portföy":
    st.title(" Profesyonel Portföy Yönetimi")
    st.write("Varlıklarınızı seçin, hazır şablonları kullanın veya ağırlıkları dinamik olarak düzenleyin.")
    
    # 1. HAZIR PORTFÖY ŞABLONLARI
    st.subheader(" Hazır Portföy Şablonları")
    c_sh1, c_sh2, c_sh3 = st.columns(3)
    
    # API'den gelen gerçek varlık listesini al
    assets = fetch_assets()
    
    # Session State Tanımlamaları (Şablonların hafızada doğru tutulması için)
    if "selected_assets" not in st.session_state:
        st.session_state.selected_assets = [assets[0], assets[1]] if len(assets) > 1 else assets
    if "weight_inputs" not in st.session_state:
        st.session_state.weight_inputs = {t: round(100/len(st.session_state.selected_assets), 2) for t in st.session_state.selected_assets}
    if "last_portfolio_data" not in st.session_state:
        st.session_state["last_portfolio_data"] = None
    # Şablon Tanımları
    templates = {
        "Eşit Ağırlık": {"assets": assets[:11], "dist": "equal"},
        "Enerji Yoğun": {"assets": ["XOM", "CVX", "XLE", "USO", "SPY"], "weights": [25.0, 25.0, 20.0, 15.0, 15.0], "dist": "manual"},
        "Güvenli Liman": {"assets": ["GLD", "TLT", "SPY", "UNG"], "weights": [35.0, 35.0, 20.0, 10.0], "dist": "manual"}
    }

    selected_template = None
    if c_sh1.button(" Eşit Ağırlık", width='stretch'): selected_template = "Eşit Ağırlık"
    if c_sh2.button(" Enerji Yoğun", width='stretch'): selected_template = "Enerji Yoğun"
    if c_sh3.button(" Güvenli Liman", width='stretch'): selected_template = "Güvenli Liman"

    if selected_template:
        tmpl = templates[selected_template]
        valid_assets = [a for a in tmpl["assets"] if a in assets]
        st.session_state.selected_assets = valid_assets
        
        if tmpl["dist"] == "equal":
            n = len(valid_assets)
            st.session_state.weight_inputs = {t: round(100/n, 2) for t in valid_assets}
        else:
            st.session_state.weight_inputs = dict(zip(valid_assets, tmpl.get("weights", [])))
        
        # Sayısal girdileri session_state üzerinden de sıfırla ki senkron çalışsınlar
        for t in assets:
            if t in st.session_state.weight_inputs:
                st.session_state[f"num_{t}"] = st.session_state.weight_inputs[t]
            else:
                st.session_state[f"num_{t}"] = 0.0
        st.rerun()

    # 2. VARLIK SEÇİMİ (MULTISELECT)
    safe_defaults = [a for a in st.session_state.selected_assets if a in assets]
    selected = st.multiselect("Portföy Varlıkları:", assets, default=safe_defaults, format_func=ticker_label, key="p_assets_multi")
    st.session_state.selected_assets = selected

    if not selected:
        st.info("Analiz için en az bir varlık seçin.")
        st.stop()

    # 3. AKILLI AĞIRLIK GİRİŞİ VE PASTA GRAFİK (YAN YANA)
    st.divider()
    col_input, col_chart = st.columns([1.2, 1])

    with col_input:
        st.subheader(" Ağırlık Ayarları")
        
        # Hızlı İşlem Butonları
        c_btn1, c_btn2 = st.columns(2)
        if c_btn1.button(" Tümünü Eşitle", width='stretch'):
            n = len(selected)
            for t in selected: st.session_state[f"num_{t}"] = round(100/n, 2)
            st.rerun()
        
        if c_btn2.button(" Kalanı Tamamla", width='stretch'):
            if len(selected) > 0:
                current_sum = sum([st.session_state.get(f"num_{t}", 0) for t in selected[:-1]])
                st.session_state[f"num_{selected[-1]}"] = round(max(0.0, 100.0 - current_sum), 2)
                st.rerun()

        # Sayısal Number Inputlar (Sliderlar yerine daha hassas kontrol)
        current_weights = []
        for t in selected:
            def_val = st.session_state.get("weight_inputs", {}).get(t, 100.0/len(selected) if len(selected)>0 else 0)
            val = st.number_input(f"{ticker_label(t)} (%)", 0.0, 100.0, value=float(st.session_state.get(f"num_{t}", def_val)), key=f"num_{t}", step=0.5)
            current_weights.append(val)

        # Canlı Toplam Göstergesi ve Renk Kodları (Issue Geliştirmesi)
        total_w = round(sum(current_weights), 2)
        if len(selected) < 2:
            st.markdown("### 🔴 Korelasyon analizi için en az 2 varlık seçin.")
            btn_lock = True
        elif abs(total_w - 100) < 0.1:
            st.markdown(f"### 🟢 Toplam Ağırlık: `% {total_w:.2f} / 100` (Mükemmel)")
            btn_lock = False
        elif total_w > 100:
            st.markdown(f"### 🔴 Toplam Ağırlık: `% {total_w:.2f} / 100` (Sınır Aşıldı!)")
            btn_lock = True
        else:
            st.markdown(f"### 🟡 Toplam Ağırlık: `% {total_w:.2f} / 100` (Eksik Dağılım)")
            btn_lock = True

    with col_chart:
        st.subheader(" Portföy Dağılımı")
        if selected and len(current_weights) == len(selected):
            fig = px.pie(values=current_weights, names=selected, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(template="plotly_dark", margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, width='stretch')

    # 4. ANALİZ BUTONU VE GERÇEK ZAMANLI SONUÇLAR
    if st.button(" Portföyü Analiz Et", type="primary", use_container_width=True, disabled=btn_lock, key="p_analyze_final"):
        try:
            with st.spinner("Gerçek piyasa verileri ve risk rasyoları hesaplanıyor..."):
                final_w_list = [w/100 for w in current_weights]
                
                # Canlı POST endpointi tetikleniyor
                data = get_portfolio_summary(selected, final_w_list)
                st.session_state["last_portfolio_data"] = data
                corr_matrix = get_correlation_matrix(selected)

                st.divider()
                
                # --- 🤖 AI ÖZET KARTI ---
                with st.spinner("🤖 AI özeti hazırlanıyor..."):
                    ai_summary = generate_portfolio_summary(data)
                    if ai_summary:
                        st.subheader("🤖 AI Portföy Özeti")
                        st.info(ai_summary)
                        st.divider()
                
                # Risk Metrikleri Widgetları
                m1, m2, m3 = st.columns(3)
                port_var = data.get('VaR', data.get('portfolio_var', data.get('var_95', 0)))
                port_es = data.get('ES', data.get('expected_shortfall', data.get('es', 0)))
                div_eff = data.get('Diversification_Effect', data.get('diversification_effect', 0))
                
                m1.metric("Portföy VaR (%95)", f"{port_var:.2%}")
                m2.metric("Expected Shortfall (ES)", f"{port_es:.2%}")
                m3.metric("Çeşitlendirme Etkisi", f"{div_eff:.2%}")

                # --- Hiyerarşik Korelasyon Matrisi (Ward Sıralamalı) ---
                st.subheader(" Hiyerarşik Korelasyon Matrisi")
                st.markdown("*Varlıklar Ward metoduna göre benzerliklerine göre dizilmiştir.*")
                st.dataframe(corr_matrix.style.background_gradient(cmap="RdYlGn_r", axis=None).format("{:.2f}"), width='stretch')

                # --- Otomatik Risk Analiz Notları ---
                st.subheader(" Akıllı Portföy Yorumları")
                upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
                pairs = upper_tri.unstack().dropna()
                
                insights_count = 0
                for (var1, var2), corr in pairs.items():
                    if corr >= 0.70:
                        st.info(f" **{var1}** ve **{var2}** arasında çok güçlü bağ var ({corr:.2f}). Beraber düşme riskleri yüksektir.")
                        insights_count += 1
                    elif corr <= -0.40:
                        st.success(f" **{var1}** ve **{var2}** negatif korelasyon gösteriyor ({corr:.2f}). Çeşitlendirme için mükemmel.")
                        insights_count += 1
                
                if insights_count == 0:
                    st.write("Portföy varlıkları arasında uç bir bağımlılık tespit edilmedi. Yapı sağlıklı görünüyor.")

                st.divider()
                st.caption(" **Kritik Not:** Bu analiz tarihsel verilerle hesaplanmıştır. Korelasyonlar kriz anlarında değişkenlik gösterebilir.")

                # --- Excel Export ---
                alloc_df = pd.DataFrame([
                    {"Varlık": ticker_label(t), "Ağırlık (%)": w * 100}
                    for t, w in zip(selected, final_w_list)
                ])
                metrics_df = pd.DataFrame([{
                    "Portföy VaR (95%)": f"{port_var:.4f}",
                    "Expected Shortfall": f"{port_es:.4f}",
                    "Çeşitlendirme Etkisi": f"{div_eff:.4f}",
                }])
                corr_export = corr_matrix.reset_index().rename(columns={"index": "Varlık"})
                excel = to_excel_bytes({
                    "Özet": metrics_df,
                    "Dağılım": alloc_df,
                    "Korelasyon Matrisi": corr_export,
                })
                st.download_button("Excel İndir", data=excel, file_name="portfoy_analizi.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except Exception as e:
            st.error(f"Portföy analizi sırasında bir hata oluştu: {e}")

    # --- 🤖 5. INTERAKTIF CHATBOT (SAYFA ALTINDA HER AN AKTİF) ---
    st.divider()

    # Gerçek zamanlı ağırlık verilerinin bota aktarılması
    bot_summary = st.session_state.get("last_portfolio_data") or {
        "allocation": {t: w for t, w in zip(selected, current_weights)}
    }

    # Arkadaşının chatbot bileşeni çağrılıyor
    render_portfolio_chat(bot_summary)


# --- SAYFA: KRİZ SİMÜLASYONU ---
elif page == "Kriz Simülasyonu":
    st.title("Kriz Modu Simülasyonu")
    st.markdown(
        "Portföyünüzün **2020 COVID çöküşü**, **Ukrayna savaşı** veya "
        "**Fed faiz şoku** gibi tarihsel kriz dönemlerinde nasıl performans "
        "göstereceğini simüle edin."
    )

    CRISIS_SCENARIOS = {
        "COVID-19 Mart 2020":    ("2020-02-20", "2020-03-23"),
        "Ukrayna Savaşı 2022":   ("2022-02-24", "2022-04-01"),
        "Fed Faiz Şoku 2022":    ("2022-01-01", "2022-10-31"),
        "Petrol Çöküşü 2020":    ("2020-03-01", "2020-04-30"),
    }
    CRISIS_DESC = {
        "COVID-19 Mart 2020":    "Pandemi ilanıyla küresel piyasalar 33 günde %34 geriledi.",
        "Ukrayna Savaşı 2022":   "Rusya işgaliyle enerji ve emtia piyasaları sert dalgalandı.",
        "Fed Faiz Şoku 2022":    "40 yılın en agresif faiz artış döngüsü; tahvil ve büyüme varlıkları ağır kayıp yaşadı.",
        "Petrol Çöküşü 2020":    "WTI vadeli işlemleri negatife döndü; enerji sektörü için tarihi kriz.",
        "Özel Tarih Aralığı":   "Kendi tarih aralığınızı girin.",
    }

    col_left, col_right = st.columns([1, 2], gap="large")

    #Sol panel: konfigürasyon 
        
    with col_left:
        st.subheader("1. Portföy")

        all_assets = fetch_assets()
        prev_selection = st.session_state.get("selected_assets", all_assets[:3])
        safe_defaults  = [a for a in prev_selection if a in all_assets] or all_assets[:3]

        crisis_tickers = st.multiselect(
            "Varlıklar:",
            all_assets,
            default=safe_defaults,
            format_func=ticker_label,
            key="crisis_tickers",
        )

        if not crisis_tickers:
            st.info("En az 1 varlık seçin.")
            st.stop()

        equal_w = round(100 / len(crisis_tickers), 2)
        crisis_weights = []
        for t in crisis_tickers:
            w_val = st.number_input(
                f"{ticker_label(t)} (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.get(f"cw_{t}", equal_w)),
                step=1.0,
                key=f"cw_{t}",
            )
            crisis_weights.append(w_val)

        total_cw = round(sum(crisis_weights), 2)
        if abs(total_cw - 100) < 0.1:
            st.success(f"Toplam: %{total_cw:.0f} ✓")
        else:
            st.warning(f"Toplam: %{total_cw:.1f} / 100 - tam 100 olmalı")

        st.divider()
        st.subheader("2. Senaryo")

        scenario_options = list(CRISIS_SCENARIOS.keys()) + ["Özel Tarih Aralığı"]
        selected_scenario = st.selectbox("Kriz Dönemi:", scenario_options, key="crisis_scenario")
        st.caption(CRISIS_DESC.get(selected_scenario, ""))

        if selected_scenario == "Özel Tarih Aralığı":
            scenario_start = str(st.date_input("Başlangıç:", value=pd.Timestamp("2020-02-20"), key="crisis_start"))
            scenario_end   = str(st.date_input("Bitiş:",     value=pd.Timestamp("2020-03-23"), key="crisis_end"))
        else:
            scenario_start, scenario_end = CRISIS_SCENARIOS[selected_scenario]
            st.caption(f"**{scenario_start}** → **{scenario_end}**")

        st.divider()
        weights_ok = abs(total_cw - 100) < 0.1
        run_btn = st.button(
            "Simülasyonu Çalıştır",
            type="primary",
            use_container_width=True,
            disabled=not weights_ok,
            key="crisis_run",
        )

    #  Sağ panel: sonuçlar  
    with col_right:
        if not run_btn:
            st.markdown("""
                <div style="display:flex;align-items:center;justify-content:center;
                            height:320px;border:2px dashed #142841;border-radius:12px;
                            color:#8A9BB5;font-family:'Inter',sans-serif;">
                    <div style="text-align:center">
                        <div style="font-size:52px;margin-bottom:12px;">📉</div>
                        <div>Portföyü yapılandırın ve simülasyonu başlatın</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            try:
                final_weights = [w / 100 for w in crisis_weights]
                with st.spinner(f"'{selected_scenario}' senaryosu simüle ediliyor..."):
                    result = run_stress_test(crisis_tickers, final_weights, scenario_start, scenario_end)

                cum_ret  = result["portfolio_cumulative_return"]
                max_dd   = result["max_drawdown"]
                worst    = result["worst_day"]
                best     = result["best_day"]
                n_days   = result["n_trading_days"]
                baseline = result.get("baseline_cumulative_return")
                contrib  = result["ticker_contributions"]

                # Metrik satırı
                m1, m2, m3, m4 = st.columns(4)
                ret_color = "red" if cum_ret < 0 else "green"
                m1.metric("Kümülatif Getiri",  f"%{cum_ret:.2f}")
                m2.metric("Maks. Drawdown",    f"%{max_dd:.2f}")
                m3.metric("En Kötü Gün",       f"%{worst:.2f}")
                m4.metric("Simülasyon Süresi", f"{n_days} gün")

                # Baz dönem karşılaştırması
                if baseline is not None:
                    diff = cum_ret - baseline
                    if cum_ret < 0 and baseline >= 0:
                        st.error(
                            f"Normal dönemde portföy **%{baseline:.2f}** getiri sağlarken, "
                            f"kriz döneminde **%{abs(cum_ret):.2f}** kaybetti."
                        )
                    else:
                        arrow = "▼" if diff < 0 else "▲"
                        st.info(
                            f"Normal dönem: **%{baseline:.2f}** | "
                            f"Kriz dönemi: **%{cum_ret:.2f}** | "
                            f"Fark: {arrow} **%{abs(diff):.2f}**"
                        )

                st.divider()

                # Kümülatif performans grafiği
                daily_df = pd.DataFrame(result["daily_returns"])
                daily_df["date"] = pd.to_datetime(daily_df["date"])

                line_col = "#FF4B4B" if cum_ret < 0 else "#1D9E75"
                fill_col = "rgba(255,75,75,0.08)" if cum_ret < 0 else "rgba(29,158,117,0.08)"

                fig_cum = go.Figure()
                fig_cum.add_trace(go.Scatter(
                    x=daily_df["date"],
                    y=daily_df["cumulative"],
                    mode="lines",
                    name="Kümülatif Getiri (%)",
                    line=dict(color=line_col, width=2),
                    fill="tozeroy",
                    fillcolor=fill_col,
                    hovertemplate="%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>",
                ))
                fig_cum.add_hline(y=0, line_dash="dash", line_color="#8A9BB5", opacity=0.4)
                fig_cum.update_layout(
                    title=f"{selected_scenario} - Kümülatif Portföy Performansı",
                    xaxis_title="Tarih",
                    yaxis_title="Kümülatif Getiri (%)",
                    hovermode="x unified",
                    template="plotly_dark",
                    paper_bgcolor="#0B1929",
                    plot_bgcolor="#0B1929",
                    font=dict(color="#F1EFE8"),
                )
                st.plotly_chart(fig_cum, use_container_width=True)

                # Varlık katkıları yatay bar
                contrib_sorted = sorted(contrib.items(), key=lambda x: x[1])
                bar_labels  = [ticker_label(t) for t, _ in contrib_sorted]
                bar_values  = [v for _, v in contrib_sorted]
                bar_colors  = ["#FF4B4B" if v < 0 else "#1D9E75" for v in bar_values]

                fig_bar = go.Figure(go.Bar(
                    x=bar_values,
                    y=bar_labels,
                    orientation="h",
                    marker_color=bar_colors,
                    text=[f"%{v:.2f}" for v in bar_values],
                    textposition="outside",
                    hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
                ))
                fig_bar.update_layout(
                    title="Varlık Katkıları (Ağırlıklı Kümülatif Getiri)",
                    xaxis_title="Katkı (%)",
                    template="plotly_dark",
                    paper_bgcolor="#0B1929",
                    plot_bgcolor="#0B1929",
                    font=dict(color="#F1EFE8"),
                    height=max(200, len(contrib) * 45 + 100),
                    margin=dict(l=10, r=60),
                )
                st.plotly_chart(fig_bar, use_container_width=True)

                # Risk yorumu
                worst_t = min(contrib, key=contrib.get)
                best_t  = max(contrib, key=contrib.get)
                if contrib[worst_t] < -0.01:
                    st.error(f"**En yüksek kayıp:** {ticker_label(worst_t)} → %{contrib[worst_t]:.2f}")
                if contrib[best_t] > 0.01:
                    st.success(f"**En iyi koruma:** {ticker_label(best_t)} → +%{contrib[best_t]:.2f}")
                elif best_t != worst_t:
                    st.info(f"**En az zarar eden:** {ticker_label(best_t)} → %{contrib[best_t]:.2f}")

                # Excel export
                st.divider()
                export_daily = daily_df.rename(columns={
                    "date":       "Tarih",
                    "return":     "Günlük Getiri (%)",
                    "cumulative": "Kümülatif Getiri (%)",
                })
                contrib_export_rows = []
                for t, v in contrib_sorted:
                    w_idx = crisis_tickers.index(t) if t in crisis_tickers else -1
                    w_pct = crisis_weights[w_idx] if w_idx >= 0 else 0
                    contrib_export_rows.append({"Varlık": ticker_label(t), "Ağırlık (%)": round(w_pct, 2), "Katkı (%)": v})
                metrics_row = pd.DataFrame([{
                    "Senaryo":              selected_scenario,
                    "Başlangıç":           scenario_start,
                    "Bitiş":               scenario_end,
                    "Kümülatif Getiri (%)": cum_ret,
                    "Maks. Drawdown (%)":  max_dd,
                    "En Kötü Gün (%)":     worst,
                    "En İyi Gün (%)":      best,
                    "İşlem Günü":          n_days,
                    "Baz Dönem (%)":       baseline,
                }])
                excel = to_excel_bytes({
                    "Özet":            metrics_row,
                    "Günlük Getiriler": export_daily,
                    "Varlık Katkıları": pd.DataFrame(contrib_export_rows),
                })
                st.download_button(
                    "Excel İndir",
                    data=excel,
                    file_name=f"kriz_{selected_scenario[:22].replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            except ValueError as e:
                st.error(str(e))
            except ConnectionError as e:
                st.error(str(e))
                st.code("uvicorn backend.main:app --reload", language="bash")
            except TimeoutError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Simülasyon sırasında bir hata oluştu: {e}")