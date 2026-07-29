"""Tests for domain enumerations."""

from __future__ import annotations

from solarops.shared_kernel.enums import (
    ActionType,
    ApprovalOutcome,
    AssetType,
    BatteryMode,
    CommandStatus,
    ExecutionOutcome,
    GridStatus,
    InverterStatus,
    RiskLevel,
)


def test_str_enums_serialise_to_stable_strings() -> None:
    assert AssetType.BATTERY == "BATTERY"
    assert ActionType.CHARGE_BATTERY.value == "CHARGE_BATTERY"
    assert str(ExecutionOutcome.SUCCESS) == "SUCCESS"


def test_command_status_success_is_only_completed() -> None:
    assert CommandStatus.COMPLETED.is_success
    assert not CommandStatus.EXECUTED.is_success
    assert not CommandStatus.BLOCKED_BY_SAFETY.is_success


def test_command_status_terminal_classification() -> None:
    assert CommandStatus.COMPLETED.is_terminal
    assert CommandStatus.BLOCKED_BY_SAFETY.is_terminal
    assert CommandStatus.CANCELLED.is_terminal
    # progress states are not terminal
    assert not CommandStatus.CREATED.is_terminal
    assert not CommandStatus.DISPATCHED.is_terminal


def test_command_status_failure_excludes_completed() -> None:
    assert CommandStatus.VERIFICATION_FAILED.is_failure
    assert not CommandStatus.COMPLETED.is_failure
    assert not CommandStatus.VERIFIED.is_failure


def test_every_terminal_state_is_success_xor_failure() -> None:
    for status in CommandStatus:
        if status.is_terminal:
            assert status.is_success != status.is_failure


def test_risk_level_is_ordered_by_severity() -> None:
    assert RiskLevel.LOW < RiskLevel.MEDIUM < RiskLevel.HIGH < RiskLevel.CRITICAL
    assert RiskLevel.HIGH >= RiskLevel.MEDIUM
    assert max(RiskLevel) is RiskLevel.CRITICAL


def test_risk_policy_matches_cesf_section_8() -> None:
    # LOW: auto-execute, no approval, no notification
    assert RiskLevel.LOW.is_auto_executable
    assert not RiskLevel.LOW.requires_manual_approval
    assert not RiskLevel.LOW.requires_notification

    # MEDIUM: auto-execute but notify
    assert RiskLevel.MEDIUM.is_auto_executable
    assert RiskLevel.MEDIUM.requires_notification
    assert not RiskLevel.MEDIUM.requires_manual_approval

    # HIGH: manual approval required
    assert RiskLevel.HIGH.requires_manual_approval
    assert not RiskLevel.HIGH.is_auto_executable

    # CRITICAL: auto-rejected
    assert RiskLevel.CRITICAL.is_auto_rejected
    assert not RiskLevel.CRITICAL.is_auto_executable


def test_execution_outcome_success_flag() -> None:
    assert ExecutionOutcome.SUCCESS.is_success
    assert not ExecutionOutcome.FAILED.is_success
    assert not ExecutionOutcome.TIMED_OUT.is_success


def test_approval_outcomes_present() -> None:
    assert {o.value for o in ApprovalOutcome} == {
        "APPROVED",
        "REJECTED",
        "MODIFIED",
        "EXPIRED",
    }


def test_action_type_includes_load_shedding() -> None:
    # Added for the Simulation context's building-load model (Phase 2) — additive,
    # nothing else depends on ActionType being closed.
    assert ActionType.SHED_LOAD.value == "SHED_LOAD"
    assert ActionType.RESTORE_LOAD.value == "RESTORE_LOAD"


def test_battery_inverter_grid_status_enums_are_shared_vocabulary() -> None:
    # Moved here from per-context duplicates (Phase 3 follow-up) — Simulation
    # and Telemetry both import these same definitions rather than each owning
    # a mirrored copy translated at the platform composition root.
    assert {mode.value for mode in BatteryMode} == {"IDLE", "CHARGING", "DISCHARGING"}
    assert {status.value for status in GridStatus} == {"CONNECTED", "OUTAGE", "UNSTABLE"}
    assert InverterStatus.FAULT_OVERTEMP.value == "FAULT_OVERTEMP"
