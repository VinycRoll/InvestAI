"""Settings page."""
import base64
from io import BytesIO

import streamlit as st
from components.cards import page_header, section_label
from helpers import escape_html, toast
from PIL import Image, ImageOps, UnidentifiedImageError
from services import api
from streamlit_cropper import st_cropper

AVATAR_INPUT_MAX_BYTES = 10 * 1024 * 1024
AVATAR_OUTPUT_SIZE = 512


def _open_avatar(image_bytes: bytes) -> Image.Image | None:
    """Load an uploaded avatar safely for the visual crop editor."""
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB").copy()
    except (OSError, UnidentifiedImageError):
        return None

    width, height = image.size
    if not width or not height or width * height > 40_000_000:
        return None

    return image


def _encode_avatar(avatar: Image.Image) -> bytes:
    """Resize a cropped image for storage as a compact profile avatar."""
    avatar = avatar.convert("RGB")
    avatar = avatar.resize((AVATAR_OUTPUT_SIZE, AVATAR_OUTPUT_SIZE), Image.Resampling.LANCZOS)

    output = BytesIO()
    avatar.save(output, format="JPEG", quality=88, optimize=True)
    return output.getvalue()


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

    section_label("Foto de Perfil")
    avatar_url = user.get("avatar_url")
    if avatar_url and avatar_url.startswith("data:"):
        try:
            st.image(base64.b64decode(avatar_url.split(",", 1)[1]), width=96)
        except (IndexError, ValueError):
            pass

    uploaded_avatar = st.file_uploader(
        "Escolha uma imagem PNG, JPEG ou WebP (máx. 10 MB)",
        type=["png", "jpg", "jpeg", "webp"],
        key="profile_avatar_upload",
    )
    if uploaded_avatar:
        avatar_bytes = uploaded_avatar.getvalue()
        if len(avatar_bytes) > AVATAR_INPUT_MAX_BYTES:
            st.error("A imagem original deve ter no máximo 10 MB.")
        else:
            source_avatar = _open_avatar(avatar_bytes)
            if not source_avatar:
                st.error("Não foi possível processar essa imagem. Escolha outro arquivo.")
            else:
                st.caption("Arraste a moldura quadrada e use a rolagem do mouse para aproximar ou afastar.")
                cropped_image = st_cropper(
                    source_avatar,
                    aspect_ratio=(1, 1),
                    box_color="#6C63FF",
                    realtime_update=True,
                    key="profile_avatar_cropper",
                )
                cropped_avatar = _encode_avatar(cropped_image)
                st.image(cropped_avatar, width=160, caption="Prévia da foto de perfil")
                if st.button("Salvar foto de perfil", type="primary", key="save_profile_avatar"):
                    avatar_data_url = f"data:image/jpeg;base64,{base64.b64encode(cropped_avatar).decode('ascii')}"
                    result = api.api_call("post", "/api/auth/avatar", json={"avatar_url": avatar_data_url})
                    if result and result.get("user"):
                        st.session_state.user = result["user"]
                        toast("Foto de perfil atualizada!", "success")
                        st.rerun()

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
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
