"""Warehouse Operations Analytics Dashboard - Streamlit entrypoint."""

import streamlit as st

from sections import (
    ai_operational_summary,
    ask_ai,
    carrier_performance_ranking,
    daily_operations_trend,
    exception_rate_by_warehouse,
    kpi_scorecards,
    labor_cost_trend,
    machine_downtime_heatmap,
    productivity_by_warehouse,
    root_cause_analysis,
)

st.set_page_config(page_title="Warehouse Operations Analytics", layout="wide")

st.title("Warehouse Operations Analytics Dashboard")

try:
    ai_operational_summary.render()
except Exception as exc:
    st.error(f"Could not load AI Operational Summary: {exc}")

try:
    kpi_scorecards.render()
except Exception as exc:
    st.error(f"Could not load KPI Scorecards: {exc}")

try:
    daily_operations_trend.render()
except Exception as exc:
    st.error(f"Could not load Daily Operations Trend: {exc}")

try:
    productivity_by_warehouse.render()
except Exception as exc:
    st.error(f"Could not load Productivity by Warehouse & Shift: {exc}")

try:
    labor_cost_trend.render()
except Exception as exc:
    st.error(f"Could not load Labor Cost Trend: {exc}")

try:
    exception_rate_by_warehouse.render()
except Exception as exc:
    st.error(f"Could not load Exception Rate by Warehouse: {exc}")

try:
    machine_downtime_heatmap.render()
except Exception as exc:
    st.error(f"Could not load Machine Downtime Heatmap: {exc}")

try:
    carrier_performance_ranking.render()
except Exception as exc:
    st.error(f"Could not load Carrier Performance Ranking: {exc}")

try:
    root_cause_analysis.render()
except Exception as exc:
    st.error(f"Could not load Operational Root Cause Analysis: {exc}")

try:
    ask_ai.render()
except Exception as exc:
    st.error(f"Could not load Ask AI: {exc}")
