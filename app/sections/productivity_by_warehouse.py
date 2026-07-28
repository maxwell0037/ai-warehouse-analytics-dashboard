"""Productivity by Warehouse & Shift section."""

import plotly.graph_objects as go
import streamlit as st

from db import run_query
from queries import PRODUCTIVITY_BY_WAREHOUSE
from theme import CRITICAL_COLOR, GRIDLINE_COLOR, MUTED_TEXT, warehouse_color_map


def render() -> None:
    st.subheader("Productivity by Warehouse & Shift")
    st.caption(
        "Parcels processed per labor hour for every warehouse/shift combination, "
        "ranked lowest to highest. This is where a staffing or process problem "
        "shows up before it becomes a missed SLA - a low bar means labor hours "
        "are being spent without matching throughput."
    )

    # Query 2 already orders by parcels_per_labor_hour ASC - used as-is, not re-sorted.
    data = run_query(PRODUCTIVITY_BY_WAREHOUSE)

    labels = data["warehouse_name"] + " — " + data["shift_name"]
    category_order = labels.tolist()  # ascending order from the query, lowest first

    warehouses = data["warehouse_name"].unique().tolist()
    color_map = warehouse_color_map(data["warehouse_name"])

    lowest_idx = data["parcels_per_labor_hour"].idxmin()

    fig = go.Figure()

    for wh in warehouses:
        subset = data[data["warehouse_name"] == wh]
        subset_labels = subset["warehouse_name"] + " — " + subset["shift_name"]
        line_colors = [CRITICAL_COLOR if idx == lowest_idx else "rgba(0,0,0,0)" for idx in subset.index]
        line_widths = [3 if idx == lowest_idx else 0 for idx in subset.index]

        fig.add_trace(
            go.Bar(
                name=wh,
                x=subset["parcels_per_labor_hour"],
                y=subset_labels,
                orientation="h",
                marker=dict(
                    color=color_map[wh],
                    cornerradius=4,
                    line=dict(color=line_colors, width=line_widths),
                ),
                customdata=subset[["total_parcels", "total_labor_hours"]],
                hovertemplate=(
                    "%{y}<br>"
                    "Productivity: %{x:.2f} parcels/labor hour<br>"
                    "Total Parcels: %{customdata[0]:,}<br>"
                    "Total Labor Hours: %{customdata[1]:,.1f}"
                    "<extra></extra>"
                ),
            )
        )

    lowest_row = data.loc[lowest_idx]
    fig.add_annotation(
        x=lowest_row["parcels_per_labor_hour"],
        y=labels.loc[lowest_idx],
        text=f"⚠ Lowest productivity: {lowest_row['parcels_per_labor_hour']:.2f} pph",
        showarrow=True,
        arrowhead=2,
        arrowcolor=CRITICAL_COLOR,
        font=dict(color=CRITICAL_COLOR),
        ax=70,
        ay=0,
    )

    fig.update_layout(
        yaxis=dict(
            categoryorder="array",
            categoryarray=category_order,
            autorange="reversed",  # lowest-productivity row (first in category_order) shown first, at top
            title=None,
        ),
        xaxis=dict(title="Parcels per Labor Hour", gridcolor=GRIDLINE_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title="Warehouse"),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED_TEXT),
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View underlying data"):
        st.dataframe(data, hide_index=True, use_container_width=True)
