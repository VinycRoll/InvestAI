"""Dashboard page."""
import streamlit as st
from components.cards import (
    balance_card,
    empty_state,
    metric_card,
    page_header,
    section_label,
    skeleton_loader,
)
from components.charts import render_category_pie, render_monthly_trend
from helpers import format_currency
from services import api


def dashboard_page() -> None:
    page_header("Dashboard", "Visão geral das suas finanças")

    data = api.api_call("get", "/api/dashboard/summary")
    if not data:
        skeleton_loader(count=3, cols=3)
        empty_state("📊", "Bem-vindo ao InvestIA",
                    "Envie seu primeiro extrato para começar a analisar suas finanças")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(metric_card("Arquivos", str(data.get("files_count", 0))), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("Análises", str(data.get("analyses_count", 0))), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("Mensagens", str(data.get("messages_count", 0))), unsafe_allow_html=True)

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    last = data.get("last_analysis")
    if last:
        section_label("Última Análise")

        inc = last.get("total_income", 0)
        exp = last.get("total_expenses", 0)
        bal = last.get("balance", 0)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(metric_card("Receitas", f"R$ {format_currency(inc)}"), unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card("Despesas", f"R$ {format_currency(exp)}"), unsafe_allow_html=True)
        with c3:
            st.markdown(balance_card(bal), unsafe_allow_html=True)

        if last.get("categories"):
            st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
            section_label("Distribuição de Gastos")
            render_category_pie(last["categories"], hole=0.65, height=350)

    if last and last.get("monthly_data"):
        st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
        section_label("Tendência Mensal")
        render_monthly_trend(last["monthly_data"])
