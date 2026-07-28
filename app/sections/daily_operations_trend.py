"""Daily Operations Trend section: order volume vs. labor cost over time."""

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from db import run_query
from queries import DAILY_OPERATIONS_SUMMARY
from theme import AXIS_COLOR, CATEGORICAL_PALETTE, GRIDLINE_COLOR, MUTED_TEXT

_VOLUME_COLOR = CATEGORICAL_PALETTE[0]  # slot 1, blue
_COST_COLOR = CATEGORICAL_PALETTE[1]  # slot 2, orange


def render() -> None:
    st.subheader("Daily Operations Trend")
    st.caption(
        "Daily order volume (bars) against daily labor cost (line) across the "
        "full available history. Shows whether cost is moving in step with "
        "volume or diverging from it - e.g. month-end volume surges or "
        "machine-downtime days where cost rises faster than volume."
    )

    daily = run_query(DAILY_OPERATIONS_SUMMARY).sort_values("operational_date")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=daily["operational_date"],
            y=daily["order_volume"],
            name="Order Volume",
            marker=dict(color=_VOLUME_COLOR, cornerradius=4),
            hovertemplate="Order Volume: %{y:,}<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=daily["operational_date"],
            y=daily["labor_cost"],
            name="Labor Cost",
            mode="lines",
            line=dict(color=_COST_COLOR, width=2),
            hovertemplate="Labor Cost: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED_TEXT),
    )
    fig.update_xaxes(title_text="Date", gridcolor=GRIDLINE_COLOR, linecolor=AXIS_COLOR)
    fig.update_yaxes(
        title_text="Order Volume",
        title_font=dict(color=_VOLUME_COLOR),
        tickfont=dict(color=_VOLUME_COLOR),
        gridcolor=GRIDLINE_COLOR,
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Labor Cost ($)",
        title_font=dict(color=_COST_COLOR),
        tickfont=dict(color=_COST_COLOR),
        showgrid=False,
        secondary_y=True,
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View underlying data"):
        st.dataframe(
            daily[["operational_date", "order_volume", "labor_cost"]],
            hide_index=True,
            use_container_width=True,
        )
