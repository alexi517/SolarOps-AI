"""Recommendations screen — GET /sites/{id}/recommendations, with a button
to run a fresh cycle via POST /sites/{id}/decision-cycle (brief §2, polish
pass §3)."""

from __future__ import annotations

import config
import streamlit as st
import style
from api_client import ApiError, ApiUnreachable, get_recommendations, run_decision_cycle


def render() -> None:
    style.inject_global_css()
    style.header("Recommendations", icon="🧠")

    if st.button("Run decision cycle now", type="primary"):
        try:
            cycle = run_decision_cycle(config.SITE_ID)
        except ApiUnreachable:
            st.error(f"Cannot reach the API at {config.API_BASE_URL}. Is it running?")
            st.stop()
        except ApiError as exc:
            st.error(f"API error {exc.status_code}: {exc.detail}")
            st.stop()
        command = cycle["command"]
        st.success(
            f"Decision cycle ran — command {command['command_id']} is now "
            f"{command['status']}. Check the Approvals screen if it's awaiting approval."
        )
        ranked = cycle["recommendations"]
    else:
        try:
            ranked = get_recommendations(config.SITE_ID)
        except ApiUnreachable:
            st.error(f"Cannot reach the API at {config.API_BASE_URL}. Is it running?")
            st.stop()
        except ApiError as exc:
            st.error(f"API error {exc.status_code}: {exc.detail}")
            st.stop()

    recommendations = ranked["recommendations"]
    if not recommendations:
        with style.card("recommendations-empty"):
            st.info("No recommendations available.")
        return

    for index, recommendation in enumerate(recommendations):
        label = (
            f"{index + 1}. {recommendation['action']} — "
            f"confidence {recommendation['confidence']:.0%}"
        )
        with style.card(f"recommendation-{recommendation['recommendation_id']}"):
            st.subheader(label)
            st.write(recommendation["reason"])
            st.caption(f"Params: {recommendation['params']}")

            with st.expander("Why this, why now, alternatives, risks"):
                st.write("**Why now:**", recommendation["why_now"] or "—")
                st.write("**Evidence:**")
                for line in recommendation["evidence"]:
                    st.write(f"- {line}")
                st.write("**Alternatives considered:**")
                for line in recommendation["alternatives"]:
                    st.write(f"- {line}")
                st.write("**Risks:**")
                for line in recommendation["risks"]:
                    st.write(f"- {line}")


if __name__ == "__main__":
    render()
