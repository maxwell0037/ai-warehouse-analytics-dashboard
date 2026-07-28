"""KPI Scorecards section: today's core metrics vs. the previous day."""

from typing import Optional

import pandas as pd
import streamlit as st

from db import run_query
from queries import DAILY_OPERATIONS_SUMMARY


def get_latest_kpis() -> Optional[tuple[pd.Series, pd.Series]]:
    """Return (today, yesterday) rows from Query 1, or None without enough history.

    Shared by this section's UI and the AI Operational Summary's KPI payload,
    so the "latest day vs. previous day" logic exists in exactly one place.
    """
    daily = run_query(DAILY_OPERATIONS_SUMMARY)
    if len(daily) < 2:
        return None
    return daily.iloc[0], daily.iloc[1]


def render() -> None:
    st.subheader("KPI Scorecards")

    latest = get_latest_kpis()
    if latest is None:
        st.warning("Not enough daily history to compute day-over-day deltas.")
        return
    today, yesterday = latest

    def delta(col: str) -> float:
        return today[col] - yesterday[col]

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Orders",
        f"{today['order_volume']:,.0f}",
        f"{delta('order_volume'):+,.0f}",
    )
    col2.metric(
        "Labor Cost",
        f"${today['labor_cost']:,.0f}",
        f"{delta('labor_cost'):+,.0f}",
        delta_color="inverse",
    )
    col3.metric(
        "Productivity",
        f"{today['parcels_per_labor_hour']:.2f} pph",
        f"{delta('parcels_per_labor_hour'):+.2f}",
    )
    col4.metric(
        "Exception Rate",
        f"{today['exception_rate_pct']:.2f}%",
        f"{delta('exception_rate_pct'):+.2f} pts",
        delta_color="inverse",
    )
    col5.metric(
        "Late Shipment Rate",
        f"{today['late_shipment_rate_pct']:.2f}%",
        f"{delta('late_shipment_rate_pct'):+.2f} pts",
        delta_color="inverse",
    )

    st.caption(
        f"Latest day: {today['operational_date']:%b %d, %Y}  ·  "
        f"Compared to {yesterday['operational_date']:%b %d, %Y}"
    )
