"""Chat page."""
import streamlit as st
from components.cards import page_header
from helpers import escape_html
from services import api


def chat_page() -> None:
    page_header("Chat", "Converse com o assistente financeiro")

    files = api.api_call("get", "/api/files")
    latest_file_id = files[0]["id"] if files else None
    latest_filename = files[0]["filename"] if files else None

    if latest_filename:
        st.markdown(f"""
        <div style="background:var(--accent-glow);border:1px solid rgba(108,99,255,0.2);border-radius:12px;padding:12px 16px;margin-bottom:20px;">
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="color:var(--accent);font-size:14px;">✦</span>
                <span style="color:var(--text-secondary);font-size:13px;">Contexto ativo: <strong style="color:var(--text-primary);">{escape_html(latest_filename)}</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if "chat_messages" not in st.session_state:
        history = api.api_call("get", "/api/chat/history")
        st.session_state.chat_messages = history or []

    for msg in st.session_state.chat_messages:
        role = msg["role"]
        with st.chat_message(role):
            st.markdown(msg["content"])

    if not st.session_state.chat_messages:
        st.markdown("""
        <div style="text-align:center;padding:20px;margin-bottom:16px;">
            <div style="width:56px;height:56px;background:linear-gradient(135deg,#6C63FF,#4ECDC4);border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:24px;">✦</div>
            <p style="color:var(--text-secondary);font-size:14px;margin:0;">Pergunte sobre seus gastos, receitas ou investimentos</p>
        </div>
        """, unsafe_allow_html=True)

        quick_qs = [
            "Quanto gastei no total este mes?",
            "Quais sao meus maiores gastos?",
            "Como posso economizar?",
            "Analise minhas categorias de gastos",
        ]
        cols = st.columns(2)
        for i, q in enumerate(quick_qs):
            with cols[i % 2]:
                if st.button(q, key=f"quick_{i}", use_container_width=True):
                    st.session_state.quick_question = q
                    st.rerun()

    if prompt := st.chat_input("Digite sua pergunta..."):
        if hasattr(st.session_state, "quick_question"):
            prompt = st.session_state.quick_question
            del st.session_state.quick_question

        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                payload = {"message": prompt}
                if latest_file_id:
                    payload["file_id"] = latest_file_id
                result = api.api_call("post", "/api/chat", json=payload)

            if result and "response" in result:
                response = result["response"]
                st.markdown(response)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
