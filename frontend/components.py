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
    fig = px.line(df, x=x, y=available, title=title,
                  color_discrete_sequence=["#E8A33D", "#1D9E75", "#5B9BD5"])
    fig.update_layout(xaxis_title="Tarih", yaxis_title="Volatilite", legend_title="Model", **_CHART_LAYOUT)
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
        title=f"{ticker} - Getiri vs VaR (%95 Güven Aralığı)",
        xaxis_title="Tarih",
        yaxis_title="Günlük Getiri",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        **_CHART_LAYOUT,
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
                <span style="font-weight: bold; font-size: 1.1rem; color: #E8A33D;">{ticker}</span>
                <span style="font-size: 0.75rem; font-weight: bold; color: {color}; background-color: {bg_color}; padding: 2px 10px; border-radius: 12px; border: 1px solid {color};">{badge}</span>
            </div>
            <div style="margin-top: 10px;">
                <span style="font-size: 1.5rem; font-weight: bold; color: #F1EFE8; font-family: 'IBM Plex Mono', monospace;">%{garch_vol*100:.2f}</span>
                <span style="font-size: 0.9rem; color: {delta_color}; margin-left: 8px;">
                    {delta_icon} {abs(delta*100):.2f}
                </span>
            </div>
            <div style="font-size: 0.75rem; color: #8A9BB5; margin-top: 5px;">Son GARCH Volatilitesi</div>
        </div>
    """, unsafe_allow_html=True)


def regime_chart(df: pd.DataFrame, ticker: str, show_opec: bool = True):
    """Tarihsel Olaylar ve Volatilite Rejimleri - OPEC kararları opsiyonel."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    fig = go.Figure()

    # 1. Ana GARCH Çizgisi
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["GARCH"],
        name="GARCH Volatilitesi",
        line=dict(color="#00D4FF", width=2),
    ))

    # 2. Ekstrem eşik yatay çizgisi
    avg_vol = df["GARCH"].mean()
    extreme_thresh = avg_vol * 1.5
    fig.add_hline(
        y=extreme_thresh,
        line_dash="dot",
        line_color="#FF4B4B",
        opacity=0.45,
        annotation_text="Ekstrem Eşik",
        annotation=dict(font=dict(size=9, color="#FF4B4B")),
    )

    # 3. Makro olaylar (nokta + ok)
    macro_events = [
        {"date": "2020-03-16", "text": "COVID-19", "color": "#FF4B4B"},
        {"date": "2022-02-24", "text": "Ukrayna",  "color": "#FFAC1C"},
    ]
    for ev in macro_events:
        ev_dt = pd.to_datetime(ev["date"])
        if df["date"].min() <= ev_dt <= df["date"].max():
            idx   = (df["date"] - ev_dt).abs().idxmin()
            y_val = df.loc[idx, "GARCH"]
            fig.add_annotation(
                x=ev_dt, y=y_val,
                text=ev["text"],
                showarrow=True, arrowhead=2, arrowwidth=1.5,
                arrowcolor=ev["color"],
                bgcolor="rgba(11,25,41,0.85)",
                font=dict(color=ev["color"], size=10),
                bordercolor=ev["color"], borderwidth=1, borderpad=3,
            )

    # 4. OPEC karar çizgileri
    if show_opec:
        date_min, date_max = df["date"].min(), df["date"].max()
        in_range = [
            e for e in OPEC_EVENTS
            if date_min <= pd.to_datetime(e["date"]) <= date_max
        ]
        for i, ev in enumerate(in_range):
            color = _OPEC_COLORS.get(ev["type"], "#E8A33D")
            # Pozisyonları sırayla alt-üst değiştirerek annotation çakışmasını azalt
            pos = "top left" if i % 2 == 0 else "top right"
            fig.add_vline(
                x=ev["date"],
                line_width=1.2,
                line_dash="dot",
                line_color=color,
                opacity=0.65,
                annotation_text=ev["short"],
                annotation_position=pos,
                annotation=dict(
                    font=dict(size=8, color=color),
                    bgcolor="rgba(11,25,41,0.82)",
                    bordercolor=color,
                    borderpad=2,
                    borderwidth=1,
                ),
            )

    fig.update_layout(
        title=f"<b>{ticker} Volatilite Rejimleri ve Tarihsel Olaylar</b>",
        template="plotly_dark",
        paper_bgcolor="#0B1929",
        plot_bgcolor="#0B1929",
        font=dict(color="#F1EFE8"),
        height=520,
        xaxis_title="Tarih",
        yaxis_title="Oynaklık (GARCH)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, width='stretch')


# ---  HABER VE SENTIMENT BİLEŞENLERİ ---

def _sentiment_display(sentiment) -> tuple[str, str]:
    """Sentiment değerinden (label veya float) gösterim metni ve renk döndürür."""
    if isinstance(sentiment, (int, float)):
        if sentiment > 0.05:   return "● POZİTİF", "green"
        if sentiment < -0.05:  return "● NEGATİF", "red"
        return "● NÖTR", "orange"
    mapping = {
        "positive": ("● POZİTİF", "green"),
        "negative": ("● NEGATİF", "red"),
        "neutral":  ("● NÖTR",    "orange"),
    }
    return mapping.get(str(sentiment).lower(), ("● NÖTR", "orange"))


def news_card(item: dict):
    """Haber kartını native Streamlit container ile render eder."""
    try:
        formatted_date = datetime.fromtimestamp(item.get('datetime', 0)).strftime('%d %b %H:%M')
    except Exception:
        formatted_date = "Bilinmiyor"

    badge_text, badge_color = _sentiment_display(item.get('sentiment_label', 'neutral'))
    headline = item.get('headline', 'Başlık bulunamadı')
    url      = item.get('url', '#')
    source   = item.get('source', 'Kaynak')

    with st.container(border=True):
        c_meta, c_badge = st.columns([3, 1])
        c_meta.caption(f"**{source}** • {formatted_date}")
        c_badge.markdown(f"<div style='text-align:right'>:{badge_color}[**{badge_text}**]</div>", unsafe_allow_html=True)
        st.markdown(f"[{headline}]({url})")


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