"""Forecasts screen — GET /sites/{id}/forecasts (brief §2). Shows honestly
that only solar is registered; load/battery-SOC render as designed "not yet
available" placeholder cards, never a faked chart (polish pass §4)."""

from __future__ import annotations

import config
import plotly.graph_objects as go
import streamlit as st
import style
from api_client import ApiError, ApiUnreachable, get_forecasts


def _themed_forecast_chart(points: list[dict], kind: str) -> go.Figure:
    timestamps = [p["timestamp"] for p in points]
    values = [p["value"] for p in points]

    fig = go.Figure(
        go.Scatter(
            x=timestamps,
            y=values,
            name=kind,
            mode="lines",
            fill="tozeroy",
            line={"color": "#4CAF50", "width": 2},
            fillcolor="rgba(76, 175, 80, 0.18)",
        )
    )
    return style.apply_chart_theme(fig, height=280)


def render() -> None:
    style.inject_global_css()
    style.header("Forecasts", icon="📈")

    try:
        payload = get_forecasts(config.SITE_ID)
    except ApiUnreachable:
        st.error(f"Cannot reach the API at {config.API_BASE_URL}. Is it running?")
        st.stop()
    except ApiError as exc:
        st.error(f"API error {exc.status_code}: {exc.detail}")
        st.stop()

    for entry in payload["forecasts"]:
        kind = entry["kind"]
        with style.card(f"forecast-{kind}"):
            st.subheader(kind)

            if not entry["available"]:
                st.markdown(style.pill("Not yet available", "amber"), unsafe_allow_html=True)
                st.caption(entry["reason"] or "No reason given by the API.")
                continue

            forecast = entry["forecast"]
            st.markdown(style.pill("Live", "green"), unsafe_allow_html=True)
            st.caption(
                f"{forecast['model_name']} v{forecast['model_version']} — "
                f"generated {forecast['generated_at']} — horizon {forecast['horizon_minutes']} min"
            )
            fig = _themed_forecast_chart(forecast["points"], kind)
            st.plotly_chart(fig, theme=None, config={"displayModeBar": False})
            with st.expander("Raw points"):
                st.json(forecast["points"])


if __name__ == "__main__":
    render()
