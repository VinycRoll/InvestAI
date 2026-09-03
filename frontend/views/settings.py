"""Settings page."""
import streamlit as st
from components.cards import page_header, section_label
from helpers import escape_html, toast
from services import api


def settings_page() -> None:
    page_header("Configurações", "Gerencie sua conta e preferências")

    user = st.session_state.user or {}

    section_label("Informações da Conta")
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,var(--bg-card),var(--bg-secondary));border:1px solid var(--border);border-radius:16px;padding:22px;margin-bottom:24px;">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
            <div>
                <div style="color:var(--text-muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px;">Nome</div>
                <div style="color:var(--text-primary);font-size:14px;font-weight:600;">{escape_html(user.get('name', '—'))}</div>
            </div>
            <div>
                <div style="color:var(--text-muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px;">Email</div>
                <div style="color:var(--text-primary);font-size:14px;font-weight:600;">{escape_html(user.get('email', '—'))}</div>
            </div>
            <div>
                <div style="color:var(--text-muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px;">Provedor</div>
                <div style="color:var(--text-primary);font-size:14px;font-weight:600;">{escape_html(user.get('provider', 'email').title())}</div>
            </div>
            <div>
                <div style="color:var(--text-muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px;">Membro desde</div>
                <div style="color:var(--text-primary);font-size:14px;font-weight:600;">{escape_html(user.get('created_at', '—')[:10] if user.get('created_at') else '—')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    section_label("Alterar Senha")
    with st.form("change_password_form"):
        current_pw = st.text_input("Senha atual", type="password", placeholder="Sua senha atual")
        new_pw = st.text_input("Nova senha", type="password", placeholder="Mínimo 8 caracteres")
        confirm_pw = st.text_input("Confirmar nova senha", type="password", placeholder="Repita a nova senha")
        if st.form_submit_button("Alterar Senha", use_container_width=True, type="primary"):
            if not current_pw or not new_pw or not confirm_pw:
                toast("Preencha todos os campos", "error")
            elif new_pw != confirm_pw:
                toast("As senhas não coincidem", "error")
            elif len(new_pw) < 8:
                toast("Nova senha deve ter no mínimo 8 caracteres", "error")
            else:
                result = api.api_call("post", "/api/auth/change-password", json={
                    "current_password": current_pw,
                    "new_password": new_pw,
                })
                if result and result.get("success"):
                    toast("Senha alterada com sucesso!", "success")
                else:
                    toast("Erro ao alterar senha. Verifique a senha atual.", "error")

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    section_label("Zona de Perigo", color="var(--red)")
    if "confirm_delete" not in st.session_state:
        st.session_state.confirm_delete = False

    if not st.session_state.confirm_delete:
        if st.button("Excluir minha conta", type="secondary", key="delete_account_btn"):
            st.session_state.confirm_delete = True
            st.rerun()
    else:
        st.markdown("""
        <div style="background:rgba(255,71,87,0.08);border:1px solid rgba(255,71,87,0.2);border-radius:12px;padding:16px;margin-bottom:12px;">
            <p style="color:var(--red);font-weight:600;font-size:14px;margin:0 0 4px;">⚠ Tem certeza?</p>
            <p style="color:var(--text-secondary);font-size:13px;margin:0;">Esta ação é irreversível. Todos seus dados serão perdidos.</p>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button("Sim, excluir", type="primary", key="confirm_delete_yes"):
                result = api.api_call("delete", "/api/auth/account")
                if result and result.get("success"):
                    st.session_state.token = None
                    st.session_state.user = None
                    toast("Conta excluída com sucesso.", "info")
                    st.rerun()
                else:
                    toast("Erro ao excluir conta.", "error")
        with c2:
            if st.button("Cancelar", key="confirm_delete_no"):
                st.session_state.confirm_delete = False
                st.rerun()
