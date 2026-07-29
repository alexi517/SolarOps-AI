"""Tests for the domain exception hierarchy."""

from __future__ import annotations

from solarops.shared_kernel.enums import CommandStatus
from solarops.shared_kernel.exceptions import (
    DomainError,
    DuplicateCommandError,
    FailSafeTriggered,
    InvalidStateTransition,
    PolicyViolation,
    SafetyViolation,
    SolarOpsError,
)


def test_all_domain_errors_share_a_common_root() -> None:
    for exc in (
        InvalidStateTransition(CommandStatus.CREATED, CommandStatus.COMPLETED),
        PolicyViolation("max SOC exceeded"),
        SafetyViolation("battery temperature too high"),
        DuplicateCommandError("key-1"),
        FailSafeTriggered("SafetyValidator"),
    ):
        assert isinstance(exc, DomainError)
        assert isinstance(exc, SolarOpsError)


def test_invalid_state_transition_message_and_attrs() -> None:
    exc = InvalidStateTransition(CommandStatus.CREATED, CommandStatus.EXECUTED)
    assert exc.current is CommandStatus.CREATED
    assert exc.attempted is CommandStatus.EXECUTED
    assert "cannot transition" in str(exc)
    assert "CREATED" in str(exc) and "EXECUTED" in str(exc)


def test_policy_and_safety_violations_expose_reason() -> None:
    assert PolicyViolation("no charging in maintenance mode").reason == (
        "no charging in maintenance mode"
    )
    assert SafetyViolation("current exceeds limit").reason == "current exceeds limit"


def test_duplicate_command_error_carries_key() -> None:
    exc = DuplicateCommandError("idem-42")
    assert exc.idempotency_key == "idem-42"
    assert "idem-42" in str(exc)


def test_fail_safe_names_the_component() -> None:
    exc = FailSafeTriggered("SafetyValidator")
    assert exc.component == "SafetyValidator"
    assert "execution refused" in str(exc)
