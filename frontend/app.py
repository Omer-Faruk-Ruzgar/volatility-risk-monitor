import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
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
    get_news, get_sentiment_alert
)

# Profesyonel Görsel Bileşenler
from components import (
    line_chart, multi_line_chart, regime_chart, 
    var_breach_chart, summary_table, ticker_card, 
    news_card, sentiment_alert_banner
)

# Sayfa Ayarları
st.set_page_config(page_title="Volatility Risk Monitor", layout="wide")

# Ticker listesini önbellekle — her sayfa yenilenişinde tekrar çekilmez
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
    """Tüm ticker'ları sekme olarak gösterir, seçili olanı döndürür."""
    assets = fetch_assets()
    tabs = st.tabs(assets)
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
        .main-title { font-size: 42px; font-weight: bold; text-align: center; color: #1E3A5F; margin-bottom: 8px; }
        .sub-title  { font-size: 17px; text-align: center; color: #555; margin-bottom: 32px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">Volatility Risk Monitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Finansal piyasaların anlık risk durumunu ve oynaklık metriklerini tek bakışta izleyin.</div>', unsafe_allow_html=True)
    
    st.divider()

    # Canlı Ticker Kartları Bölümü
    st.subheader("Piyasa Risk Özeti")
    
    try:
        with st.spinner("Piyasa özetleri backend'den çekiliyor, lütfen bekleyin..."):
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
            st.warning("Henüz görüntülenecek veri bulunamadı. Lütfen backend bağlantısını kontrol edin.")
            
    except Exception as e:
        st.error(f"Dashboard yüklenirken bir hata oluştu: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.info(" **İpucu:** Yukarıdaki kartlar son GARCH volatilitesini gösterir. Detaylı analiz için sol menüden ilgili sekmeye geçiş yapabilirsiniz.")
    
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
        news_ticker = st.selectbox("Hisse Haberlerini İncele:", fetch_assets(), index=0)
    
    try:
        with st.spinner(f"{news_ticker} haberleri analiz ediliyor..."):
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
    st.caption("Bu platform sadece akademik amaçlıdır ve yatırım tavsiyesi içermez. Veriler 5 dakikada bir güncellenir.")


# --- SAYFA: RETURNS ---
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
            line_chart(df, x="date", y="log_return", title=f"{ticker} — Günlük Logaritmik Getiriler")

            df["cumulative"] = df["log_return"].cumsum()
            line_chart(df, x="date", y="cumulative", title=f"{ticker} — Kümülatif Log Getiri")

        except ConnectionError as e:
            st.error(f" {e}")
        except Exception as e:
            st.error(f"Hata: {e}")

    render_for_ticker(render_returns)


# --- SAYFA: VOLATILITY ---
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
            st.dataframe(stats, width='stretch', hide_index=True)

        except ConnectionError as e:
            st.error(f"{e}")
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
                st.dataframe(breach_df, width='stretch', hide_index=True)
            else:
                st.success("Seçili dönemde VaR ihlali bulunmuyor.")

        except ConnectionError as e:
            st.error(f" {e}")
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

        except ConnectionError as e:
            st.error(f" {e}")
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
    selected = st.multiselect("Portföy Varlıkları:", assets, default=safe_defaults, key="p_assets_multi")
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
            val = st.number_input(f"{t} (%)", 0.0, 100.0, value=float(st.session_state.get(f"num_{t}", def_val)), key=f"num_{t}", step=0.5)
            current_weights.append(val)

        # Canlı Toplam Göstergesi ve Renk Kodları (Issue Geliştirmesi)
        total_w = round(sum(current_weights), 2)
        if abs(total_w - 100) < 0.1:
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