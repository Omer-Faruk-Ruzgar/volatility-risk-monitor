import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def line_chart(df: pd.DataFrame, x: str, y: str, title: str):
    """Genel amaçlı tek serili çizgi grafiği (Örn: Returns)"""
    fig = px.line(df, x=x, y=y, title=title)
    fig.update_layout(xaxis_title="Tarih", yaxis_title=y)
    st.plotly_chart(fig, use_container_width=True)


def multi_line_chart(df: pd.DataFrame, x: str, y_cols: list, title: str):
    """Birden fazla seriyi aynı grafikte gösterir (Örn: EWMA vs GARCH vs Forecast)"""
    # Sadece DataFrame'de gerçekten var olan kolonları çiz
    available = [c for c in y_cols if c in df.columns]
    if not available:
        st.warning("Gösterilecek veri bulunamadı.")
        return
    fig = px.line(df, x=x, y=available, title=title)
    fig.update_layout(xaxis_title="Tarih", yaxis_title="Volatilite", legend_title="Model")
    st.plotly_chart(fig, use_container_width=True)


def var_breach_chart(df: pd.DataFrame, ticker: str, method: str = "parametric"):
    """
    Getiri serisi + VaR çizgisi + ihlal noktalarını tek bir grafikte gösterir.

    df kolonları: date, return, parametric_var / historical_var, es, is_breach
    """
    var_col = "parametric_var" if method == "parametric" else "historical_var"
    label   = "Parametrik VaR" if method == "parametric" else "Tarihsel VaR"

    fig = go.Figure()

    # Getiri çizgisi (gri)
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
    st.plotly_chart(fig, use_container_width=True)


def summary_table(df: pd.DataFrame, title: str = ""):
    """Verileri şık bir tablo olarak gösterir"""
    if title:
        st.subheader(title)
    st.dataframe(df, use_container_width=True)
