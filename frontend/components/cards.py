"""Reusable cards and placeholders shared across pages.

Centralizes the repeated metric/balance/empty-state card HTML and the skeleton
loader so pages stay compact and consistent.
"""
import streamlit as st
from helpers import format_currency


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<h1 style="font-size:28px;font-weight:800;color:var(--text-primary);margin:0 0 8px;letter-spacing:-0.5px;">{title}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="color:var(--text-muted);font-size:14px;margin:0 0 28px;">{subtitle}</p>',
        unsafe_allow_html=True,
    )


def section_label(text: str, margin: str = "16px", color: str = "var(--text-secondary)") -> None:
    """Uppercase muted section heading used across pages."""
    st.markdown(
        f'<p style="color:{color};font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin:0 0 {margin};">{text}</p>',
        unsafe_allow_html=True,
    )


def metric_card(label, value, delta=None, delta_suffix=""):
    delta_html = ""
    if delta is not None:
        color = "var(--green)" if delta >= 0 else "var(--red)"
        arrow = "↑" if delta >= 0 else "↓"
        delta_html = f'<div style="color:{color};font-size:13px;font-weight:600;margin-top:6px;">{arrow} {abs(delta):.1f}{delta_suffix}</div>'
    return f"""
    <div style="background:linear-gradient(135deg,var(--bg-card),var(--bg-secondary));border:1px solid var(--border);border-radius:16px;padding:22px;transition:all 0.3s ease;">
        <div style="color:var(--text-secondary);font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">{label}</div>
        <div style="color:var(--text-primary);font-size:26px;font-weight:700;">{value}</div>
        {delta_html}
    </div>
    """


def balance_card(balance) -> str:
    color = "var(--green)" if balance >= 0 else "var(--red)"
    return f"""
    <div style="background:linear-gradient(135deg,var(--bg-card),var(--bg-secondary));border:1px solid var(--border);border-radius:16px;padding:22px;">
        <div style="color:var(--text-secondary);font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">Saldo</div>
        <div style="color:{color};font-size:26px;font-weight:700;">R$ {format_currency(balance)}</div>
    </div>
    """


def empty_state(emoji: str, title: str, subtitle: str) -> None:
    st.markdown(f"""
    <div style="text-align:center;padding:60px 20px;background:linear-gradient(135deg,var(--bg-card),var(--bg-primary));border:1px solid var(--border);border-radius:20px;">
        <div style="font-size:48px;margin-bottom:16px;">{emoji}</div>
        <h3 style="color:var(--text-primary);font-weight:700;margin:0 0 8px;">{title}</h3>
        <p style="color:var(--text-secondary);margin:0;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def skeleton_loader(count=3, cols=None):
    """Render animated skeleton placeholder cards while data loads."""
    card_html = """
    <div class="skeleton-card">
        <div class="skeleton-line short" style="margin-bottom:10px;"></div>
        <div class="skeleton-line medium"></div>
        <div class="skeleton-line short" style="margin-top:10px;"></div>
    </div>
    """
    if cols:
        columns = st.columns(cols)
        for i in range(count):
            with columns[i % cols]:
                st.markdown(card_html, unsafe_allow_html=True)
    else:
        for _ in range(count):
            st.markdown(card_html, unsafe_allow_html=True)
