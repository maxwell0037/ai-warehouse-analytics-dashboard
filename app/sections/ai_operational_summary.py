"""AI Operational Summary section - the top-of-dashboard executive summary."""

import streamlit as st

from ai_summary import generate_summary
from kpi_context import build_kpi_payload


def _run_summary() -> None:
    with st.spinner("Generating summary..."):
        st.session_state.ai_summary_result = generate_summary(build_kpi_payload())


def render() -> None:
    st.subheader("AI Operational Summary")

    if "ai_summary_result" not in st.session_state:
        _run_summary()

    result = st.session_state.ai_summary_result

    if result.is_fallback:
        st.warning(result.summary)
    else:
        st.write(result.summary)
        if result.recommendations:
            st.markdown("**Recommendations:**")
            for rec in result.recommendations:
                st.markdown(f"- {rec}")

    if st.button("🔄 Refresh Summary"):
        build_kpi_payload.clear()  # force a genuine refetch, not the cached payload
        _run_summary()
        st.rerun()
