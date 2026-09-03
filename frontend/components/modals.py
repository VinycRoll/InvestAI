"""Onboarding welcome modal (fully Streamlit-native)."""
import streamlit as st


def onboarding_check() -> None:
    """Show a welcome onboarding modal on first login (3 steps).

    The overlay and card are rendered in the main document (full viewport) and
    the X is a real Streamlit button positioned over the top-right corner of the
    card. Clicking it sets ``onboarding_done`` so the modal does not reappear on
    later reruns. This is fully Streamlit-native (no fake HTML button) and does
    not corrupt session_state.
    """
    if st.session_state.onboarding_done:
        return

    st.markdown("""
    <div class="onboarding-modal-overlay" id="onboarding-modal">
        <div class="onboarding-modal-card">
            <div style="width:64px;height:64px;background:linear-gradient(135deg,#6C63FF,#4ECDC4);border-radius:18px;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;font-size:28px;">&#x1F48E;</div>
            <h2 style="color:var(--text-primary);font-size:22px;font-weight:800;margin:0 0 8px;">Bem-vindo ao InvestIA!</h2>
            <p style="color:var(--text-secondary);font-size:14px;margin:0 0 28px;">Sua plataforma de análise financeira inteligente</p>
            <div style="text-align:left;">
                <div style="display:flex;gap:14px;align-items:flex-start;margin-bottom:20px;">
                    <div style="min-width:36px;height:36px;background:var(--accent-glow);border-radius:10px;display:flex;align-items:center;justify-content:center;color:var(--accent);font-weight:800;font-size:14px;">1</div>
                    <div>
                        <div style="color:var(--text-primary);font-weight:600;font-size:14px;">Upload do Extrato</div>
                        <div style="color:var(--text-muted);font-size:12px;margin-top:2px;">Envie seus extratos bancários (OFX, CSV, XLSX, PDF)</div>
                    </div>
                </div>
                <div style="display:flex;gap:14px;align-items:flex-start;margin-bottom:20px;">
                    <div style="min-width:36px;height:36px;background:rgba(78,205,196,0.15);border-radius:10px;display:flex;align-items:center;justify-content:center;color:var(--blue);font-weight:800;font-size:14px;">2</div>
                    <div>
                        <div style="color:var(--text-primary);font-weight:600;font-size:14px;">Faça a Análise</div>
                        <div style="color:var(--text-muted);font-size:12px;margin-top:2px;">IA analisa seus gastos, renda e oferece insights</div>
                    </div>
                </div>
                <div style="display:flex;gap:14px;align-items:flex-start;">
                    <div style="min-width:36px;height:36px;background:rgba(255,217,61,0.15);border-radius:10px;display:flex;align-items:center;justify-content:center;color:var(--yellow);font-weight:800;font-size:14px;">3</div>
                    <div>
                        <div style="color:var(--text-primary);font-weight:600;font-size:14px;">Converse com IA</div>
                        <div style="color:var(--text-muted);font-size:12px;margin-top:2px;">Tire dúvidas sobre investimentos e finanças pessoais</div>
                    </div>
                </div>
            </div>
            <div style="height:12px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _col = st.columns([1, 3, 1])[1]
    with _col:
        if st.button("✕", key="onboarding_close_btn", use_container_width=True, type="secondary", help="Fechar boas-vindas"):
            st.session_state.onboarding_done = True
            st.rerun()
