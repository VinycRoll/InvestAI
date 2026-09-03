"""Reports page (analysis history + export)."""
import streamlit as st
from components.cards import empty_state, page_header
from services import api

_MIME_MAP = {"html": "text/html", "csv": "text/csv", "json": "application/json", "pdf": "application/pdf"}


def download_report(analysis_id: int, fmt: str) -> None:
    """Render a download button for an exported report in the given format."""
    response = api.api_download("/api/reports/export", {"analysis_id": analysis_id, "format": fmt})
    if response is None:
        return
    if response.status_code == 200:
        st.download_button(
            label=f"⬇ {fmt.upper()}",
            data=response.content,
            file_name=f"investia_{analysis_id}.{fmt}",
            mime=_MIME_MAP[fmt],
            key=f"dl_{fmt}_{analysis_id}",
            use_container_width=True,
        )
    else:
        st.error(f"Erro ao gerar relatório ({response.status_code}).")


def reports_page() -> None:
    page_header("Relatórios", "Exporte seus relatórios financeiros")

    history = api.api_call("get", "/api/analysis/history")
    if not history:
        empty_state("📋", "Nenhuma análise encontrada",
                    "Faça uma análise primeiro na aba Análise")
        return

    for a in history:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,var(--bg-card),var(--bg-secondary));border:1px solid var(--border);border-radius:16px;padding:20px;margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <div>
                    <div style="color:var(--text-primary);font-weight:700;font-size:14px;">Análise #{a['id']}</div>
                    <div style="color:var(--text-muted);font-size:12px;margin-top:2px;">{a['created_at'][:10]}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
        with c1:
            download_report(a["id"], "html")
        with c2:
            download_report(a["id"], "csv")
        with c3:
            download_report(a["id"], "json")
        with c4:
            download_report(a["id"], "pdf")
        with c5:
            if st.button("Excluir", key=f"del_analysis_{a['id']}", use_container_width=True):
                st.session_state[f"confirm_del_{a['id']}"] = True
                st.rerun()
            if st.session_state.get(f"confirm_del_{a['id']}"):
                st.warning("Tem certeza?")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("Sim", key=f"yes_del_{a['id']}", type="primary", use_container_width=True):
                        api.api_call("delete", f"/api/analysis/{a['id']}")
                        del st.session_state[f"confirm_del_{a['id']}"]
                        st.rerun()
                with cc2:
                    if st.button("Não", key=f"no_del_{a['id']}", use_container_width=True):
                        del st.session_state[f"confirm_del_{a['id']}"]
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
