import streamlit as st
import plotly.express as px
import pandas as pd

def line_chart(df: pd.DataFrame, x: str, y: str, title: str):
    """Genel Amaçlı tek serili çizgi grafiği (Örn: Returns)"""
    fig = px.line(df, x=x, y=y, title=title)
    st.plotly_chart(fig, use_container_width=True)

def multi_line_chart(df: pd.DataFrame, x: str, y_cols: list, title: str):
    """Birden fazla veriyi aynı grafikte gösterir (Örn: EWMA vs GARCH)"""
    fig = px.line(df, x=x, y=y_cols, title=title)
    st.plotly_chart(fig, use_container_width=True)

def summary_table(df: pd.DataFrame, title: str = ""):
    """Verileri şık bir tablo olarak gösterir"""
    if title:
        st.subheader(title)
    st.dataframe(df, use_container_width=True)