"""Commands screen — GET /sites/{id}/commands, and GET /commands/{id}/audit
for a selected command (brief §2, polish pass §3)."""

from __future__ import annotations

import config
import streamlit as st
import style
from api_client import ApiError, ApiUnreachable, get_command, get_command_audit, list_commands


def render() -> None:
    style.inject_global_css()
    style.header("Commands", icon="📋")

    try:
        commands = list_commands(config.SITE_ID)
    except ApiUnreachable:
        st.error(f"Cannot reach the API at {config.API_BASE_URL}. Is it running?")
        st.stop()
    except ApiError as exc:
        st.error(f"API error {exc.status_code}: {exc.detail}")
        st.stop()

    if not commands:
        with style.card("commands-empty"):
            st.info("No commands yet. Run a decision cycle from the Recommendations screen.")
        return

    with style.card("commands-table"):
        st.dataframe(
            [
                {
                    "command_id": c["command_id"],
                    "action": c["action"],
                    "status": c["status"],
                    "created_at": c["created_at"],
                }
                for c in commands
            ],
            width="stretch",
        )

        command_ids = [c["command_id"] for c in commands]
        selected_id = st.selectbox("Select a command for detail + audit trail", command_ids)

    if not selected_id:
        return

    try:
        detail = get_command(selected_id)
        audit_trail = get_command_audit(selected_id)
    except ApiUnreachable:
        st.error(f"Cannot reach the API at {config.API_BASE_URL}. Is it running?")
        st.stop()
    except ApiError as exc:
        st.error(f"API error {exc.status_code}: {exc.detail}")
        st.stop()

    with style.card(f"command-detail-{selected_id}"):
        st.subheader("Command detail")
        st.markdown(
            style.pill(detail["status"], style.status_pill_kind(detail["status"])),
            unsafe_allow_html=True,
        )
        st.json(detail)

    with style.card(f"command-audit-{selected_id}"):
        st.subheader("Audit trail")
        if not audit_trail:
            st.info("No audit entries yet.")
        else:
            st.dataframe(
                [
                    {
                        "event_type": e["event_type"],
                        "occurred_at": e["occurred_at"],
                        "correlation_id": e["correlation_id"],
                    }
                    for e in audit_trail
                ],
                width="stretch",
            )


if __name__ == "__main__":
    render()
