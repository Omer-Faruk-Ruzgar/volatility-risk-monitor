import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine

#  OPEC Karar Veritabanı
# type: "cut" (amber) | "increase" (teal) | "collapse" (kirmizi)
# bpd_magnitude: bin bpd (kbpd) cinsinden buyukluk -- intensity bar icin
# episode: ardisik stratejik grup etiketi -- gruplama icin
# trigger: kisa tetikleyici aciklama -- expandable detay icin
OPEC_EVENTS = [
    {
        "date": "2016-11-30", "short": "Viyana '16",
        "detail": "OPEC Viyana Anlasması: 8 yil sonra ilk uretim kesintisi",
        "type": "cut", "bpd_magnitude": 1200, "episode": "vienna_series",
        "trigger": "WTI ~45$/varil seviyesinde uzun suren dusuk fiyat; Suudi Arabistan ve Rusya uzlasma zorunlulugu hissetti.",
    },
    {
        "date": "2018-06-22", "short": "Uretim Artisi '18",
        "detail": "OPEC+ Iran/Venezuela telafisi icin uretim artisi (~1M bpd)",
        "type": "increase", "bpd_magnitude": 1000, "episode": "2018_adjustment",
        "trigger": "ABD'nin Iran yaptirimlari ve Venezuela uretim cokmesi sonrasi arz acigi riski; WTI 75$/varil ustune cikti.",
    },
    {
        "date": "2019-12-06", "short": "Kesinti Derinlesme",
        "detail": "OPEC+ toplantisi: kesinti 1.7M bpd'ye derinlestirildi",
        "type": "cut", "bpd_magnitude": 1700, "episode": "2019_deepening",
        "trigger": "Kuresel ekonomi yavaslama endisesi ve ABD seyil uretimindeki hizli artis; 2020 ilk ceyrek icin savunmaci pozisyon.",
    },
    {
        "date": "2020-03-06", "short": "Fiyat Savasi '20",
        "detail": "OPEC+ gorusmeleri coktu; Suudi Arabistan-Rusya fiyat savasi basladi",
        "type": "collapse", "bpd_magnitude": 0, "episode": "covid_crisis",
        "trigger": "Rusya'nin OPEC+ kesinti teklifini reddetmesi uzerine Suudi Arabistan maksimum uretim politikasina gecti; COVID talep soku ile cakisti.",
    },
    {
        "date": "2020-04-09", "short": "Tarihi Anlasma '20",
        "detail": "G20 baskisiyla tarihi OPEC+ anlasması: 9.7M bpd kesinti",
        "type": "cut", "bpd_magnitude": 9700, "episode": "covid_crisis",
        "trigger": "COVID-19 talep cokmesi kuresel talebi -30M bpd dusurdu; ABD, Kanada ve Rusya da katilmasiyla G20 koordinasyonu saglandi.",
    },
    {
        "date": "2021-07-18", "short": "Uretim Artisi '21",
        "detail": "OPEC+ aylik 400k bpd artis anlasması (kademeli normallesme)",
        "type": "increase", "bpd_magnitude": 400, "episode": "recovery",
        "trigger": "COVID sonrasi ekonomilerin acilmasiyla talep toparlandı; Delta varyanti riski altinda temkinli adimlarla uretim artisi.",
    },
    {
        "date": "2022-10-05", "short": "-2M bpd '22",
        "detail": "OPEC+ 2M bpd uretim kesintisi (ABD ara secimleri oncesi, yuksek enflasyon)",
        "type": "cut", "bpd_magnitude": 2000, "episode": "2022_extension",
        "trigger": "Fed faiz artislarinin petrol talebini frenleyecegi ve resesyon endisesi; WTI 90$/varil'den 80$/varil'e gerilemisti.",
    },
    {
        "date": "2023-04-02", "short": "Suudi Surprizi '23",
        "detail": "Suudi Arabistan 500k bpd gonullu ek kesinti acikladi (piyasayi sasirtti)",
        "type": "cut", "bpd_magnitude": 500, "episode": "2022_extension",
        "trigger": "SVB ve Credit Suisse krizlerinin ardindan petrol fiyati 70$/varil altina indi; Suudi Arabistan onceden haber vermeden hamlede bulundu.",
    },
    {
        "date": "2023-11-30", "short": "Uzatma '23",
        "detail": "OPEC+ kesintilerini Q1 2024'e uzatti; Suudi ek kesintisi devam etti",
        "type": "cut", "bpd_magnitude": 2200, "episode": "2022_extension",
        "trigger": "Cin ekonomisinin beklentilerin altinda kalmasi ve dolar gucu petrol talebini basti; anlasmadan once fiyatlar -4% gerilemisti.",
    },
    {
        "date": "2024-06-02", "short": "2025'e Uzatma",
        "detail": "OPEC+ toplantisi: kumulatif kesintiler 2025 sonuna kadar uzatildi",
        "type": "cut", "bpd_magnitude": 3660, "episode": "2022_extension",
        "trigger": "ABD seyil petrol uretimi rekor seviyede; kuresel talep belirsizligi ve non-OPEC+ uretim artisi altinda fiyat savunma stratejisi.",
    },
]

_OPEC_COLORS = {
    "cut":      "#E8A33D",
    "increase": "#1D9E75",
    "collapse": "#FF4B4B",
}

# Episode gruplama metadatasi: etiket ve renk
_EPISODE_META = {
    "vienna_series":   ("Vienna Anlasma Serisi",      "#5B9BD5"),
    "2018_adjustment": ("2018 Uretim Duzenlenmesi",   "#9FB3C8"),
    "2019_deepening":  ("2019 Derinlestirme",          "#E8A33D"),
    "covid_crisis":    ("COVID Krizi",                 "#FF4B4B"),
    "recovery":        ("Toparlanma Donemi",            "#1D9E75"),
    "2022_extension":  ("Kesinti Genisletme Serisi",   "#E8A33D"),
}

# Episode siralamasi (dict ekleme sirasi Python 3.7+ garantisi yok; liste tut)
_EPISODE_ORDER = [
    "vienna_series", "2018_adjustment", "2019_deepening",
    "covid_crisis", "recovery", "2022_extension",
]

def _bpd_label(bpd_k: int) -> str:
    """bpd_magnitude (kbpd) degerini okunakli etikete donusturur."""
    if bpd_k == 0:
        return "Anlasmasiz"
    if bpd_k >= 1000:
        return f"{bpd_k / 1000:.1f}M bpd"
    return f"{bpd_k}k bpd"


def _bpd_intensity(bpd_k: int) -> tuple:
    """bpd_magnitude'e gore (border_px, opacity) dondurur."""
    if bpd_k == 0:
        return 6, 1.0    # collapse: tam dolu, kalin
    if bpd_k < 500:
        return 3, 0.45   # dusuk: ince, soluk
    if bpd_k < 2000:
        return 5, 0.70   # orta
    return 8, 1.0        # yuksek: kalin, parlak


@st.cache_data(ttl=86400)
def compute_opec_market_reactions() -> dict:
    """
    Her OPEC karari tarihinden sonra T+1 ve kumulatif 5 gunluk
    USO/BNO log-return tepkilerini log_returns tablosundan hesaplar.
    Sonuclar gun sonunda guncellendiginden TTL 24 saat.
    """
    db_path = Path(__file__).resolve().parent.parent / "data" / "market.db"
    try:
        engine = create_engine(f"sqlite:///{db_path}")
        df = pd.read_sql("SELECT * FROM log_returns", engine, parse_dates=["Date"])
        df = df.set_index("Date").sort_index()
    except Exception:
        return {}

    reactions = {}
    for event in OPEC_EVENTS:
        date = pd.Timestamp(event["date"])
        after = df[df.index > date].head(5)
        if after.empty:
            reactions[event["date"]] = None
            continue
        def _col(col, i=0):
            return float(after[col].iloc[i]) if col in after.columns and len(after) > i else None
        reactions[event["date"]] = {
            "uso_t1": _col("USO", 0),
            "bno_t1": _col("BNO", 0),
            "uso_5d": float(after["USO"].sum()) if "USO" in after.columns else None,
            "bno_5d": float(after["BNO"].sum()) if "BNO" in after.columns else None,
            "n_days": len(after),
        }
    return reactions


def opec_decision_table(events: list):
    """
    OPEC kararlarini episode bazli gruplar halinde gosterir.
    Her satirda:
      - Sol: bpd buyuklugune gore intensity bar (kalin/ince, parlak/soluk)
      - Baslik: tarih + tur etiketi + bpd rozeti
      - Acilabilir: tetikleyici aciklama + T+1/5g USO-BNO piyasa tepkisi metrikleri
    """
    reactions = compute_opec_market_reactions()
    type_labels = {"cut": "Kesinti", "increase": "Artis", "collapse": "Cokus/Kriz"}

    # Episodlara gore grupla
    grouped: dict = {}
    for ep in _EPISODE_ORDER:
        grouped[ep] = [e for e in events if e.get("episode") == ep]

    for ep_key in _EPISODE_ORDER:
        ep_events = grouped.get(ep_key, [])
        if not ep_events:
            continue
        ep_label, ep_color = _EPISODE_META.get(ep_key, (ep_key, "#9FB3C8"))

        # Episode baslik
        st.markdown(
            f'<div style="background:linear-gradient(90deg,{ep_color}28 0%,transparent 100%);'
            f'border-left:3px solid {ep_color};padding:5px 12px;margin:14px 0 5px 0;'
            f'border-radius:0 4px 4px 0;">'
            f'<span style="color:{ep_color};font-size:10px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.1em;">'
            f'{ep_label} -- {len(ep_events)} karar'
            f'</span></div>',
            unsafe_allow_html=True,
        )

        for ev in ep_events:
            type_color = _OPEC_COLORS.get(ev["type"], "#E8A33D")
            type_label = type_labels.get(ev["type"], ev["type"])
            bpd_k      = ev.get("bpd_magnitude", 0)
            bar_px, bar_op = _bpd_intensity(bpd_k)
            bpd_text   = _bpd_label(bpd_k)
            trigger    = ev.get("trigger", "")
            rx         = reactions.get(ev["date"])

            # Kalin/ince border intensitysini rgba ile goster
            r_hex = type_color.lstrip("#")
            r, g, b = int(r_hex[0:2], 16), int(r_hex[2:4], 16), int(r_hex[4:6], 16)
            border_color = f"rgba({r},{g},{b},{bar_op})"

            # bpd rozeti (collapse icin gosterme)
            bpd_badge = ""
            if bpd_k > 0:
                bpd_badge = (
                    f'<span style="background:{type_color}22;border:1px solid {type_color}55;'
                    f'border-radius:4px;padding:1px 7px;font-size:10px;color:{type_color};'
                    f'font-family:\'IBM Plex Mono\',monospace;margin-left:6px;">'
                    f'{bpd_text}</span>'
                )

            st.markdown(
                f'<div style="border-left:{bar_px}px solid {border_color};'
                f'background:#0D1E30;border-radius:0 6px 6px 0;'
                f'padding:9px 14px 6px 14px;margin-bottom:3px;">'
                f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:5px;">'
                f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:11px;'
                f'color:#9FB3C8;">{ev["date"]}</span>'
                f'<span style="background:{type_color}33;border:1px solid {type_color}66;'
                f'border-radius:4px;padding:1px 8px;font-size:10px;font-weight:700;'
                f'color:{type_color};">{type_label}</span>'
                f'{bpd_badge}'
                f'</div>'
                f'<div style="color:#D8D0C4;font-size:12px;line-height:1.4;">{ev["detail"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            with st.expander("Tetikleyici ve Piyasa Tepkisi"):
                if trigger:
                    st.markdown(
                        f'<div style="font-size:12px;color:#B0C4D8;margin-bottom:10px;">'
                        f'<span style="color:#6A8AAA;font-size:10px;text-transform:uppercase;'
                        f'letter-spacing:0.07em;">Tetikleyici  </span>{trigger}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if rx:
                    def _pct(v):
                        return f"{v:+.1%}" if v is not None else "Veri yok"
                    def _delta(v):
                        return float(f"{v:.4f}") if v is not None else None

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("T+1 USO", _pct(rx["uso_t1"]),
                              delta=_delta(rx["uso_t1"]),
                              delta_color="normal")
                    c2.metric("T+1 BNO", _pct(rx["bno_t1"]),
                              delta=_delta(rx["bno_t1"]),
                              delta_color="normal")
                    c3.metric(f"5g USO (n={rx['n_days']})", _pct(rx["uso_5d"]),
                              delta=_delta(rx["uso_5d"]),
                              delta_color="normal")
                    c4.metric(f"5g BNO (n={rx['n_days']})", _pct(rx["bno_5d"]),
                              delta=_delta(rx["bno_5d"]),
                              delta_color="normal")
                    st.caption(
                        "Log-return bazli kumulatif hesap. T+1: karari izleyen ilk islem gunu. "
                        "5g: sonraki 5 islem gununde USO/BNO toplam log-return."
                    )
                else:
                    st.caption("Bu tarih icin fiyat verisi mevcut degil veya hesaplanamadi.")


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


_EVENT_TYPE_STYLE = {
    "VaR Ihlali":     ("FF4B4B", "VaR Ihlali"),
    "Volatilite Spike": ("E8A33D", "Volatilite Spike"),
}


def risk_event_card(event: dict):
    """Risk olayi karti: tarih, olay tipi etiketleri, GARCH/getiri degerleri ve eslesen haberler."""
    date_str    = event.get("date", "")
    event_types = event.get("event_types", [])
    garch_vol   = event.get("garch_vol")
    return_val  = event.get("return_value")
    news_items  = event.get("news", [])
    has_archive = event.get("has_archive", False)

    type_badges_html = ""
    for etype in event_types:
        hex_c, label = _EVENT_TYPE_STYLE.get(etype, ("9FB3C8", etype))
        type_badges_html += (
            f"<span style='background:#{hex_c}22;color:#{hex_c};"
            f"border:1px solid #{hex_c}55;border-radius:4px;"
            f"padding:2px 8px;font-size:0.73rem;font-weight:600;"
            f"margin-right:6px;'>{label}</span>"
        )

    metric_parts = []
    if garch_vol is not None:
        metric_parts.append(
            f"GARCH Vol: <span style='color:#E8A33D;font-weight:600;'>{garch_vol:.2%}</span>"
        )
    if return_val is not None:
        ret_hex = "1D9E75" if return_val >= 0 else "FF4B4B"
        metric_parts.append(
            f"Getiri: <span style='color:#{ret_hex};font-weight:600;'>{return_val:.4f}</span>"
        )
    metric_html = (
        "<div style='margin:4px 0 8px 0;font-size:0.8rem;color:#9FB3C8;'>"
        + " &nbsp;|&nbsp; ".join(metric_parts)
        + "</div>"
        if metric_parts else ""
    )

    with st.container(border=True):
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:2px;'>"
            f"<span style='color:#9FB3C8;font-size:0.85rem;font-weight:600;'>{date_str}</span>"
            f"{type_badges_html}</div>",
            unsafe_allow_html=True,
        )
        if metric_html:
            st.markdown(metric_html, unsafe_allow_html=True)

        if news_items:
            for item in news_items:
                news_card(item)
        elif has_archive:
            st.caption("Bu tarih icin iliskilendirilmis haber bulunamadi.")
        else:
            st.caption("Bu tarih icin haber arsivi mevcut degil (Finnhub ucretsiz plan siniri).")


def _geo_risk_level(score: float) -> tuple:
    """Skora gore risk seviyesi etiketi ve rengi dondurur."""
    if score >= 7:
        return "Kritik", "#B91C1C"
    elif score >= 4:
        return "Yuksek", "#E0524F"
    elif score >= 2:
        return "Orta", "#E8A33D"
    return "Dusuk", "#1D9E75"


def geo_risk_map(regions: dict):
    """
    Jeopolitik risk gostergesi: Scattergeo ile dunya haritasinda
    8 bolge bazli gerilim skorlarini renk ve boyut olarak gosterir.
    Kartlarda eslesen haber basliklari ve bolge aciklamalari yer alir.
    """
    if not regions:
        st.info("Risk bolgesi verisi alinamamadi.")
        return

    labels  = [r["label"]  for r in regions.values()]
    lats    = [r["lat"]    for r in regions.values()]
    lons    = [r["lon"]    for r in regions.values()]
    scores  = [r["score"]  for r in regions.values()]

    # Hover metnine haber sayisini da ekle
    custom = [[r["score"], r.get("headline_count", 0)] for r in regions.values()]

    fig = go.Figure(go.Scattergeo(
        lat=lats,
        lon=lons,
        text=labels,
        customdata=custom,
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Gerilim Skoru: %{customdata[0]:.1f}/10<br>"
            "Eslesen Haber: %{customdata[1]}<extra></extra>"
        ),
        mode="markers+text",
        textposition="top center",
        textfont=dict(color="#F1EFE8", size=10, family="Inter"),
        marker=dict(
            size=[12 + s * 3.5 for s in scores],
            color=scores,
            colorscale=[
                [0.0,  "#1D9E75"],
                [0.35, "#E8A33D"],
                [0.65, "#E0524F"],
                [1.0,  "#B91C1C"],
            ],
            cmin=0,
            cmax=10,
            colorbar=dict(
                title=dict(text="Gerilim", font=dict(color="#9FB3C8", size=11)),
                tickfont=dict(color="#9FB3C8", size=10),
                thickness=12,
                len=0.7,
            ),
            line=dict(width=1.5, color="#0B1929"),
        ),
    ))

    fig.update_geos(
        bgcolor="#0B1929",
        landcolor="#142841",
        showocean=True,
        oceancolor="#091520",
        showcountries=True,
        countrycolor="#1F3A5C",
        showcoastlines=True,
        coastlinecolor="#1F3A5C",
        showframe=False,
        projection_type="natural earth",
    )
    fig.update_layout(
        paper_bgcolor="#0B1929",
        margin=dict(l=0, r=0, t=10, b=0),
        height=430,
        geo=dict(
            showland=True,
            lataxis_range=[-55, 75],
            lonaxis_range=[-130, 155],
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # -- Ozet banner: en yuksek riskli 3 bolge --
    sorted_regions = sorted(regions.items(), key=lambda x: x[1]["score"], reverse=True)
    top3 = sorted_regions[:3]
    st.markdown(
        '<div style="display:flex; gap:8px; margin-bottom:12px; flex-wrap:wrap;">',
        unsafe_allow_html=True,
    )
    banner_parts = []
    for _, r in top3:
        lvl, clr = _geo_risk_level(r["score"])
        banner_parts.append(
            f'<span style="background:{clr}22; border:1px solid {clr}55; '
            f'border-radius:20px; padding:3px 10px; font-size:11px; color:{clr}; '
            f'font-weight:600;">'
            f'{r["label"]} -- {r["score"]:.1f}/10 ({lvl})</span>'
        )
    st.markdown(
        '<div style="display:flex; gap:8px; margin-bottom:10px; flex-wrap:wrap;">'
        + "".join(banner_parts)
        + "</div>",
        unsafe_allow_html=True,
    )

    # -- Bolge detay kartlari (4 sutun) --
    cols = st.columns(4)
    for i, (region_id, r) in enumerate(regions.items()):
        score = r["score"]
        lvl, score_color = _geo_risk_level(score)
        hl_count = r.get("headline_count", 0)
        top_headlines = r.get("top_headlines", [])
        description = r.get("description", "")
        tickers_str = "  ".join(r["tickers"])

        # Haber basliklari HTML blogu
        news_html = ""
        if top_headlines:
            items_html = "".join(
                f'<div style="font-size:9px; color:#9FB3C8; margin-top:4px; '
                f'padding-left:6px; border-left:2px solid #2A4A6A; line-height:1.4;">'
                f'{h[:90]}{"..." if len(h) > 90 else ""}</div>'
                for h in top_headlines
            )
            news_html = (
                f'<div style="margin-top:7px;">'
                f'<div style="font-size:8px; color:#4A6A8A; text-transform:uppercase; '
                f'letter-spacing:0.08em; margin-bottom:3px;">Son Haberler</div>'
                + items_html
                + "</div>"
            )
        elif hl_count == 0:
            news_html = (
                '<div style="font-size:9px; color:#4A6A8A; margin-top:6px; '
                'font-style:italic;">Aktif haber bulunamadi</div>'
            )

        desc_html = ""
        if description:
            desc_html = (
                f'<div style="font-size:9px; color:#6A8AAA; margin-top:6px; '
                f'line-height:1.45;">{description}</div>'
            )

        with cols[i % 4]:
            st.markdown(
                f'<div style="background:#0F2035; border-radius:8px; '
                f'padding:10px 12px; margin-bottom:8px; '
                f'border-left:3px solid {score_color}; height:100%;">'
                f'<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
                f'<span style="font-size:11px; font-weight:600; color:#F1EFE8; '
                f'line-height:1.3; flex:1; padding-right:8px;">{r["label"]}</span>'
                f'<div style="text-align:right; flex-shrink:0;">'
                f'<div style="font-size:18px; font-weight:700; color:{score_color}; line-height:1;">'
                f'{score:.1f}<span style="font-size:9px; color:#4A6A8A;">/10</span></div>'
                f'<div style="font-size:8px; color:{score_color}; font-weight:600; '
                f'text-transform:uppercase; letter-spacing:0.06em;">{lvl}</div>'
                f'</div>'
                f'</div>'
                f'<div style="font-size:9px; color:#6A8AAA; margin-top:5px; '
                f'font-family:\'IBM Plex Mono\',monospace;">{tickers_str}</div>'
                f'<div style="font-size:8px; color:#4A6A8A; margin-top:2px;">'
                f'{hl_count} haber analiz edildi</div>'
                + desc_html
                + news_html
                + "</div>",
                unsafe_allow_html=True,
            )

    st.caption(
        "Skor hesabi: VADER duygu analizi (negatif taraf 0-10 araligina olceklendi) "
        "ve haber hacmi bonusu (maks +2 puan). "
        "Finnhub genel haber akisindan bolge bazli anahtar kelime filtresiyle uretilmistir."
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