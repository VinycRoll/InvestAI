"""Upload page."""
import streamlit as st
from components.cards import page_header, section_label
from helpers import escape_html
from services import api

_SUPPORTED_FORMATS_HTML = """
<div style="background:linear-gradient(135deg,var(--bg-card),var(--bg-secondary));border:1px solid var(--border);border-radius:20px;padding:32px;margin-bottom:24px;">
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
        <div style="text-align:center;padding:16px;border-radius:12px;background:var(--accent-glow);border:1px solid rgba(108,99,255,0.15);">
            <div style="font-size:24px;margin-bottom:6px;">🏦</div>
            <div style="color:var(--text-primary);font-size:12px;font-weight:600;">OFX/QFX</div>
            <div style="color:var(--text-muted);font-size:10px;">Extratos</div>
        </div>
        <div style="text-align:center;padding:16px;border-radius:12px;background:rgba(78,205,196,0.08);border:1px solid rgba(78,205,196,0.15);">
            <div style="font-size:24px;margin-bottom:6px;">📊</div>
            <div style="color:var(--text-primary);font-size:12px;font-weight:600;">CSV</div>
            <div style="color:var(--text-muted);font-size:10px;">Planilhas</div>
        </div>
        <div style="text-align:center;padding:16px;border-radius:12px;background:rgba(255,217,61,0.08);border:1px solid rgba(255,217,61,0.15);">
            <div style="font-size:24px;margin-bottom:6px;">📗</div>
            <div style="color:var(--text-primary);font-size:12px;font-weight:600;">XLSX</div>
            <div style="color:var(--text-muted);font-size:10px;">Excel</div>
        </div>
        <div style="text-align:center;padding:16px;border-radius:12px;background:rgba(255,71,87,0.08);border:1px solid rgba(255,71,87,0.15);">
            <div style="font-size:24px;margin-bottom:6px;">📄</div>
            <div style="color:var(--text-primary);font-size:12px;font-weight:600;">PDF</div>
            <div style="color:var(--text-muted);font-size:10px;">Documentos</div>
        </div>
    </div>
</div>
"""


def upload_page() -> None:
    page_header("Upload", "Envie seus extratos para análise")

    st.markdown(_SUPPORTED_FORMATS_HTML, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Arraste seus arquivos aqui",
        type=["ofx", "qfx", "csv", "xlsx", "xls", "pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        for file in uploaded_files:
            file_key = f"{file.name}_{file.size}"
            if file_key in st.session_state.uploaded_ids:
                continue
            with st.spinner(f"Processando {file.name}..."):
                files_data = {"file": (file.name, file.getvalue())}
                result = api.api_call("post", "/api/upload", files=files_data)

                if result and "parsed" in result:
                    parsed = result["parsed"]
                    txns = parsed.get("total_transactions", 0) or len(parsed.get("transactions", []))
                    st.session_state.uploaded_ids.add(file_key)

                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,rgba(0,212,170,0.08),rgba(0,212,170,0.02));border:1px solid rgba(0,212,170,0.2);border-radius:14px;padding:16px 20px;margin-bottom:12px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;">
                            <div style="display:flex;align-items:center;gap:12px;">
                                <div style="width:36px;height:36px;background:rgba(0,212,170,0.15);border-radius:10px;display:flex;align-items:center;justify-content:center;">✓</div>
                                <div>
                                    <div style="color:var(--text-primary);font-weight:600;font-size:14px;">{escape_html(file.name)}</div>
                                    <div style="color:var(--text-secondary);font-size:12px;">{txns} transações · {escape_html(parsed.get('type', ''))}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    section_label("Arquivos Enviados")

    files = api.api_call("get", "/api/files")
    if files:
        for f in files:
            st.markdown(f"""
            <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:14px;padding:14px 18px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div style="width:32px;height:32px;background:var(--accent-glow);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;">📄</div>
                    <div>
                        <div style="color:var(--text-primary);font-weight:600;font-size:13px;">{escape_html(f['filename'])}</div>
                        <div style="color:var(--text-muted);font-size:11px;">{escape_html(f['file_type']).upper()} · {f['file_size'] / 1024:.1f} KB</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Excluir", key=f"del_{f['id']}", type="secondary"):
                api.api_call("delete", f"/api/files/{f['id']}")
                st.rerun()
    else:
        st.markdown("""
        <div style="text-align:center;padding:40px;color:var(--text-muted);">
            <div style="font-size:32px;margin-bottom:12px;">📂</div>
            <p style="margin:0;">Nenhum arquivo enviado ainda</p>
        </div>
        """, unsafe_allow_html=True)
