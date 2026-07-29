"""Overview screen — GET /sites/{id}/state (brief §2), with GET .../forecasts
for the solar-vs-load chart. Presentation only (polish pass §3-4)."""

from __future__ import annotations

import config
import plotly.graph_objects as go
import streamlit as st
import style
from api_client import ApiError, ApiUnreachable, get_forecasts, get_state


def _battery_gauge(soc_pct: float) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=soc_pct,
            number={"suffix": "%", "font": {"size": 36}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": "#4CAF50"},
                "bgcolor": "white",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 20], "color": "#FBE3E1"},
                    {"range": [20, 80], "color": "#E3F3E4"},
                    {"range": [80, 100], "color": "#FFF3D6"},
                ],
            },
            title={"text": "Battery SOC"},
        )
    )
    return style.apply_gauge_theme(fig)


def _solar_vs_load_chart(points: list[dict], current_load_kw: float) -> go.Figure:
    timestamps = [p["timestamp"] for p in points]
    solar_values = [p["value"] for p in points]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=solar_values,
            name="Solar (forecast)",
            mode="lines",
            fill="tozeroy",
            line={"color": "#4CAF50", "width": 2},
            fillcolor="rgba(76, 175, 80, 0.18)",
        )
    )
    # No load forecast is registered (6a) — the current reading is shown as a
    # flat reference line, honestly labelled, never a fabricated trend.
    fig.add_trace(
        go.Scatter(
            x=[timestamps[0], timestamps[-1]],
            y=[current_load_kw, current_load_kw],
            name="Building load (current — no forecast yet)",
            mode="lines",
            line={"color": "#8A2A22", "width": 2, "dash": "dash"},
        )
    )
    fig.update_layout(title="Solar forecast vs current load")
    fig.update_yaxes(title="kW")
    return style.apply_chart_theme(fig, height=300, show_legend=True)


def render() -> None:
    style.inject_global_css()
    style.header("Overview", icon="🏭")

    try:
        state = get_state(config.SITE_ID)
    except ApiUnreachable:
        st.error(f"Cannot reach the API at {config.API_BASE_URL}. Is it running?")
        st.stop()
    except ApiError as exc:
        st.error(f"API error {exc.status_code}: {exc.detail}")
        st.stop()

    if state["grid_status"] != "CONNECTED":
        st.markdown(
            style.pill(f"Grid status: {state['grid_status']}", "red"), unsafe_allow_html=True
        )
    if state["any_asset_offline"]:
        st.markdown(style.pill("At least one asset is offline", "amber"), unsafe_allow_html=True)
    if state["fault_codes"]:
        st.markdown(
            style.pill(f"Active faults: {', '.join(state['fault_codes'])}", "red"),
            unsafe_allow_html=True,
        )

    with style.card("overview-metrics"):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Battery SOC", f"{state['battery_soc_pct']:.1f} %")
        col2.metric("Solar Power", f"{state['solar_power_kw']:.1f} kW")
        col3.metric("Building Load", f"{state['building_load_kw']:.1f} kW")
        col4.metric("Grid Power", f"{state['grid_power_kw']:.1f} kW")

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Battery Temp", f"{state['battery_temp_c']:.1f} °C")
        col6.metric("Inverter Temp", f"{state['inverter_temp_c']:.1f} °C")
        col7.metric("Grid Status", state["grid_status"])
        col8.metric("Inverter Status", state["inverter_status"])

    chart_col, gauge_col = st.columns([2, 1])
    with chart_col, style.card("overview-solar-load"):
        try:
            forecasts = get_forecasts(config.SITE_ID)
        except (ApiUnreachable, ApiError):
            st.info("Solar/load chart unavailable — could not reach the forecasts endpoint.")
        else:
            solar = next(
                (f for f in forecasts["forecasts"] if f["kind"] == "SOLAR_GENERATION"), None
            )
            if solar and solar["available"]:
                fig = _solar_vs_load_chart(
                    solar["forecast"]["points"], state["building_load_kw"]
                )
                st.plotly_chart(fig, theme=None, config={"displayModeBar": False})
            else:
                st.info("Solar forecast not available yet.")

    with gauge_col, style.card("overview-battery-gauge"):
        fig = _battery_gauge(state["battery_soc_pct"])
        st.plotly_chart(fig, theme=None, config={"displayModeBar": False})

    with st.expander("Full reading (raw)"):
        st.json(state)


if __name__ == "__main__":
    render()
