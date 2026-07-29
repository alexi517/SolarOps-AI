"""Anomalies screen — GET /sites/{id}/anomalies (brief §2). Shows all six
required fields, colored by severity (polish pass §3)."""

from __future__ import annotations

import config
import streamlit as st
import style
from api_client import ApiError, ApiUnreachable, get_anomalies


def render() -> None:
    style.inject_global_css()
    style.header("Anomalies", icon="⚠️")

    try:
        anomalies = get_anomalies(config.SITE_ID)
    except ApiUnreachable:
        st.error(f"Cannot reach the API at {config.API_BASE_URL}. Is it running?")
        st.stop()
    except ApiError as exc:
        st.error(f"API error {exc.status_code}: {exc.detail}")
        st.stop()

    if not anomalies:
        with style.card("anomalies-empty"):
            st.markdown(style.pill("All clear", "green"), unsafe_allow_html=True)
            st.write("No anomalies detected in the last 24 hours.")
        return

    for anomaly in anomalies:
        with style.card(f"anomaly-{anomaly['anomaly_id']}"):
            kind = style.severity_pill_kind(anomaly["severity"])
            st.markdown(
                f"{style.pill(anomaly['severity'], kind)} "
                f"**{anomaly['anomaly_type']}** — {anomaly['affected_asset']} — "
                f"confidence {anomaly['confidence']:.0%}",
                unsafe_allow_html=True,
            )
            with st.expander("Detail"):
                st.write("Detected at:", anomaly["detected_at"])
                st.write("Recommended action:", anomaly["recommended_action"])
                st.write("Supporting evidence:")
                for line in anomaly["supporting_evidence"]:
                    st.write(f"- {line}")


if __name__ == "__main__":
    render()
