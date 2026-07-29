"""Approvals screen — the human-in-the-loop workflow made clickable
(brief §2, the key screen). Lists commands paused via GET .../pending; each
gets Approve/Reject/Modify buttons that call the corresponding API POSTs
(with the API key) and then show the resulting command state. Polished as
an operator console (polish pass §3): cards, risk pills, green Approve /
red Reject, toast + inline confirmation."""

from __future__ import annotations

import json

import config
import streamlit as st
import style
from api_client import (
    ApiError,
    ApiUnreachable,
    approve,
    get_command,
    list_pending_approvals,
    modify,
    reject,
)


def _show_api_problem(exc: Exception) -> None:
    if isinstance(exc, ApiUnreachable):
        st.error(f"Cannot reach the API at {config.API_BASE_URL}. Is it running?")
    elif isinstance(exc, ApiError):
        st.error(f"API error {exc.status_code}: {exc.detail}")


def _record_result(action: str, result: dict) -> None:
    # st.rerun() below restarts the script immediately, which would otherwise
    # wipe a st.success()/st.json() shown in the same run before anyone sees
    # it — session_state survives the rerun, so we stash it and render it
    # from the top of render() instead, on the next run. st.toast() is the
    # "just happened" feedback; this is the durable inline confirmation.
    command = result["command"]
    st.session_state.setdefault("last_decisions", []).insert(0, (action, command))
    st.toast(f"{action} — command {command['command_id']} is now {command['status']}.", icon="✅")


def render() -> None:
    style.inject_global_css()
    style.header("Approvals", icon="✅")
    st.caption("Commands paused awaiting a human decision (CESF §8 — RiskLevel.HIGH).")

    for action, command in st.session_state.get("last_decisions", [])[:5]:
        with style.card(f"decision-{command['command_id']}-{action}"):
            kind = style.status_pill_kind(command["status"])
            st.markdown(
                f"{style.pill(action, kind)} command **{command['command_id']}** "
                f"is now {style.pill(command['status'], kind)}",
                unsafe_allow_html=True,
            )
            with st.expander("Detail"):
                st.json(command)

    try:
        pending = list_pending_approvals(config.SITE_ID)
    except (ApiUnreachable, ApiError) as exc:
        _show_api_problem(exc)
        st.stop()

    if not pending:
        with style.card("approvals-empty"):
            st.info("Nothing is currently awaiting approval. Run a decision cycle to produce one.")
        return

    for entry in pending:
        approval_id = entry["approval_request_id"]
        command_id = entry["command_id"]

        with style.card(f"approval-{approval_id}"):
            st.markdown(
                f"### Command {command_id}  "
                f"{style.pill(entry['risk_level'], style.risk_pill_kind(entry['risk_level']))}",
                unsafe_allow_html=True,
            )
            st.caption(f"Requested {entry['requested_at']} — times out {entry['timeout_at']}")

            try:
                command_detail = get_command(command_id)
            except (ApiUnreachable, ApiError) as exc:
                _show_api_problem(exc)
                continue
            st.write(
                f"**Action:** {command_detail['action']}  —  "
                f"**Params:** {command_detail['params']}"
            )

            operator_id = st.text_input(
                "Operator ID", value="OP-dashboard", key=f"operator-{approval_id}"
            )
            reason = st.text_input("Reason", key=f"reason-{approval_id}")

            approve_col, reject_col = st.columns(2)
            with approve_col:
                if st.button(
                    "Approve", key=f"approve-{approval_id}", type="primary", width="stretch"
                ):
                    try:
                        result = approve(approval_id, operator_id=operator_id, reason=reason)
                    except (ApiUnreachable, ApiError) as exc:
                        _show_api_problem(exc)
                    else:
                        _record_result("Approved", result)
                        st.rerun()

            with reject_col, st.container(key=f"danger-reject-{approval_id}"):
                if st.button("Reject", key=f"reject-{approval_id}", width="stretch"):
                    try:
                        result = reject(approval_id, operator_id=operator_id, reason=reason)
                    except (ApiUnreachable, ApiError) as exc:
                        _show_api_problem(exc)
                    else:
                        _record_result("Rejected", result)
                        st.rerun()

            with st.expander("Modify params, then approve"):
                params_text = st.text_area(
                    "Modified params (JSON)",
                    value=json.dumps(command_detail["params"], indent=2),
                    key=f"params-{approval_id}",
                )
                if st.button("Modify & approve", key=f"modify-{approval_id}"):
                    try:
                        modified_params = json.loads(params_text)
                    except ValueError as exc:
                        st.error(f"Params must be valid JSON: {exc}")
                    else:
                        try:
                            result = modify(
                                approval_id,
                                operator_id=operator_id,
                                reason=reason,
                                modified_params=modified_params,
                            )
                        except (ApiUnreachable, ApiError) as exc:
                            _show_api_problem(exc)
                        else:
                            _record_result("Modified", result)
                            st.rerun()


if __name__ == "__main__":
    render()
