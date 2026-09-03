"""Analysis page (category assignment + results)."""
import streamlit as st
from components.cards import (
    balance_card,
    metric_card,
    page_header,
    section_label,
)
from components.charts import render_category_pie, render_spending_heatmap
from helpers import escape_html, format_currency
from services import api

ALL_CATEGORIES = [
    "alimentacao", "moradia", "transporte", "saude", "educacao",
    "lazer", "assinaturas", "transferencias", "investimentos",
    "vestuario", "pets", "casa", "outros",
]

_ASSIGN_BANNER = """
<div style="background:linear-gradient(135deg,rgba(108,99,255,0.08),rgba(78,205,196,0.04));border:1px solid rgba(108,99,255,0.2);border-radius:16px;padding:20px;margin-bottom:24px;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <div style="width:28px;height:28px;background:linear-gradient(135deg,#6C63FF,#4ECDC4);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;color:white;">1</div>
        <span style="color:var(--text-primary);font-weight:700;font-size:15px;">Etapa 1 de 2 — Atribuição de Categorias</span>
    </div>
    <p style="color:var(--text-secondary);font-size:13px;margin:0;">Revise e ajuste as categorias atribuídas automaticamente a cada transação. O sistema aprenderá com suas correções.</p>
</div>
"""

_NO_FILES_HTML = """
<div style="text-align:center;padding:60px 20px;background:linear-gradient(135deg,var(--bg-card),var(--bg-primary));border:1px solid var(--border);border-radius:20px;">
    <div style="font-size:48px;margin-bottom:16px;">📁</div>
    <h3 style="color:var(--text-primary);font-weight:700;margin:0 0 8px;">Nenhum arquivo encontrado</h3>
    <p style="color:var(--text-secondary);margin:0;">Envie um arquivo na aba Upload primeiro</p>
</div>
"""


def analysis_page() -> None:
    page_header("Análise", "Analise seus dados financeiros com IA")

    # --- Step 2: Show results ---
    if st.session_state.get("analysis_step") == "result" and st.session_state.get("analysis_result"):
        _render_analysis_results(st.session_state.analysis_result)
        if st.button("Nova Análise", use_container_width=True):
            st.session_state.analysis_step = None
            st.session_state.analysis_result = None
            st.session_state.analysis_transactions = None
            st.rerun()
        return

    # --- Step 1: Assign categories ---
    if st.session_state.get("analysis_step") == "assign" and st.session_state.get("analysis_transactions"):
        custom_cats = api.api_call("get", "/api/categories")
        if custom_cats:
            for c in custom_cats:
                if c["name"] not in ALL_CATEGORIES:
                    ALL_CATEGORIES.append(c["name"])
        category_options = sorted(ALL_CATEGORIES)

        txns = st.session_state.analysis_transactions
        st.markdown(_ASSIGN_BANNER, unsafe_allow_html=True)

        section_label(f"{len(txns)} Transações", margin="12px")

        edited = []
        for i, txn in enumerate(txns):
            amount = txn.get("amount", 0)
            sign = "+" if amount >= 0 else "-"
            color = "var(--green)" if amount >= 0 else "var(--red)"
            current_cat = txn.get("category", "outros")

            c1, c2, c3 = st.columns([3, 4, 1])
            with c1:
                st.markdown(f"""
                <div style="padding:6px 0;">
                    <div style="color:var(--text-muted);font-size:11px;">{escape_html(txn.get('date', ''))}</div>
                    <div style="color:var(--text-primary);font-size:13px;font-weight:600;margin-top:2px;">{escape_html(txn.get('description', '')[:40])}</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                cat_idx = category_options.index(current_cat) if current_cat in category_options else len(category_options) - 1
                selected_cat = st.selectbox(
                    "Categoria",
                    category_options,
                    index=cat_idx,
                    key=f"txn_cat_{i}",
                    label_visibility="collapsed",
                )
            with c3:
                st.markdown(f"""
                <div style="padding:6px 0;text-align:right;">
                    <div style="color:{color};font-size:14px;font-weight:700;">{sign} R$ {format_currency(abs(amount))}</div>
                </div>
                """, unsafe_allow_html=True)
            edited.append({
                "date": txn["date"],
                "description": txn["description"],
                "amount": txn["amount"],
                "category": selected_cat,
            })

        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Voltar", use_container_width=True):
                st.session_state.analysis_step = None
                st.session_state.analysis_transactions = None
                st.rerun()
        with c2:
            if st.button("Confirmar e Analisar", use_container_width=True, type="primary"):
                changed = [e for e in edited if e["category"] != txns[edited.index(e)].get("category", "")]
                if changed:
                    api.api_call("post", "/api/categories/learn", json={"assignments": [
                        {"description": e["description"], "category": e["category"]} for e in changed
                    ]})

                with st.spinner("Reanalisando com categorias atualizadas..."):
                    result = api.api_call("post", "/api/analysis", json={
                        "file_id": st.session_state.analysis_file_id,
                        "analysis_type": "full",
                    })
                if result and "result" in result:
                    st.session_state.analysis_step = "result"
                    st.session_state.analysis_result = result
                    st.session_state.analysis_transactions = None
                    st.rerun()
                else:
                    st.error("Erro ao reanalisar.")
        return

    # --- Initial state: file selector ---
    files = api.api_call("get", "/api/files")
    if not files:
        st.markdown(_NO_FILES_HTML, unsafe_allow_html=True)
        return

    file_options = {f"{f['filename']} ({f['file_type'].upper()})": f["id"] for f in files}
    selected = st.selectbox("Arquivo", list(file_options.keys()))

    if st.button("Iniciar Análise", use_container_width=True, type="primary"):
        file_id = file_options[selected]

        with st.spinner("Carregando transações..."):
            txns = api.api_call("get", f"/api/transactions/{file_id}")

        if txns:
            st.session_state.analysis_step = "assign"
            st.session_state.analysis_transactions = txns
            st.session_state.analysis_file_id = file_id
            st.rerun()
        else:
            st.error("Nenhuma transação encontrada no arquivo.")


def _render_analysis_results(result):
    local = result["result"].get("local_analysis", {})
    ai = result["result"].get("ai_analysis", "")

    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(0,212,170,0.08),rgba(0,212,170,0.02));border:1px solid rgba(0,212,170,0.2);border-radius:16px;padding:20px;margin-bottom:24px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <div style="width:28px;height:28px;background:linear-gradient(135deg,#00D4AA,#4ECDC4);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;color:white;">✓</div>
            <span style="color:var(--text-primary);font-weight:700;font-size:15px;">Etapa 2 de 2 — Resultado da Análise</span>
        </div>
        <p style="color:var(--text-secondary);font-size:13px;margin:0;">Categorias confirmadas e aprendidas pelo sistema.</p>
    </div>
    """, unsafe_allow_html=True)

    if local:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(metric_card("Receitas", f"R$ {format_currency(local.get('total_income', 0))}"), unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card("Despesas", f"R$ {format_currency(local.get('total_expenses', 0))}"), unsafe_allow_html=True)
        with c3:
            st.markdown(balance_card(local.get('balance', 0)), unsafe_allow_html=True)
        with c4:
            st.markdown(metric_card("Poupança", f"{local.get('savings_rate', 0)}%"), unsafe_allow_html=True)

        if local.get("alerts"):
            st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
            section_label("Alertas", margin="12px", color="var(--yellow)")
            for alert in local["alerts"]:
                st.warning(alert["message"])

        if local.get("monthly_comparison"):
            st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
            section_label("Comparativo Mensal", margin="12px")
            for comp in local["monthly_comparison"]:
                with st.expander(f"{comp['month']}"):
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Receita", f"R$ {format_currency(comp['income'])}", f"{comp['income_change_pct']:+.1f}%")
                    mc2.metric("Despesa", f"R$ {format_currency(comp['expenses'])}", f"{comp['expense_change_pct']:+.1f}%")
                    mc3.metric("Saldo", f"R$ {format_currency(comp['balance'])}")

        if local.get("categories"):
            st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
            section_label("Categorias", margin="12px")
            render_category_pie(local["categories"], hole=0.6, height=320,
                                text_font_size=12, legend_font_size=11)

        if local.get("daily_data"):
            st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
            section_label("Calendario de Gastos", margin="12px")
            if local["daily_data"]:
                render_spending_heatmap(local["daily_data"])

        if local.get("recurring_expenses"):
            st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
            section_label("Recorrentes", margin="12px")
            for rec in local["recurring_expenses"][:5]:
                st.markdown(f"""
                <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:14px 18px;margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="color:var(--text-primary);font-weight:600;font-size:13px;">{escape_html(rec['description'])}</div>
                        <div style="color:var(--accent);font-weight:700;font-size:14px;">R$ {format_currency(rec['avg_amount'])}</div>
                    </div>
                    <div style="color:var(--text-muted);font-size:11px;margin-top:4px;">{rec['count']}x · Total R$ {format_currency(rec['total'])}</div>
                </div>
                """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(metric_card("Investimento Sugerido", f"R$ {format_currency(local.get('suggested_investment', 0))}"), unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card("Media Mensal Gastos", f"R$ {format_currency(local.get('avg_monthly_expenses', 0))}"), unsafe_allow_html=True)

    if ai:
        st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:linear-gradient(135deg,rgba(108,99,255,0.08),rgba(78,205,196,0.04));border:1px solid rgba(108,99,255,0.15);border-radius:16px;padding:24px;margin-bottom:12px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <div style="width:28px;height:28px;background:linear-gradient(135deg,#6C63FF,#4ECDC4);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;">✦</div>
                <span style="color:var(--text-primary);font-weight:700;font-size:14px;">Analise da IA</span>
            </div>
        """, unsafe_allow_html=True)
        st.markdown(ai)
        st.markdown('</div>', unsafe_allow_html=True)
