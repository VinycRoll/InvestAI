"""Sidebar navigation rendering (native Streamlit buttons + theme/logout controls)."""
import streamlit as st
from components.icons import icon

NAV_ITEMS = [
    ("Dashboard", "dashboard"),
    ("Upload", "upload"),
    ("Análise", "analysis"),
    ("Chat", "chat"),
    ("Categorias", "tags"),
    ("Relatórios", "report"),
    ("Configurações", "settings"),
]


def sidebar() -> str:
    with st.sidebar:
        user = st.session_state.user or {}
        name = user.get("name", "Usuário")
        email = user.get("email", "")

        st.markdown(f"""
        <div style="padding:4px 0 20px;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
                <div style="width:40px;height:40px;background:linear-gradient(135deg,#6C63FF,#4ECDC4);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:16px;color:white;font-weight:700;">{name[0].upper()}</div>
                <div>
                    <div style="color:var(--text-primary);font-size:14px;font-weight:600;">{name}</div>
                    <div style="color:var(--text-muted);font-size:11px;">{email}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="color:var(--text-muted);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;padding:0 8px;margin-bottom:8px;">Navegação</div>', unsafe_allow_html=True)

        current_page = st.session_state.get("_nav_page", "Dashboard")

        for label, icon_name in NAV_ITEMS:
            is_selected = label == current_page
            icon_color = "var(--accent)" if is_selected else "var(--text-secondary)"
            col_icon, col_label = st.columns([1, 5], gap="small")
            with col_icon:
                st.markdown(icon(icon_name, 18, icon_color), unsafe_allow_html=True)
            with col_label:
                if st.button(
                    label,
                    key=f"nav_{label}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state["_nav_page"] = label
                    st.rerun()
        page = current_page

        st.markdown('<div style="height:1px;background:var(--border);margin:16px 0;"></div>', unsafe_allow_html=True)

        st.markdown('<div style="color:var(--text-muted);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;padding:0 8px;margin-bottom:8px;">Aparência</div>', unsafe_allow_html=True)
        theme_label = "☀️  Modo Claro" if st.session_state.theme == "dark" else "🌙  Modo Escuro"
        if st.button(theme_label, use_container_width=True, key="theme_toggle"):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()

        if st.button("Sair da conta", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()

        st.markdown("""
        <div style="position:fixed;bottom:20px;left:20px;right:20px;text-align:center;">
            <p style="color:var(--text-muted);font-size:10px;">InvestIA v2.0 — Powered by Gemini</p>
        </div>
        """, unsafe_allow_html=True)

        return page
