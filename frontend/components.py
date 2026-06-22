import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

def line_chart(df: pd.DataFrame, x: str, y: str, title: str):
    """Genel amaçlı tek serili çizgi grafiği (Örn: Returns)"""
    fig = px.line(df, x=x, y=y, title=title)
    fig.update_layout(xaxis_title="Tarih", yaxis_title=y)
    st.plotly_chart(fig, width='stretch')


def multi_line_chart(df: pd.DataFrame, x: str, y_cols: list, title: str):
    """Birden fazla seriyi aynı grafikte gösterir (Örn: EWMA vs GARCH vs Forecast)"""
    # Sadece DataFrame'de gerçekten var olan kolonları çiz
    available = [c for c in y_cols if c in df.columns]
    if not available:
        st.warning("Gösterilecek veri bulunamadı.")
        return
    fig = px.line(df, x=x, y=available, title=title)
    fig.update_layout(xaxis_title="Tarih", yaxis_title="Volatilite", legend_title="Model")
    st.plotly_chart(fig, width='stretch')


def var_breach_chart(df: pd.DataFrame, ticker: str, method: str = "parametric"):
    """
    Getiri serisi + VaR çizgisi + ihlal noktalarını tek bir grafikte gösterir.
    df kolonları: date, return, parametric_var / historical_var, es, is_breach
    """
    var_col = "parametric_var" if method == "parametric" else "historical_var"
    label   = "Parametrik VaR" if method == "parametric" else "Tarihsel VaR"

    fig = go.Figure()

    # Getiri çizgisi (mavi)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["return"],
        name="Günlük Getiri",
        line=dict(color="steelblue", width=1),
        opacity=0.7,
    ))

    # VaR çizgisi (kırmızı kesik)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df[var_col],
        name=label,
        line=dict(color="red", width=1.5, dash="dash"),
    ))

    # ES çizgisi (turuncu kesik)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["es"],
        name="Expected Shortfall",
        line=dict(color="orange", width=1.5, dash="dot"),
    ))

    # İhlal noktaları (kırmızı daire)
    breach_col = "is_breach" if "is_breach" in df.columns else "breach"
    if breach_col in df.columns:
        breaches = df[df[breach_col]]
        if not breaches.empty:
            fig.add_trace(go.Scatter(
                x=breaches["date"], y=breaches["return"],
                mode="markers",
                name=f"VaR İhlali ({len(breaches)})",
                marker=dict(color="red", size=6, symbol="circle"),
            ))

    fig.update_layout(
        title=f"{ticker} — Getiri vs VaR (%95 Güven Aralığı)",
        xaxis_title="Tarih",
        yaxis_title="Günlük Getiri",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    st.plotly_chart(fig, width='stretch')


def summary_table(df: pd.DataFrame, title: str = ""):
    """Verileri şık bir tablo olarak gösterir"""
    if title:
        st.subheader(title)
    st.dataframe(df, width='stretch')


def ticker_card(ticker: str, garch_vol: float, delta: float, status: str):
    """
    Koyfin stili dinamik hisse özet kartı.
    Görünüm: Ticker Adı | Son Volatilite | Değişim | Durum Badge
    """
    if status == "Ekstrem":
        color = "#FF4B4B"  # Kırmızı
        bg_color = "rgba(255, 75, 75, 0.1)"
        badge = " EKSTREM"
    elif status == "Yüksek":
        color = "#FFA500"  # Turuncu
        bg_color = "rgba(255, 165, 0, 0.1)"
        badge = " YÜKSEK"
    else:
        color = "#28A745"  # Yeşil
        bg_color = "rgba(40, 167, 69, 0.1)"
        badge = " NORMAL"

    delta_icon = "▲" if delta > 0 else "▼"
    delta_color = "red" if delta > 0 else "green"

    st.markdown(f"""
        <div style="
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            border-left: 5px solid {color};
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 10px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; font-size: 1.1rem; color: #1E3A5F;">{ticker}</span>
                <span style="font-size: 0.8rem; font-weight: bold; color: {color}; background-color: {bg_color}; padding: 2px 8px; border-radius: 15px;">{badge}</span>
            </div>
            <div style="margin-top: 10px;">
                <span style="font-size: 1.5rem; font-weight: bold; color: #333;">%{garch_vol*100:.2f}</span>
                <span style="font-size: 0.9rem; color: {delta_color}; margin-left: 8px;">
                    {delta_icon} {abs(delta*100):.2f}
                </span>
            </div>
            <div style="font-size: 0.75rem; color: #666; margin-top: 5px;">Son GARCH Volatilitesi</div>
        </div>
    """, unsafe_allow_html=True)


def regime_chart(df: pd.DataFrame, ticker: str):
    """Tarihsel Olaylar ve Volatilite Rejimleri (Karanlık Tema)"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    
    fig = go.Figure()

    # 1. Ana GARCH Çizgisi
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["GARCH"],
        name="GARCH Volatilitesi",
        line=dict(color="#00D4FF", width=2)
    ))

    # 2. Eşik Değerleri
    avg_vol = df["GARCH"].mean()
    extreme_thresh = avg_vol * 1.5
    
    fig.add_hline(y=extreme_thresh, line_dash="dot", 
                  annotation_text="Ekstrem Eşik", 
                  line_color="red", opacity=0.5)

    # 3. Önemli Olaylar (Annotations)
    events = [
        {"date": "2020-03-16", "text": "COVID-19", "color": "#FF4B4B"},
        {"date": "2022-02-24", "text": "Ukrayna", "color": "#FFAC1C"}
    ]

    for event in events:
        event_dt = pd.to_datetime(event["date"])
        if df["date"].min() <= event_dt <= df["date"].max():
            idx = (df["date"] - event_dt).abs().idxmin()
            y_val = df.loc[idx, "GARCH"]
            
            fig.add_annotation(
                x=event_dt, y=y_val,
                text=event["text"],
                showarrow=True, arrowhead=1,
                arrowcolor=event["color"],
                bgcolor="rgba(255,255,255,0.8)",
                font=dict(color="black", size=10)
            )

    fig.update_layout(
        title=f"<b>{ticker} Volatilite Rejimleri ve Kriz Dönemleri</b>",
        template="plotly_dark",
        height=500,
        xaxis_title="Tarih",
        yaxis_title="Oynaklık",
        hovermode="x unified"
    )
    st.plotly_chart(fig, width='stretch')


# ---  YENİ EKLEME: HABER VE SENTIMENT BİLEŞENLERİ ---

def sentiment_badge(label: str) -> str:
    """Sentiment etiketine veya skoruna göre renkli HTML badge döndürür."""
    colors = {
        "positive": "#28A745",  # Yeşil
        "negative": "#FF4B4B",  # Kırmızı
        "neutral":  "#FFA500"   # Turuncu
    }
    
    # Gelen veri sayısal string ise dinamik analiz et
    try:
        val = float(label)
        if val > 0.05: color_label, color = "POSITIVE", "#28A745"
        elif val < -0.05: color_label, color = "NEGATIVE", "#FF4B4B"
        else: color_label, color = "NEUTRAL", "#FFA500"
    except ValueError:
        color_label = label.upper()
        color = colors.get(label, "#888")

    return f"""
        <span style="
            background-color: {color}22; 
            color: {color}; 
            padding: 2px 10px; 
            border-radius: 12px; 
            border: 1px solid {color}; 
            font-size: 0.7rem; 
            font-weight: bold;
            display: inline-block;">
            {color_label}
        </span>
    """


def news_card(item: dict):
    """Tek bir haber kartını sol kenarlık duygu rengiyle render eder (Issue Tasarım Kararı)."""
    try:
        dt_object = datetime.fromtimestamp(item.get('datetime', 0))
        formatted_date = dt_object.strftime('%d %b %H:%M')
    except Exception:
        formatted_date = "Bilinmiyor"
    
    sentiment = item.get('sentiment_label', 'neutral')
    
    if isinstance(sentiment, (int, float)):
        border_color = "#28A745" if sentiment > 0.05 else ("#FF4B4B" if sentiment < -0.05 else "#FFA500")
        sentiment_text = str(sentiment)
    else:
        border_colors = {"Positive": "#28A745", "Negative": "#FF4B4B", "Neutral": "#FFA500"}
        border_color = border_colors.get(sentiment, "#888")
        sentiment_text = sentiment

    st.markdown(f"""
        <div style="
            border-left: 5px solid {border_color};
            background-color: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 12px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="color: #aaa; font-size: 0.8rem; font-weight: 500;">{item.get('source', 'KAYNAK')} • {formatted_date}</span>
                {sentiment_badge(sentiment_text)}
            </div>
            <a href="{item.get('url', '#')}" target="_blank" style="text-decoration: none; color: #e0e0e0; font-weight: bold; font-size: 1rem; line-height: 1.4; display: block;">
                {item.get('headline', 'Başlık bulunamadı')}
            </a>
        </div>
    """, unsafe_allow_html=True)


def sentiment_alert_banner(alert: dict):
    """Kritik piyasa uyarı banner'ını 4 metrik kolonuyla render eder."""
    if not alert or not alert.get("should_warn"):
        st.success(" **Piyasa Durumu:** Olağandışı bir duygu baskısı veya volatilite saptanmadı.")
        return

    score = alert.get("sentiment_score", 0)
    container = st.error if score < -0.5 else st.warning

    with container(f" **Kritik Piyasa Alarmı:** {alert.get('reason', 'Yüksek Risk Seviyesi')}"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Duygu Skoru", f"{score:.2f}")
        c2.metric("Negatif Haber", alert.get('negative_news_count', 0))
        c3.metric("Anlık Volatilite", f"{alert.get('current_vol', 0):.4f}")
        c4.metric("Vol. Yüzdelik", f"%{alert.get('vol_percentile', 0)}")