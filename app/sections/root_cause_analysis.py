"""Operational Root Cause Analysis section.

Combines several already-tested KPI queries (no new SQL, no re-aggregation
in the database) into a single warehouse/date table and applies deterministic
Python business rules to label the most likely operational cause per row.
"""

import pandas as pd
import streamlit as st

from db import run_query
from queries import (
    CARRIER_PERFORMANCE_RANKING,
    EXCEPTION_RATE_BY_WAREHOUSE,
    LATE_SHIPMENT_RATE,
    MACHINE_DOWNTIME_SUMMARY,
    ROOT_CAUSE_LABOR_COST_INCREASE,
)


def assemble_table() -> tuple[pd.DataFrame, bool]:
    # Backbone: Query 8 is already at warehouse+date grain and already carries
    # labor cost, volume, labor hours, and the downtime/month-end flags this
    # analysis is built on - it's the natural base for this table.
    base = run_query(ROOT_CAUSE_LABOR_COST_INCREASE).copy()
    base["work_date"] = pd.to_datetime(base["work_date"])

    # Productivity: arithmetic on two columns Query 8 already returns, not a new query.
    base["productivity"] = base["order_volume"] / base["labor_hours"]

    # Exception Rate by Warehouse has no date dimension - the finest grain
    # available is each warehouse's overall average, attached to every row
    # for that warehouse.
    exceptions = run_query(EXCEPTION_RATE_BY_WAREHOUSE)[["warehouse_name", "exception_rate_pct"]]
    base = base.merge(exceptions, on="warehouse_name", how="left")

    # Machine Downtime Summary is grained by warehouse + weekday, not exact
    # date - matched here by the weekday name of each row's own date.
    downtime = run_query(MACHINE_DOWNTIME_SUMMARY).copy()
    downtime["weekday"] = downtime["weekday"].str.strip()
    downtime = downtime[["warehouse_name", "weekday", "total_downtime_minutes"]]
    base["weekday"] = base["work_date"].dt.day_name()
    base = base.merge(downtime, on=["warehouse_name", "weekday"], how="left")
    base["total_downtime_minutes"] = base["total_downtime_minutes"].fillna(0)

    # Late Shipment Rate is grained by warehouse + week - matched here by the
    # Monday-starting week each row's date falls in, the same convention
    # Query 7's own date_trunc('week', ...) uses.
    late = run_query(LATE_SHIPMENT_RATE).copy()
    late["week_start"] = pd.to_datetime(late["week_start"])
    base["week_start"] = base["work_date"] - pd.to_timedelta(base["work_date"].dt.dayofweek, unit="D")
    base = base.merge(late[["warehouse_name", "week_start", "late_shipment_rate_pct"]], on=["warehouse_name", "week_start"], how="left")

    # Carrier Performance Ranking has no warehouse dimension (any carrier can
    # serve any warehouse) - used only as a system-wide signal of whether a
    # carrier is currently a clear outlier, not attributed to a specific row.
    carriers = run_query(CARRIER_PERFORMANCE_RANKING)
    worst_rate = carriers["late_shipment_rate_pct"].max()
    other_carriers_median = carriers.loc[carriers["late_shipment_rate_pct"] != worst_rate, "late_shipment_rate_pct"].median()
    carrier_risk_elevated = worst_rate > other_carriers_median * 3

    return base, carrier_risk_elevated


def classify(base: pd.DataFrame, carrier_risk_elevated: bool) -> pd.Series:
    productivity_threshold = base["productivity"].median()
    exception_threshold = base["exception_rate_pct"].median()
    late_threshold = base["late_shipment_rate_pct"].median()

    def classify_row(row) -> str:
        # Query 8 already flags whether this exact warehouse/date had a downtime
        # event - more precise than the weekday-matched Downtime Minutes display
        # column, so the classification uses it directly rather than re-deriving
        # a threshold from that coarser figure.
        high_downtime = row["had_downtime"]
        low_productivity = row["productivity"] < productivity_threshold
        high_exception = row["exception_rate_pct"] > exception_threshold
        high_late = row["late_shipment_rate_pct"] > late_threshold
        high_cost = row["cost_variance_vs_baseline"] > 0

        # High exception rate + downtime -> Operational Bottleneck
        if high_exception and high_downtime:
            return "Operational Bottleneck"
        # High downtime + low productivity -> Machine Downtime
        if high_downtime and low_productivity:
            return "Machine Downtime"
        # High labor cost + month-end volume increase -> Volume Surge
        if high_cost and row["is_month_end"]:
            return "Volume Surge"
        # High late shipment rate + poor carrier performance -> Carrier Delay
        if high_late and carrier_risk_elevated:
            return "Carrier Delay"
        return "Other / Mixed Factors"

    return base.apply(classify_row, axis=1)


def render() -> None:
    st.subheader("Operational Root Cause Analysis")
    st.caption(
        "Combines labor cost, productivity, exception rate, downtime, and late "
        "shipment signals for the warehouse-days with the largest cost swings, "
        "and applies fixed business rules (not AI) to flag the most likely "
        "cause. Exception Rate is each warehouse's overall average (its source "
        "query has no date breakdown); Downtime Minutes and Late Shipment Rate "
        "are matched by day-of-week and week respectively - the finest grain "
        "the existing queries provide. Click a column header to sort; rows "
        "with an identified cause are highlighted."
    )

    base, carrier_risk_elevated = assemble_table()
    base["likely_root_cause"] = classify(base, carrier_risk_elevated)

    display = base[
        [
            "warehouse_name",
            "work_date",
            "labor_cost",
            "productivity",
            "exception_rate_pct",
            "total_downtime_minutes",
            "late_shipment_rate_pct",
            "likely_root_cause",
        ]
    ].rename(
        columns={
            "warehouse_name": "Warehouse",
            "work_date": "Date",
            "labor_cost": "Labor Cost",
            "productivity": "Productivity",
            "exception_rate_pct": "Exception Rate",
            "total_downtime_minutes": "Downtime Minutes",
            "late_shipment_rate_pct": "Late Shipment Rate",
            "likely_root_cause": "Likely Root Cause",
        }
    )

    # A pandas Styler (row background coloring) disables st.dataframe's
    # interactive column sort, which the "sortable" requirement also needs -
    # so abnormal rows are flagged with a leading icon column instead, which
    # keeps the grid a plain, fully sortable dataframe.
    display.insert(
        0,
        "Flag",
        display["Likely Root Cause"].apply(lambda cause: "🔶" if cause != "Other / Mixed Factors" else ""),
    )

    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Flag": st.column_config.TextColumn(width="small"),
            "Date": st.column_config.DateColumn(format="MMM D, YYYY"),
            "Labor Cost": st.column_config.NumberColumn(format="$%.2f"),
            "Productivity": st.column_config.NumberColumn(format="%.2f pph"),
            "Exception Rate": st.column_config.NumberColumn(format="%.2f%%"),
            "Downtime Minutes": st.column_config.NumberColumn(format="%.0f"),
            "Late Shipment Rate": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )
