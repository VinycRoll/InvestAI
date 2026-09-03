"""Login and registration pages."""
import streamlit as st
from helpers import _get_logo_b64
from services import api


def _render_logo() -> None:
    _b64 = _get_logo_b64()
    if _b64:
        _logo_html = f'<img src="data:image/png;base64,{_b64}" alt="InvestIA" style="width:220px;max-width:80vw;height:auto;margin:0 auto 20px;display:block;filter:drop-shadow(0 4px 12px rgba(108,99,255,0.3));">'
    else:
        _logo_html = '<div style="width:72px;height:72px;background:linear-gradient(135deg,#6C63FF,#4ECDC4);border-radius:20px;display:flex;align-items:center;justify-content:center;margin:0 auto 24px;font-size:32px;">💎</div>'

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:center;padding:8px 0 0;">
        <div style="text-align:center;max-width:420px;width:100%;">
            {_logo_html}
            <p style="color:var(--text-secondary);font-size:14px;margin:4px 0 0;letter-spacing:0.3px;">Análise financeira inteligente</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _divider() -> None:
    st.markdown('<div style="height:1px;width:64px;background:linear-gradient(90deg,transparent,var(--border),transparent);margin:12px auto 14px;border-radius:1px;"></div>', unsafe_allow_html=True)


def _set_session(result) -> None:
    if result and "token" in result:
        st.session_state.token = result["token"]
        st.session_state.user = result["user"]
        st.rerun()


def login_page() -> None:
    _render_logo()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        _divider()
        st.markdown('<p style="color:var(--text-primary);font-size:18px;font-weight:700;margin:0 0 24px;">Entrar</p>', unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="seu@email.com", label_visibility="collapsed")
            password = st.text_input("Senha", type="password", placeholder="Sua senha", label_visibility="collapsed")
            submitted = st.form_submit_button("Entrar", use_container_width=True, type="primary")

            if submitted:
                if not email or not password:
                    st.error("Preencha email e senha")
                elif "@" not in email:
                    st.error("Email inválido")
                else:
                    result = api.api_call("post", "/api/auth/login", json={
                        "email": email,
                        "password": password,
                    })
                    _set_session(result)

        st.markdown("""
        <div style="text-align:center;margin:20px 0 0;">
            <p style="color:var(--text-muted);font-size:13px;margin:0;">
                Não tem conta?
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Criar conta", use_container_width=True, key="go_register"):
            st.session_state.auth_page = "register"
            st.rerun()


def register_page() -> None:
    _render_logo()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        _divider()
        st.markdown('<p style="color:var(--text-primary);font-size:18px;font-weight:700;margin:0 0 24px;">Criar Conta</p>', unsafe_allow_html=True)

        with st.form("register_form"):
            name = st.text_input("Nome", placeholder="Seu nome completo", label_visibility="collapsed")
            email = st.text_input("Email", placeholder="seu@email.com", label_visibility="collapsed")
            password = st.text_input("Senha", type="password", placeholder="Mínimo 8 caracteres", label_visibility="collapsed")
            confirm = st.text_input("Confirmar senha", type="password", placeholder="Repita a senha", label_visibility="collapsed")
            submitted = st.form_submit_button("Criar conta", use_container_width=True, type="primary")

            if submitted:
                if not name or not email or not password or not confirm:
                    st.error("Preencha todos os campos")
                elif "@" not in email:
                    st.error("Email inválido")
                elif password != confirm:
                    st.error("As senhas não coincidem")
                elif len(password) < 8:
                    st.error("Senha deve ter no mínimo 8 caracteres")
                elif not any(c.isupper() for c in password):
                    st.error("Senha deve conter pelo menos uma letra maiúscula")
                elif not any(c.islower() for c in password):
                    st.error("Senha deve conter pelo menos uma letra minúscula")
                elif not any(c.isdigit() for c in password):
                    st.error("Senha deve conter pelo menos um número")
                else:
                    result = api.api_call("post", "/api/auth/register", json={
                        "email": email,
                        "name": name,
                        "password": password,
                    })
                    _set_session(result)

        st.markdown("""
        <div style="text-align:center;margin:20px 0 0;">
            <p style="color:var(--text-muted);font-size:13px;margin:0;">
                Já tem uma conta?
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Fazer login", use_container_width=True, key="go_login"):
            st.session_state.auth_page = "login"
            st.rerun()
