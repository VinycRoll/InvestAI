"""Plotly chart builders and theme-aware styling shared across pages.

Centralizes the repeated pie / trend / heatmap charts and the theme tokens so
dashboard and analysis pages render identical figures.
"""
from datetime import datetime as _dt

import plotly.graph_objects as go
import streamlit as st

CHART_COLORS = [
    "#6C63FF", "#4ECDC4", "#FFD93D", "#FF4757", "#00D4AA", "#FF6B6B",
    "#A8E6CF", "#DDA0DD", "#98D8C8", "#F7DC6F",
]


def plotly_theme() -> dict:
    """Return theme-aware color tokens for Plotly, based on session theme."""
    is_light = st.session_state.get("theme", "dark") == "light"
    return {
        "is_light": is_light,
        "text": "#1A1A2E" if is_light else "#E8E8ED",
        "muted": "#5A5A7E" if is_light else "#8B8B9E",
        "grid": "rgba(0,0,0,0.10)" if is_light else "rgba(255,255,255,0.06)",
        "paper": "rgba(0,0,0,0)",
        "plot": "rgba(0,0,0,0)",
    }


def apply_plot_theme(fig) -> go.Figure:
    """Apply a consistent theme-aware font to a Plotly figure footer/layout."""
    t = plotly_theme()
    fig.update_layout(
        paper_bgcolor=t["paper"],
        plot_bgcolor=t["plot"],
        font=dict(color=t["muted"]),
    )
    return fig


def category_pie(categories: dict, hole: float, height: int,
                 text_font_size: int = 13, legend_font_size: int = 12) -> go.Figure:
    """Build a donut chart of spending by category."""
    t = plotly_theme()
    fig = go.Figure(data=[go.Pie(
        labels=list(categories.keys()),
        values=[c["total"] for c in categories.values()],
        hole=hole,
        marker=dict(colors=CHART_COLORS[:len(categories)]),
        textfont=dict(size=text_font_size, color=t["text"]),
    )])
    fig.update_layout(
        showlegend=True,
        legend=dict(font=dict(size=legend_font_size, color=t["muted"])),
        paper_bgcolor=t["paper"],
        plot_bgcolor=t["plot"],
        margin=dict(t=0, b=0, l=0, r=0),
        height=height,
    )
    return fig


def render_category_pie(categories: dict, hole: float, height: int,
                        text_font_size: int = 13, legend_font_size: int = 12) -> None:
    st.plotly_chart(category_pie(categories, hole, height, text_font_size, legend_font_size),
                    use_container_width=True)


def monthly_trend(monthly_data: dict) -> go.Figure:
    """Build the income/expense line chart over the available months."""
    months = sorted(monthly_data.keys())
    income_vals = [monthly_data[m].get("income", 0) for m in months]
    expense_vals = [monthly_data[m].get("expenses", 0) for m in months]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months, y=income_vals, name="Receitas",
        line=dict(color="#00D4AA", width=2.5), fill="tozeroy",
        fillcolor="rgba(0,212,170,0.08)", mode="lines+markers",
        marker=dict(size=6),
    ))
    fig.add_trace(go.Scatter(
        x=months, y=expense_vals, name="Despesas",
        line=dict(color="#FF4757", width=2.5), fill="tozeroy",
        fillcolor="rgba(255,71,87,0.08)", mode="lines+markers",
        marker=dict(size=6),
    ))
    t = plotly_theme()
    fig.update_layout(
        paper_bgcolor=t["paper"], plot_bgcolor=t["plot"],
        font=dict(color=t["muted"]), margin=dict(t=10, b=30, l=50, r=20),
        height=300, legend=dict(font=dict(size=12, color=t["muted"]), orientation="h", y=1.12),
        xaxis=dict(gridcolor=t["grid"], showgrid=False),
        yaxis=dict(gridcolor=t["grid"], tickprefix="R$ ", tickformat=",.0f"),
    )
    return fig


def spending_heatmap(daily_data: dict) -> go.Figure:
    """Build the weekly spending heatmap (Seg..Dom rows) from daily expenses."""
    dates = sorted(daily_data.keys())
    start = _dt.strptime(dates[0], "%Y-%m-%d")
    weeks = {}
    for d_str in dates:
        d = _dt.strptime(d_str, "%Y-%m-%d")
        week_num = (d - start).days // 7
        day_of_week = d.weekday()
        weeks.setdefault(week_num, {})[day_of_week] = daily_data[d_str].get("expenses", 0)
    num_weeks = max(weeks.keys()) + 1 if weeks else 1
    z = []
    for dow in range(7):
        row = []
        for w in range(num_weeks):
            row.append(weeks.get(w, {}).get(dow, 0))
        z.append(row)
    week_labels = [(start.strftime("%b %d") if w == 0 else "") for w in range(num_weeks)]
    fig = go.Figure(data=go.Heatmap(
        z=z, x=week_labels,
        y=["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"],
        colorscale=[[0, "rgba(0,0,0,0)"], [0.25, "rgba(255,71,87,0.15)"], [0.5, "rgba(255,71,87,0.4)"], [1, "rgba(255,71,87,0.85)"]],
        hoverongaps=False, showscale=False,
    ))
    t = plotly_theme()
    fig.update_layout(
        paper_bgcolor=t["paper"], plot_bgcolor=t["plot"],
        font=dict(color=t["muted"], size=11), margin=dict(t=10, b=10, l=10, r=10),
        height=180, xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, autorange="reversed"),
    )
    return fig


def render_monthly_trend(monthly_data: dict) -> None:
    st.plotly_chart(monthly_trend(monthly_data), use_container_width=True)


def render_spending_heatmap(daily_data: dict) -> None:
    st.plotly_chart(spending_heatmap(daily_data), use_container_width=True)
