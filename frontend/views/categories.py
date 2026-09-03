"""Categories page."""
import streamlit as st
from components.cards import page_header, section_label
from components.icons import icon
from helpers import escape_html, toast
from services import api
from styles.theme import BUILTIN_CATEGORIES

_INFO_HTML = """
<div style="background:var(--accent-glow);border:1px solid rgba(108,99,255,0.2);border-radius:12px;padding:16px;margin-top:16px;">
    <p style="color:var(--text-secondary);font-size:12px;margin:0;">
        <strong style="color:var(--accent);">Como funciona:</strong> As palavras-chave das categorias personalizadas são verificadas
        <strong>antes</strong> das categorias padrão. Se uma transação contiver alguma palavra-chave, será classificada na sua categoria personalizada.
    </p>
</div>
"""


def categories_page() -> None:
    page_header("Categorias", "Categorias personalizadas para classificar seus gastos")

    # --- Built-in categories ---
    section_label("Categorias Padrão", margin="12px")

    cols = st.columns(3)
    for i, (_key, label) in enumerate(BUILTIN_CATEGORIES.items()):
        with cols[i % 3]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,var(--bg-card),var(--bg-secondary));border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:10px;">
                <div style="color:var(--text-primary);font-size:13px;font-weight:600;">{label}</div>
                <div style="color:var(--text-muted);font-size:11px;margin-top:2px;">Automática</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    # --- Custom categories ---
    section_label("Categorias Personalizadas", margin="12px")

    custom_cats = api.api_call("get", "/api/categories")

    if custom_cats:
        for cat in custom_cats:
            c1, c2 = st.columns([5, 1])
            with c1:
                keywords_str = ", ".join(cat.get("keywords", []))
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,var(--bg-card),var(--bg-secondary));border:1px solid rgba(108,99,255,0.2);border-radius:12px;padding:16px;margin-bottom:8px;">
                    <div style="color:var(--text-primary);font-size:14px;font-weight:600;">{escape_html(cat['name'])}</div>
                    <div style="color:var(--text-secondary);font-size:12px;margin-top:4px;">Palavras-chave: {escape_html(keywords_str) if keywords_str else '<em>Nenhuma</em>'}</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                if st.button("🗑", key=f"del_cat_{cat['id']}", help="Excluir categoria"):
                    api.api_call("delete", f"/api/categories/{cat['id']}")
                    st.rerun()
    else:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,var(--bg-card),var(--bg-secondary));border:1px solid var(--border);border-radius:16px;padding:30px;text-align:center;margin-bottom:16px;">
            <div style="margin-bottom:12px;">{icon("tags", 36, "var(--text-muted)")}</div>
            <p style="color:var(--text-secondary);font-size:13px;margin:0;">Nenhuma categoria personalizada criada ainda</p>
        </div>
        """, unsafe_allow_html=True)

    # --- Create new category ---
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    section_label("Criar Nova Categoria", margin="12px")

    with st.form("new_category_form"):
        cat_name = st.text_input("Nome da categoria", placeholder="Ex: Academia, Cursos, Pets...")
        cat_keywords = st.text_input("Palavras-chave (separadas por vírgula)", placeholder="Ex: academia, smartfit, musculação")
        submitted = st.form_submit_button("Criar Categoria", type="primary", use_container_width=True)

        if submitted:
            if not cat_name.strip():
                st.error("Digite um nome para a categoria")
            elif not cat_keywords.strip():
                st.error("Adicione pelo menos uma palavra-chave")
            else:
                keywords = [k.strip().lower() for k in cat_keywords.split(",") if k.strip()]
                result = api.api_call("post", "/api/categories", json={"name": cat_name.strip(), "keywords": keywords})
                if result:
                    toast(f"Categoria '{cat_name}' criada com sucesso!", "success")
                    st.rerun()

    # --- Info ---
    st.markdown(_INFO_HTML, unsafe_allow_html=True)
