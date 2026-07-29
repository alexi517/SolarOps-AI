"""Domain exception hierarchy.

These represent *business-rule* violations raised during operations — distinct
from ``ValueError``/``TypeError``, which signal that a value object cannot be
constructed at all. Every domain exception descends from ``DomainError`` so
application and API layers can catch the whole family in one place and map it to
a safe response.
"""

from __future__ import annotations

__all__ = [
    "SolarOpsError",
    "DomainError",
    "InvalidStateTransition",
    "PolicyViolation",
    "SafetyViolation",
    "UnsafeStateError",
    "RiskRejected",
    "ApprovalRequired",
    "DuplicateCommandError",
    "AssetUnavailableError",
    "VerificationFailed",
    "FailSafeTriggered",
]


class SolarOpsError(Exception):
    """Root of every SolarOps-specific error."""


class DomainError(SolarOpsError):
    """A domain rule was violated during an operation."""


class InvalidStateTransition(DomainError):
    """An aggregate was asked to move between two incompatible states."""

    def __init__(self, current: object, attempted: object, *, entity: str = "Command") -> None:
        self.current = current
        self.attempted = attempted
        self.entity = entity
        super().__init__(
            f"{entity} cannot transition from {current} to {attempted}"
        )


class PolicyViolation(DomainError):
    """A command violated a configured site policy (CESF section 6)."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Policy violation: {reason}")


class SafetyViolation(DomainError):
    """A command failed a hard safety check (CESF section 7)."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Safety violation: {reason}")


class UnsafeStateError(DomainError):
    """The observed system state is outside safe operating limits."""


class RiskRejected(DomainError):
    """A command was auto-rejected because it was classified CRITICAL."""


class ApprovalRequired(DomainError):
    """Execution was attempted on a command still awaiting human approval."""


class DuplicateCommandError(DomainError):
    """A command with the same idempotency key was already accepted."""

    def __init__(self, idempotency_key: str) -> None:
        self.idempotency_key = idempotency_key
        super().__init__(f"Duplicate command rejected: {idempotency_key}")


class AssetUnavailableError(DomainError):
    """The target asset is offline or otherwise cannot accept commands."""


class VerificationFailed(DomainError):
    """Post-execution telemetry did not confirm the expected state change."""


class FailSafeTriggered(DomainError):
    """A critical pipeline component was unavailable, so execution was refused.

    This is the concrete enforcement of ADR-012 / Document 8 section 9.3:
    when in doubt, do not act.
    """

    def __init__(self, component: str) -> None:
        self.component = component
        super().__init__(
            f"Fail-safe triggered: '{component}' unavailable; execution refused"
        )
