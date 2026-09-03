"""InvestIA Streamlit entry point.

Thin bootstrap that configures the page, applies the global theme and
dispatches to the view modules. All implementation lives in ``views/``,
``components/``, ``services/`` and ``styles/``.
"""
import streamlit as st
from components.modals import onboarding_check
from components.navigation import sidebar
from styles.theme import apply_global_css, apply_theme_marker
from views.analysis import analysis_page
from views.auth import login_page, register_page
from views.categories import categories_page
from views.chat import chat_page
from views.dashboard import dashboard_page
from views.reports import reports_page
from views.settings import settings_page
from views.upload import upload_page

st.set_page_config(
    page_title="InvestIA",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_css()
apply_theme_marker()


# --- Session State ---
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"  # login or register
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "onboarding_done" not in st.session_state:
    st.session_state.onboarding_done = False
if "uploaded_ids" not in st.session_state:
    st.session_state.uploaded_ids = set()
if "_nav_page" not in st.session_state:
    st.session_state["_nav_page"] = "Dashboard"


# --- Main dispatch ---
if not st.session_state.token:
    if st.session_state.auth_page == "register":
        register_page()
    else:
        login_page()
else:
    onboarding_check()
    page = sidebar()
    page_map = {
        "Dashboard": dashboard_page,
        "Upload": upload_page,
        "Análise": analysis_page,
        "Chat": chat_page,
        "Categorias": categories_page,
        "Relatórios": reports_page,
        "Configurações": settings_page,
    }
    page_map.get(page, dashboard_page)()
