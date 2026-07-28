"""Ask AI section - free-form Q&A over the same KPI context used by the
AI Operational Summary."""

import streamlit as st

from ask_ai import ask
from kpi_context import build_kpi_payload


def render() -> None:
    st.subheader("Ask AI")
    st.caption(
        "Ask a natural-language question about today's warehouse operations. "
        "Answered using the same KPI data already shown on this dashboard - "
        "asking a question does not re-query the database."
    )

    question = st.text_input(
        "Your question",
        placeholder="Why did Warehouse B perform worse today?",
        label_visibility="collapsed",
    )

    if st.button("Ask AI"):
        if not question.strip():
            st.warning("Please enter a question first.")
        else:
            with st.spinner("Thinking..."):
                st.session_state.ask_ai_result = ask(question, build_kpi_payload())

    if "ask_ai_result" in st.session_state:
        result = st.session_state.ask_ai_result
        with st.container(border=True):
            if result.is_fallback:
                st.warning(result.answer)
            else:
                st.write(result.answer)
