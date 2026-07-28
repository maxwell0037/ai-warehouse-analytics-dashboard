"""Builds the structured KPI payload used as AI context for the Operational Summary.

Reuses the same query loader and the same helper functions already powering
the dashboard sections - no new SQL, no re-derived business logic.
"""

from typing import Any

import pandas as pd
import streamlit as st

from db import run_query
from queries import (
    CARRIER_PERFORMANCE_RANKING,
    EXCEPTION_RATE_BY_WAREHOUSE,
    MACHINE_DOWNTIME_SUMMARY,
    PRODUCTIVITY_BY_WAREHOUSE,
)
from sections.kpi_scorecards import get_latest_kpis
from sections.root_cause_analysis import assemble_table, classify


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a query result DataFrame into JSON-safe records (dates -> ISO strings)."""
    clean = df.copy()
    for col in clean.columns:
        if pd.api.types.is_datetime64_any_dtype(clean[col]):
            clean[col] = clean[col].dt.strftime("%Y-%m-%d")
    return clean.to_dict(orient="records")


@st.cache_data(ttl=300)
def build_kpi_payload() -> dict[str, Any]:
    """Assemble the full KPI context payload shared by the AI Operational
    Summary and Ask AI.

    Mirrors exactly what's already on the dashboard - the same Query 1 latest
    day/yesterday pair behind KPI Scorecards, Query 2/5/6/4 in full, and the
    same assembled + classified table behind Operational Root Cause Analysis.

    Cached (5 min TTL) so asking an Ask AI question, or simply re-rendering
    the page, does not re-run every underlying query - it reuses the same
    payload the AI Operational Summary already built. Call
    build_kpi_payload.clear() to force a genuine refetch (used by the
    Summary's "Refresh Summary" button).
    """
    latest = get_latest_kpis()
    kpis: dict[str, Any] = {}
    if latest is not None:
        today, yesterday = latest
        kpis = {
            "today": {
                "date": str(today["operational_date"]),
                "order_volume": float(today["order_volume"]),
                "labor_hours": float(today["labor_hours"]),
                "labor_cost": float(today["labor_cost"]),
                "productivity_pph": float(today["parcels_per_labor_hour"]),
                "exception_rate_pct": float(today["exception_rate_pct"]),
                "late_shipment_rate_pct": float(today["late_shipment_rate_pct"]),
            },
            "yesterday": {
                "date": str(yesterday["operational_date"]),
                "order_volume": float(yesterday["order_volume"]),
                "labor_hours": float(yesterday["labor_hours"]),
                "labor_cost": float(yesterday["labor_cost"]),
                "productivity_pph": float(yesterday["parcels_per_labor_hour"]),
                "exception_rate_pct": float(yesterday["exception_rate_pct"]),
                "late_shipment_rate_pct": float(yesterday["late_shipment_rate_pct"]),
            },
        }

    productivity = _records(run_query(PRODUCTIVITY_BY_WAREHOUSE))
    exceptions = _records(run_query(EXCEPTION_RATE_BY_WAREHOUSE))

    downtime_df = run_query(MACHINE_DOWNTIME_SUMMARY)
    downtime_df["weekday"] = downtime_df["weekday"].str.strip()  # Postgres to_char() pads to fixed width
    downtime = _records(downtime_df)

    carrier_performance = _records(run_query(CARRIER_PERFORMANCE_RANKING))

    root_base, carrier_risk_elevated = assemble_table()
    root_base = root_base.copy()
    root_base["likely_root_cause"] = classify(root_base, carrier_risk_elevated)
    root_causes = _records(
        root_base[
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
        ]
    )

    return {
        "kpis": kpis,
        "productivity": productivity,
        "exceptions": exceptions,
        "downtime": downtime,
        "carrier_performance": carrier_performance,
        "root_causes": root_causes,
    }
