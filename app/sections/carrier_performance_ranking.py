"""Carrier Performance Ranking section."""

import plotly.graph_objects as go
import streamlit as st

from db import run_query
from queries import CARRIER_PERFORMANCE_RANKING
from theme import CATEGORICAL_PALETTE, GRIDLINE_COLOR, MUTED_TEXT, WARNING_COLOR

_BASE_COLOR = CATEGORICAL_PALETTE[0]  # neutral default; the axis label already identifies the carrier


def render() -> None:
    st.subheader("Carrier Performance Ranking")
    st.caption(
        "Late shipment rate by carrier, ranked worst to best. The highlighted "
        "carrier is the one most responsible for missed delivery commitments "
        "and worth escalating first."
    )

    # Query 4 already orders by worst_performance_rank ASC (rank 1 = worst) - used as-is, not re-sorted.
    data = run_query(CARRIER_PERFORMANCE_RANKING)

    # Query 4's SELECT list exposes delivered_parcels and late_shipment_rate_pct but not
    # the raw late count (only the query's internal CTE has it) - derived here from the
    # two columns the query does return, not from any new SQL.
    data["late_shipments"] = (data["delivered_parcels"] * data["late_shipment_rate_pct"] / 100).round().astype(int)

    category_order = data["carrier_name"].tolist()  # worst-to-best order from the query
    worst_idx = data["worst_performance_rank"].idxmin()  # rank 1 = worst

    bar_colors = [WARNING_COLOR if idx == worst_idx else _BASE_COLOR for idx in data.index]

    fig = go.Figure(
        go.Bar(
            x=data["late_shipment_rate_pct"],
            y=data["carrier_name"],
            orientation="h",
            marker=dict(color=bar_colors, cornerradius=4),
            text=data["late_shipment_rate_pct"].map(lambda v: f"{v:.2f}%"),
            textposition="outside",
            customdata=data[["delivered_parcels", "late_shipments"]],
            hovertemplate=(
                "%{y}<br>"
                "Late Shipment Rate: %{x:.2f}%<br>"
                "Total Shipments: %{customdata[0]:,}<br>"
                "Late Shipments: %{customdata[1]:,}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        yaxis=dict(
            categoryorder="array",
            categoryarray=category_order,
            autorange="reversed",  # worst carrier (first in category_order) shown first, at top
            title=None,
        ),
        xaxis=dict(
            title="Late Shipment Rate (%)",
            gridcolor=GRIDLINE_COLOR,
            range=[0, data["late_shipment_rate_pct"].max() * 1.2],  # headroom for outside bar labels
        ),
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED_TEXT),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    worst = data.loc[worst_idx]
    best = data.loc[data["worst_performance_rank"].idxmax()]
    st.info(
        f"**{worst['carrier_name']} consistently underperforms the other carriers**, "
        f"with a late shipment rate of {worst['late_shipment_rate_pct']:.2f}% versus "
        f"{best['late_shipment_rate_pct']:.2f}% for {best['carrier_name']}, the best "
        "performer. This suggests carrier-specific operational issues rather than "
        "warehouse processing delays."
    )

    with st.expander("View underlying data"):
        st.dataframe(data, hide_index=True, use_container_width=True)
