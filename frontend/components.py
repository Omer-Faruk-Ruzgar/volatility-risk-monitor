import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

#  OPEC Karar Veritabanı
# Tarihler grafiklerde dikey çizgi olarak işaretlenir.
# type: "cut" (amber) | "increase" (teal) | "collapse" (kırmızı)
OPEC_EVENTS = [
    {"date": "2016-11-30", "short": "Viyana '16",         "detail": "OPEC Viyana Anlaşması: 8 yıl sonra ilk üretim kesintisi (−1.2M bpd)",       "type": "cut"},
    {"date": "2018-06-22", "short": "Üretim Artışı '18",  "detail": "OPEC+ İran/Venezuela telafisi için üretim artışı",                            "type": "increase"},
    {"date": "2019-12-06", "short": "Kesinti Derinleşme", "detail": "OPEC+ toplantısı: kesinti 1.7M bpd'ye derinleştirildi",                       "type": "cut"},
    {"date": "2020-03-06", "short": "Fiyat Savaşı '20",   "detail": "OPEC+ görüşmeleri çöktü; Suudi Arabistan-Rusya fiyat savaşı başladı",         "type": "collapse"},
    {"date": "2020-04-09", "short": "Tarihi Anlaşma '20", "detail": "G20 baskısıyla tarihi OPEC+ anlaşması: 9.7M bpd kesinti (COVID yanıtı)",     "type": "cut"},
    {"date": "2021-07-18", "short": "Üretim Artışı '21",  "detail": "OPEC+ aylık 400k bpd artış anlaşması",                                        "type": "increase"},
    {"date": "2022-10-05", "short": "−2M bpd '22",        "detail": "OPEC+ 2M bpd üretim kesintisi (ABD ara seçimleri öncesi, yüksek enflasyon)", "type": "cut"},
    {"date": "2023-04-02", "short": "Suudi Sürprizi '23", "detail": "Suudi Arabistan 500k bpd gönüllü ek kesinti açıkladı (piyasayı şaşırttı)",   "type": "cut"},
    {"date": "2023-11-30", "short": "Uzatma '23",          "detail": "OPEC+ kesintilerini Q1 2024'e uzattı; Suudi ek kesintisi devam etti",         "type": "cut"},
    {"date": "2024-06-02", "short": "2025'e Uzatma",       "detail": "OPEC+ toplantısı: kesintiler 2025 sonuna kadar uzatıldı",                    "type": "cut"},
]

_OPEC_COLORS = {
    "cut":      "#E8A33D",  # amber: üretim kesintisi (fiyat destekleyici)
    "increase": "#1D9E75",  # teal: üretim artışı
    "collapse": "#FF4B4B",  # kırmızı: çöküş / kriz
}

_CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0B1929",
    plot_bgcolor="#0B1929",
    font=dict(color="#F1EFE8"),
)

def line_chart(df: pd.DataFrame, x: str, y: str, title: str):
    """Genel amaçlı tek serili çizgi grafiği (Örn: Returns)"""
    fig = px.line(df, x=x, y=y, title=title, color_discrete_sequence=["#E8A33D"])
    fig.update_layout(xaxis_title="Tarih", yaxis_title=y, **_CHART_LAYOUT)
    st.plotly_chart(fig, width='stretch')


def multi_line_chart(df: pd.DataFrame, x: str, y_cols: list, title: str):
    """Birden fazla seriyi aynı grafikte gösterir (Örn: EWMA vs GARCH vs Forecast)"""
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
    Bloomberg tarzı dinamik hisse özet kartı - lacivert + amber tema.
    """
    if status == "Ekstrem":
        color    = "#FF4B4B"
        bg_color = "rgba(255, 75, 75, 0.12)"
        badge    = "EKSTREM"
    elif status == "Yüksek":
        color    = "#E8A33D"
        bg_color = "rgba(232, 163, 61, 0.12)"
        badge    = "YÜKSEK"
    else:
        color    = "#1D9E75"
        bg_color = "rgba(29, 158, 117, 0.12)"
        badge    = "NORMAL"

    delta_icon  = "▲" if delta > 0 else "▼"
    delta_color = "#FF4B4B" if delta > 0 else "#1D9E75"

    st.markdown(f"""
        <div style="
            background-color: #142841;
            border-radius: 10px;
            padding: 15px;
            border-left: 4px solid {color};
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
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
        _BADGE_HEX = {"green": "#1D9E75", "red": "#FF4B4B", "orange": "#E8A33D"}
        hex_color = _BADGE_HEX.get(badge_color, "#9FB3C8")
        c_badge.markdown(
            f"<div style='text-align:right'><span style='color:{hex_color};font-weight:600;font-size:0.8rem;'>{badge_text}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"[{headline}]({url})")


def geo_risk_map(regions: dict):
    """
    Jeopolitik risk gostergesi: Scattergeo ile dunya haritasinda
    bolge bazli gerilim skorlarini renk ve boyut olarak gosterir.
    Renk skalasi mevcut Bloomberg temasiyla tutarlidir.
    """
    if not regions:
        st.info("Risk bolgesi verisi alinamamadi.")
        return

    labels  = [r["label"]  for r in regions.values()]
    lats    = [r["lat"]    for r in regions.values()]
    lons    = [r["lon"]    for r in regions.values()]
    scores  = [r["score"]  for r in regions.values()]

    fig = go.Figure(go.Scattergeo(
        lat=lats,
        lon=lons,
        text=labels,
        customdata=scores,
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Gerilim Skoru: %{customdata:.1f}/10<extra></extra>"
        ),
        mode="markers+text",
        textposition="top center",
        textfont=dict(color="#F1EFE8", size=11, family="Inter"),
        marker=dict(
            size=[10 + s * 3 for s in scores],
            color=scores,
            colorscale=[
                [0.0, "#1D9E75"],
                [0.4, "#E8A33D"],
                [0.7, "#E0524F"],
                [1.0, "#B91C1C"],
            ],
            cmin=0,
            cmax=10,
            colorbar=dict(
                title=dict(text="Gerilim", font=dict(color="#9FB3C8")),
                tickfont=dict(color="#9FB3C8"),
            ),
            line=dict(width=1, color="#0B1929"),
        ),
    ))

    fig.update_geos(
        bgcolor="#0B1929",
        landcolor="#142841",
        showocean=True,
        oceancolor="#0B1929",
        showcountries=True,
        countrycolor="#1F3A5C",
        showcoastlines=True,
        coastlinecolor="#1F3A5C",
        projection_type="natural earth",
    )
    fig.update_layout(
        paper_bgcolor="#0B1929",
        margin=dict(l=0, r=0, t=10, b=0),
        height=380,
        geo=dict(
            center=dict(lat=25, lon=20),
            projection_scale=1.1,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Bolge detay kartlari
    cols = st.columns(2)
    for i, (region_id, r) in enumerate(regions.items()):
        score_color = (
            "#B91C1C" if r["score"] >= 7
            else "#E0524F" if r["score"] >= 4
            else "#E8A33D" if r["score"] >= 2
            else "#1D9E75"
        )
        hl_info = f' ({r["headline_count"]} haber)' if r.get("headline_count", 0) > 0 else " (veri yok)"
        with cols[i % 2]:
            st.markdown(
                f'<div style="background:#142841; border-radius:8px; '
                f'padding:10px 12px; margin-bottom:8px; '
                f'border-left:3px solid {score_color};">'
                f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                f'<span style="font-size:12px; font-weight:600; color:#F1EFE8;">{r["label"]}</span>'
                f'<span style="font-size:16px; font-weight:700; color:{score_color};">'
                f'{r["score"]:.1f}<span style="font-size:10px; color:#8A9BB5;">/10</span></span>'
                f'</div>'
                f'<div style="font-size:9px; color:#8A9BB5; margin-top:4px;">'
                f'{", ".join(r["tickers"])}{hl_info}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.caption(
        "GLD, TLT ve SPY belirli bir bolgeden bagimsiz olmakla birlikte "
        "bu dort bolgenin toplam risk etkisine tepki verebilir. "
        "Skor hesabi: VADER compound ortalamasi, negatif taraf 0-10 araligina olceklendi."
    )


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