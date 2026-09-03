"""General-purpose helpers shared across pages.

Contains safe HTML escaping, toasts, the logo loader and small formatting
utilities (currency/date). Keeping these centralized avoids duplication across
the page modules.
"""
import base64
import html as html_lib
from pathlib import Path

import streamlit as st


def escape_html(value) -> str:
    """Escape a dynamic value for safe injection into unsafe_allow_html."""
    if value is None:
        return ""
    return html_lib.escape(str(value), quote=True)


def format_currency(value) -> str:
    """Format a number as a Brazilian-style BRL string (e.g. 1.234,56)."""
    if value is None:
        value = 0
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def toast(message: str, type: str = "success") -> None:
    """Show a floating toast notification with auto-dismiss (5s)."""
    type_class = f"toast-{type}"
    toast_html = f"""
    <div class="toast-container">
        <div class="toast {type_class}" id="investia-toast-{hash(message)}">
            {escape_html(message)}
        </div>
    </div>
    <script>
    (function() {{
        var t = document.getElementById('investia-toast-{hash(message)}');
        if (t) {{
            setTimeout(function() {{ t.classList.add('fade-out'); }}, 4000);
            setTimeout(function() {{ t.remove(); }}, 4500);
        }}
    }})();
    </script>
    """
    st.html(toast_html)


def _get_logo_b64() -> str:
    if "_logo_b64_cached" in st.session_state:
        return st.session_state._logo_b64_cached
    for p in [Path(__file__).parent / "logo.png", Path("frontend/logo.png"), Path("image.png")]:
        if p.exists():
            try:
                b64 = base64.b64encode(p.read_bytes()).decode()
                st.session_state._logo_b64_cached = b64
                return b64
            except OSError:
                pass
    st.session_state._logo_b64_cached = ""
    return ""
