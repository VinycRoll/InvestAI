"""Global styling for the Streamlit frontend.

The full premium CSS, the theme-marker script and shared theming constants
(predefined categories, palette) live here so ``app.py`` stays a thin entry
point and pages reuse identical look & feel.
"""
import streamlit as st

# ---------------------------------------------------------------------------
# Theme / categories constants
# ---------------------------------------------------------------------------

# Predefined (built-in) category keys mapped to human-readable labels.
BUILTIN_CATEGORIES = {
    "alimentacao": "Alimentação",
    "moradia": "Moradia",
    "transporte": "Transporte",
    "saude": "Saúde",
    "educacao": "Educação",
    "lazer": "Lazer",
    "assinaturas": "Assinaturas",
    "transferencias": "Transferências",
    "investimentos": "Investimentos",
    "vestuario": "Vestuário",
    "pets": "Pets",
    "casa": "Casa",
    "outros": "Outros",
}

# Default category keys used to seed the analysis assignment selectors.
DEFAULT_CATEGORIES = list(BUILTIN_CATEGORIES.keys())

# Categorical palette shared by the pie/heatmap charts.
CATEGORY_COLORS = [
    "#6C63FF", "#4ECDC4", "#FFD93D", "#FF4757", "#00D4AA", "#FF6B6B",
    "#A8E6CF", "#DDA0DD", "#98D8C8", "#F7DC6F",
]


def is_light_theme() -> bool:
    return st.session_state.get("theme", "dark") == "light"


# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg-primary: #0A0A0F;
    --bg-secondary: var(--bg-primary);
    --bg-card: #14141C;
    --bg-card-hover: #22222F;
    --accent: #6C63FF;
    --accent-glow: rgba(108, 99, 255, 0.15);
    --accent-glow-strong: rgba(108, 99, 255, 0.3);
    --green: #00D4AA;
    --green-glow: rgba(0, 212, 170, 0.15);
    --red: #FF4757;
    --red-glow: rgba(255, 71, 87, 0.15);
    --blue: #4ECDC4;
    --yellow: #FFD93D;
    --text-primary: #E8E8ED;
    --text-secondary: #8B8B9E;
    --text-muted: #5A5A6E;
    --border: rgba(255, 255, 255, 0.06);
    --border-light: rgba(255, 255, 255, 0.1);
}

/* Light theme */
body[data-theme="light"] {
    --bg-primary: #F5F5F7;
    --bg-secondary: #FFFFFF;
    --bg-card: #FFFFFF;
    --bg-card-hover: #F0F0F2;
    --accent: #5A52D5;
    --accent-glow: rgba(90, 82, 213, 0.12);
    --accent-glow-strong: rgba(90, 82, 213, 0.22);
    --green: #00B894;
    --red: #E74C3C;
    --blue: #3498DB;
    --yellow: #F39C12;
    --text-primary: #1A1A2E;
    --text-secondary: #5A5A7E;
    --text-muted: #9A9AB0;
    --border: rgba(0, 0, 0, 0.08);
    --border-light: rgba(0, 0, 0, 0.12);
}

/* Font-family override applied to app widgets only - avoids overriding
   Streamlit's native icons (collapse arrows, header buttons, password eye). */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] *,
.main .block-container,
.stApp .stMarkdown,
.stApp .stTextInput,
.stApp .stTextArea,
.stApp .stSelectbox,
.stApp .stButton,
.stApp .stForm {
    font-family: 'Inter', sans-serif !important;
}

/* Native Streamlit password toggle: keep the default icon (FontAwesome-style
   glyph) without forcing a Material font, so "visibility/visibili" ligature
   text never leaks. */
[data-baseweb="input"] button span,
[data-baseweb="input"] [role="button"] span {
    font-family: inherit !important;
}

/* Botão nativo de recolher/expandir a sidebar: precisa da fonte de ícones
   Material Symbols, senão o texto do ícone aparece cru em vez do desenho. */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] *,
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] *,
[data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded' !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D0D14 0%, #0A0A0F 100%) !important;
    border-right: 1px solid var(--border) !important;
}

section[data-testid="stSidebar"] .stRadio > div > label {
    padding: 10px 16px !important;
    border-radius: 12px !important;
    transition: all 0.2s ease !important;
    margin-bottom: 4px !important;
}

section[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: var(--bg-card) !important;
}

section[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] {
    background: linear-gradient(135deg, var(--accent-glow) 0%, var(--accent-glow-strong) 100%) !important;
    border: 1px solid rgba(108, 99, 255, 0.3) !important;
}

.stButton > button {
    background: linear-gradient(135deg, #6C63FF 0%, #5A52D5 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(108, 99, 255, 0.3) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(108, 99, 255, 0.4) !important;
}

.stDownloadButton > button {
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-light) !important;
    border-radius: 12px !important;
    transition: all 0.2s ease !important;
}

.stDownloadButton > button:hover {
    border-color: var(--accent) !important;
    background: var(--bg-card-hover) !important;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-light) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-glow) !important;
}

.stForm {
    background: linear-gradient(135deg,var(--bg-card),var(--bg-primary)) !important;
    border: 1px solid var(--border) !important;
    border-radius: 20px !important;
    padding: 24px !important;
}

.expanderWrapper {
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    overflow: hidden;
}

div[data-testid="stMetric"] {
    background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-secondary) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 20px;
    transition: all 0.3s ease;
}

div[data-testid="stMetric"]:hover {
    border-color: var(--border-light);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
}

div[data-testid="stMetric"] label {
    color: var(--text-secondary) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    font-size: 1.5rem !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricDelta"] > div {
    font-weight: 600 !important;
}

div[data-testid="stAlert"] {
    background: var(--bg-card) !important;
    border-radius: 12px !important;
    border-left-width: 3px !important;
}

div[data-testid="stAlert"][role="alert"] {
    border-color: var(--accent) !important;
}

div[data-testid="stAlert"][data-basewarn="true"] {
    border-color: var(--yellow) !important;
    background: rgba(255, 217, 61, 0.05) !important;
}

div[data-testid="stAlert"][data-basewarning="true"] {
    border-color: var(--yellow) !important;
    background: rgba(255, 217, 61, 0.05) !important;
}

hr {
    border-color: var(--border) !important;
}

code {
    background: var(--bg-card) !important;
    border-radius: 6px !important;
    padding: 2px 6px !important;
}

.stCodeBlock {
    border-radius: 12px !important;
    border: 1px solid var(--border) !important;
}

div[data-baseweb="tab-list"] {
    gap: 4px;
}

div[data-baseweb="tab"] {
    border-radius: 10px 10px 0 0 !important;
    background: var(--bg-card) !important;
}

section[data-testid="stSidebar"] hr {
    border-color: var(--border) !important;
}

.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    color: var(--text-primary) !important;
}

.stMarkdown p, .stMarkdown li {
    color: var(--text-secondary) !important;
    line-height: 1.7 !important;
}

.stMarkdown strong {
    color: var(--text-primary) !important;
}

/* #11 Skeleton / Loading States */
@keyframes skeleton-pulse {
    0% { background-position: -200px 0; }
    100% { background-position: calc(200px + 100%) 0; }
}
.skeleton-card {
    background: linear-gradient(90deg, var(--bg-card) 8px, var(--bg-card-hover) 16px, var(--bg-card) 24px);
    background-size: 200px 100%;
    animation: skeleton-pulse 1.5s ease-in-out infinite;
    border-radius: 16px;
    border: 1px solid var(--border);
    padding: 22px;
    min-height: 80px;
    margin-bottom: 12px;
}
.skeleton-line {
    height: 12px;
    border-radius: 6px;
    background: linear-gradient(90deg, var(--bg-card) 8px, var(--bg-card-hover) 16px, var(--bg-card) 24px);
    background-size: 200px 100%;
    animation: skeleton-pulse 1.5s ease-in-out infinite;
    margin-bottom: 8px;
}
.skeleton-line.short { width: 40%; }
.skeleton-line.medium { width: 65%; }

/* #12 Toast Notifications */
@keyframes toast-slide-in {
    0% { transform: translateX(120%); opacity: 0; }
    100% { transform: translateX(0); opacity: 1; }
}
@keyframes toast-slide-out {
    0% { transform: translateX(0); opacity: 1; }
    100% { transform: translateX(120%); opacity: 0; }
}
.toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 99999;
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.toast {
    padding: 14px 20px;
    border-radius: 12px;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    font-weight: 500;
    color: #fff;
    min-width: 280px;
    max-width: 420px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.3);
    animation: toast-slide-in 0.4s ease forwards;
}
.toast.fade-out { animation: toast-slide-out 0.4s ease forwards; }
.toast-success { background: linear-gradient(135deg, #00B894, #00A381); border-left: 4px solid #00D4AA; }
.toast-error { background: linear-gradient(135deg, #E74C3C, #C0392B); border-left: 4px solid #FF4757; }
.toast-warning { background: linear-gradient(135deg, #F39C12, #E67E22); border-left: 4px solid #FFD93D; }
.toast-info { background: linear-gradient(135deg, #3498DB, #2980B9); border-left: 4px solid #4ECDC4; }

/* #17 Light theme overrides */
body[data-theme="light"] {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}
body[data-theme="light"] .stApp {
    background-color: var(--bg-primary) !important;
}
body[data-theme="light"] section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #F5F5F7 100%) !important;
}
body[data-theme="light"] section[data-testid="stSidebar"] .stRadio > div > label,
body[data-theme="light"] section[data-testid="stSidebar"] .stRadio > div > label span,
body[data-theme="light"] section[data-testid="stSidebar"] .stRadio > div > label p,
body[data-theme="light"] section[data-testid="stSidebar"] .stRadio > div > label div,
body[data-theme="light"] section[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] span,
body[data-theme="light"] section[data-testid="stSidebar"] div[data-baseweb="radio"] label,
body[data-theme="light"] section[data-testid="stSidebar"] div[data-baseweb="radio"] span,
body[data-theme="light"] section[data-testid="stSidebar"] [role="radiogroup"] label,
body[data-theme="light"] section[data-testid="stSidebar"] [role="radiogroup"] span,
body[data-theme="light"] section[data-testid="stSidebar"] p,
body[data-theme="light"] section[data-testid="stSidebar"] span,
body[data-theme="light"] section[data-testid="stSidebar"] div {
    color: var(--text-primary) !important;
}
body[data-theme="light"] .block-container {
    background-color: var(--bg-primary) !important;
}
body[data-theme="light"] .stMarkdown h1,
body[data-theme="light"] .stMarkdown h2,
body[data-theme="light"] .stMarkdown h3 {
    color: var(--text-primary) !important;
}
body[data-theme="light"] .stMarkdown p,
body[data-theme="light"] .stMarkdown span,
body[data-theme="light"] .stMarkdown li {
    color: var(--text-secondary) !important;
}
body[data-theme="light"] .stMarkdown strong {
    color: var(--text-primary) !important;
}
body[data-theme="light"] .stButton > button {
    box-shadow: 0 4px 15px rgba(90, 82, 213, 0.25) !important;
}
body[data-theme="light"] .stForm {
    background: linear-gradient(135deg, #FFFFFF, #F5F5F7) !important;
    border-color: var(--border) !important;
}
body[data-theme="light"] div[data-testid="stMetric"]:hover {
    box-shadow: 0 8px 30px rgba(0,0,0,0.08);
}
body[data-theme="light"] div[data-testid="stMetric"] label {
    color: var(--text-secondary) !important;
}
body[data-theme="light"] div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
}
body[data-theme="light"] div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
    color: var(--text-secondary) !important;
}
body[data-theme="light"] .stSelectbox label,
body[data-theme="light"] .stTextInput label,
body[data-theme="light"] .stTextArea label {
    color: var(--text-secondary) !important;
}
body[data-theme="light"] .stSelectbox div[data-baseweb="select"],
body[data-theme="light"] .stTextInput div[data-baseweb="input"],
body[data-theme="light"] .stTextArea div[data-baseweb="textarea"] {
    background-color: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
}
body[data-theme="light"] .stAlert {
    background-color: var(--bg-secondary) !important;
    color: var(--text-secondary) !important;
}
body[data-theme="light"] .stAlert p {
    color: var(--text-secondary) !important;
}
body[data-theme="light"] [data-testid="stHeader"] {
    background-color: var(--bg-primary) !important;
}
body[data-theme="light"] .stTabs [data-baseweb="tab-list"] {
    background-color: var(--bg-card-hover) !important;
}
body[data-theme="light"] .stTabs [data-baseweb="tab"] {
    color: var(--text-secondary) !important;
}
body[data-theme="light"] .stExpander {
    background-color: var(--bg-secondary) !important;
    border-color: var(--border) !important;
}
body[data-theme="light"] .stExpander p,
body[data-theme="light"] .stExpander span,
body[data-theme="light"] .stExpander div {
    color: var(--text-secondary) !important;
}
body[data-theme="light"] .stChatMessage {
    background-color: var(--bg-secondary) !important;
}
body[data-theme="light"] .stChatMessage p,
body[data-theme="light"] .stChatMessage span {
    color: var(--text-secondary) !important;
}
body[data-theme="light"] .stChatInput {
    background-color: var(--bg-secondary) !important;
}
body[data-theme="light"] .stChatInput input {
    color: var(--text-primary) !important;
}
body[data-theme="light"] div[data-baseweb="notification"] {
    background-color: var(--bg-secondary) !important;
    color: var(--text-secondary) !important;
}
body[data-theme="light"] .stDownloadButton > button {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}
body[data-theme="light"] div[data-testid="stFileUploader"] section {
    background: var(--bg-secondary) !important;
    border-color: var(--border) !important;
}
body[data-theme="light"] .stSpinner > div {
    border-top-color: var(--accent) !important;
}

/* File uploader: hide only the duplicate browser-native caption so the
   custom upload UI stays clean, while keeping click + drag & drop working.
   Streamlit renders the zone via [data-testid="stFileUploaderDropzone"]. */
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] {
    display: none !important;
}
[data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed var(--border-light) !important;
    border-radius: 14px !important;
    background: var(--bg-card) !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--accent) !important;
}

/* Onboarding modal */
.onboarding-modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 99998;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
.onboarding-modal-card {
    background: linear-gradient(135deg, var(--bg-card), var(--bg-primary));
    border: 1px solid rgba(108, 99, 255, 0.3);
    border-radius: 24px;
    padding: 40px;
    max-width: 480px;
    width: 100%;
    text-align: center;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    position: relative;
}

/* Real Streamlit X button overlaid on the modal card (top-right corner).
   The card is centered on a 480px wide viewport area, so position the button
   at the card's top-right corner using fixed coordinates. */
.st-key-onboarding_close_btn {
    position: fixed;
    top: calc(50vh - 228px);
    right: calc(50vw - 224px);
    z-index: 99999;
}
.st-key-onboarding_close_btn button {
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    padding: 0 !important;
    border-radius: 9px !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border-light) !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    font-size: 16px !important;
}
.st-key-onboarding_close_btn button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}
.st-key-onboarding_close_btn button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}

/* #9.5 Sidebar native navigation menu */
section[data-testid="stSidebar"] .st-key-nav_Dashboard,
section[data-testid="stSidebar"] .st-key-nav_Upload,
section[data-testid="stSidebar"] .st-key-nav_Análise,
section[data-testid="stSidebar"] .st-key-nav_Chat,
section[data-testid="stSidebar"] .st-key-nav_Categorias,
section[data-testid="stSidebar"] .st-key-nav_Relatórios,
section[data-testid="stSidebar"] .st-key-nav_Configurações {
    margin-bottom: 4px;
}
section[data-testid="stSidebar"] .st-key-nav_Dashboard > button,
section[data-testid="stSidebar"] .st-key-nav_Upload > button,
section[data-testid="stSidebar"] .st-key-nav_Análise > button,
section[data-testid="stSidebar"] .st-key-nav_Chat > button,
section[data-testid="stSidebar"] .st-key-nav_Categorias > button,
section[data-testid="stSidebar"] .st-key-nav_Relatórios > button,
section[data-testid="stSidebar"] .st-key-nav_Configurações > button {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 12px !important;
    padding: 8px 14px !important;
    font-weight: 500 !important;
    letter-spacing: 0.3px !important;
    box-shadow: none !important;
    color: var(--text-secondary) !important;
    justify-content: flex-start !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
section[data-testid="stSidebar"] .st-key-nav_Dashboard > button:hover,
section[data-testid="stSidebar"] .st-key-nav_Upload > button:hover,
section[data-testid="stSidebar"] .st-key-nav_Análise > button:hover,
section[data-testid="stSidebar"] .st-key-nav_Chat > button:hover,
section[data-testid="stSidebar"] .st-key-nav_Categorias > button:hover,
section[data-testid="stSidebar"] .st-key-nav_Relatórios > button:hover,
section[data-testid="stSidebar"] .st-key-nav_Configurações > button:hover {
    background: var(--accent-glow) !important;
    color: var(--text-primary) !important;
    transform: none !important;
}
section[data-testid="stSidebar"] .st-key-nav_Dashboard > button[kind="primary"],
section[data-testid="stSidebar"] .st-key-nav_Upload > button[kind="primary"],
section[data-testid="stSidebar"] .st-key-nav_Análise > button[kind="primary"],
section[data-testid="stSidebar"] .st-key-nav_Chat > button[kind="primary"],
section[data-testid="stSidebar"] .st-key-nav_Categorias > button[kind="primary"],
section[data-testid="stSidebar"] .st-key-nav_Relatórios > button[kind="primary"],
section[data-testid="stSidebar"] .st-key-nav_Configurações > button[kind="primary"] {
    background: var(--accent-glow) !important;
    border-color: var(--accent-glow-strong) !important;
    color: var(--accent) !important;
    font-weight: 700 !important;
}
body[data-theme="light"] section[data-testid="stSidebar"] .st-key-nav_Dashboard > button[kind="primary"],
body[data-theme="light"] section[data-testid="stSidebar"] .st-key-nav_Upload > button[kind="primary"],
body[data-theme="light"] section[data-testid="stSidebar"] .st-key-nav_Análise > button[kind="primary"],
body[data-theme="light"] section[data-testid="stSidebar"] .st-key-nav_Chat > button[kind="primary"],
body[data-theme="light"] section[data-testid="stSidebar"] .st-key-nav_Categorias > button[kind="primary"],
body[data-theme="light"] section[data-testid="stSidebar"] .st-key-nav_Relatórios > button[kind="primary"],
body[data-theme="light"] section[data-testid="stSidebar"] .st-key-nav_Configurações > button[kind="primary"] {
    background: rgba(90, 82, 213, 0.10) !important;
    border-color: rgba(90, 82, 213, 0.25) !important;
    color: var(--accent) !important;
}

/* #10 Mobile Responsiveness */
@media (max-width: 768px) {
    .block-container { padding: 1rem !important; }
    .stMarkdown h1 { font-size: 22px !important; }
    .stMarkdown h2 { font-size: 18px !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    div[data-testid="stMetric"] { padding: 14px !important; }
    .stColumns { flex-direction: column !important; }
    .stColumns > div { flex: 1 1 100% !important; min-width: 100% !important; }
    .stButton > button { padding: 8px 16px !important; font-size: 13px !important; }
    .toast { min-width: 200px !important; max-width: 90vw !important; font-size: 13px !important; padding: 10px 14px !important; }
    .onboarding-modal-card { padding: 24px 16px !important; max-width: 100% !important; }
    .st-key-onboarding_close_btn {
        top: calc(50vh - 224px) !important;
        right: calc(50vw - 180px) !important;
    }
}
</style>
"""


def apply_global_css() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def apply_theme_marker() -> None:
    """Set the ``data-theme`` attribute on the parent document body."""
    import streamlit.components.v1 as components

    theme = st.session_state.get("theme", "dark")
    components.html(
        f"""<script>window.parent.document.body.setAttribute('data-theme', '{theme}');</script>""",
        height=0,
    )
