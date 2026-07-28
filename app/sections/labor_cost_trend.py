"""Labor Cost Trend section: daily labor cost per warehouse vs. its 7-day rolling average."""

import plotly.graph_objects as go
import streamlit as st

from db import run_query
from queries import LABOR_COST_TREND
from theme import GRIDLINE_COLOR, MUTED_TEXT, warehouse_color_map


def render() -> None:
    st.subheader("Labor Cost Trend")
    st.caption(
        "Daily labor cost per warehouse (solid line) against its own 7-day "
        "rolling average (dashed line), across the full available history. "
        "Separates a single noisy day from a genuine upward or downward trend "
        "in labor spend, per warehouse."
    )

    # Query 3 already computes the rolling average in SQL - plotted as-is, not recomputed here.
    data = run_query(LABOR_COST_TREND)

    color_map = warehouse_color_map(data["warehouse_name"])

    fig = go.Figure()

    for wh in sorted(data["warehouse_name"].unique()):
        subset = data[data["warehouse_name"] == wh].sort_values("work_date")
        color = color_map[wh]

        fig.add_trace(
            go.Scatter(
                x=subset["work_date"],
                y=subset["daily_labor_cost"],
                name=f"{wh} — Daily Cost",
                legendgroup=wh,
                mode="lines",
                line=dict(color=color, width=2),
                hovertemplate=f"{wh} Daily Cost: " + "$%{y:,.0f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=subset["work_date"],
                y=subset["rolling_7day_avg_cost"],
                name=f"{wh} — 7-Day Avg",
                legendgroup=wh,
                mode="lines",
                line=dict(color=color, width=2, dash="dash"),
                hovertemplate=f"{wh} 7-Day Avg: " + "$%{y:,.0f}<extra></extra>",
            )
        )

    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED_TEXT),
    )
    fig.update_xaxes(title_text="Date", gridcolor=GRIDLINE_COLOR)
    fig.update_yaxes(title_text="Labor Cost ($)", gridcolor=GRIDLINE_COLOR)

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View underlying data"):
        st.dataframe(data, hide_index=True, use_container_width=True)
