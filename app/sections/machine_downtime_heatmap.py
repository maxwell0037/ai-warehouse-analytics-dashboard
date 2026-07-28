"""Machine Downtime Heatmap section."""

import plotly.graph_objects as go
import streamlit as st

from db import run_query
from queries import MACHINE_DOWNTIME_SUMMARY
from theme import MUTED_TEXT, SEQUENTIAL_SCALE

_WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def render() -> None:
    st.subheader("Machine Downtime Heatmap")
    st.caption(
        "Total sorting-machine downtime minutes by warehouse and day of week. "
        "A concentrated hot spot - rather than downtime spread evenly across "
        "days - points to a recurring operational cause instead of random "
        "equipment failure."
    )

    # Query 6 only returns warehouse/weekday combinations that actually had a
    # downtime event. Reshaped into a full grid here for the heatmap (missing
    # combinations = 0 minutes) - not re-queried or re-aggregated.
    data = run_query(MACHINE_DOWNTIME_SUMMARY)
    data["weekday"] = data["weekday"].str.strip()  # Postgres to_char() pads to fixed width

    warehouses = sorted(data["warehouse_name"].unique())
    grid = (
        data.pivot_table(
            index="warehouse_name",
            columns="weekday",
            values="total_downtime_minutes",
            fill_value=0,
        )
        .reindex(index=warehouses, columns=_WEEKDAY_ORDER, fill_value=0)
    )

    fig = go.Figure(
        go.Heatmap(
            z=grid.values,
            x=grid.columns,
            y=grid.index,
            colorscale=SEQUENTIAL_SCALE,
            colorbar=dict(title="Minutes"),
            hovertemplate="%{y} — %{x}<br>Downtime: %{z:.0f} min<extra></extra>",
        )
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED_TEXT),
        xaxis=dict(title=None),
        yaxis=dict(title=None, autorange="reversed"),
    )

    st.plotly_chart(fig, use_container_width=True)

    worst = data.loc[data["total_downtime_minutes"].idxmax()]
    st.info(
        f"**{worst['warehouse_name']} experiences significantly higher downtime on "
        f"{worst['weekday']}s** ({worst['total_downtime_minutes']:.0f} minutes across "
        f"{worst['downtime_events']} events), indicating a recurring operational "
        "bottleneck rather than random equipment failure."
    )

    with st.expander("View underlying data"):
        st.dataframe(data, hide_index=True, use_container_width=True)
