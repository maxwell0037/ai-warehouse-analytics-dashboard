"""Exception Rate by Warehouse section."""

import plotly.graph_objects as go
import streamlit as st

from db import run_query
from queries import EXCEPTION_RATE_BY_WAREHOUSE
from theme import CATEGORICAL_PALETTE, GRIDLINE_COLOR, MUTED_TEXT, WARNING_COLOR

_BASE_COLOR = CATEGORICAL_PALETTE[0]  # neutral default; the axis label already identifies the warehouse


def render() -> None:
    st.subheader("Exception Rate by Warehouse")
    st.caption(
        "Share of parcels flagged as an exception (damaged, mislabeled, "
        "misrouted, or lost), by warehouse - ranked worst to best. The "
        "highlighted warehouse is where quality issues are most concentrated "
        "and worth investigating first."
    )

    # Query 5 already orders by exception_rate_pct DESC - used as-is, not re-sorted.
    data = run_query(EXCEPTION_RATE_BY_WAREHOUSE)

    category_order = data["warehouse_name"].tolist()  # descending order from the query, highest first
    worst_idx = data["exception_rate_pct"].idxmax()

    bar_colors = [WARNING_COLOR if idx == worst_idx else _BASE_COLOR for idx in data.index]

    fig = go.Figure(
        go.Bar(
            x=data["exception_rate_pct"],
            y=data["warehouse_name"],
            orientation="h",
            marker=dict(color=bar_colors, cornerradius=4),
            text=data["exception_rate_pct"].map(lambda v: f"{v:.2f}%"),
            textposition="outside",
            customdata=data[["total_parcels", "exception_count"]],
            hovertemplate=(
                "%{y}<br>"
                "Exception Rate: %{x:.2f}%<br>"
                "Total Parcels: %{customdata[0]:,}<br>"
                "Exception Count: %{customdata[1]:,}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        yaxis=dict(
            categoryorder="array",
            categoryarray=category_order,
            autorange="reversed",  # highest exception rate (first in category_order) shown first, at top
            title=None,
        ),
        xaxis=dict(
            title="Exception Rate (%)",
            gridcolor=GRIDLINE_COLOR,
            range=[0, data["exception_rate_pct"].max() * 1.2],  # headroom for outside bar labels
        ),
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED_TEXT),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View underlying data"):
        st.dataframe(data, hide_index=True, use_container_width=True)
