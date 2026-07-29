"""Domain events the Execution context emits (Doc 8 §6.5).

``CommandBlockedBySafety`` and ``RiskAssessed`` are reused directly from
``solarops.safety.domain.events`` rather than redefined here — they already
exist (Part A), already constructed with ``aggregate_type="Command"``, and
Execution is allowed to import Safety (Phase 5 brief B.5). Redefining them
here would create two classes with the same name for the same concept.
"""

from __future__ import annotations

from dataclasses import dataclass

from solarops.shared_kernel import ActionType, DomainEvent, ExecutionOutcome

__all__ = [
    "CommandCreated",
    "CommandValidated",
    "ApprovalRequested",
    "CommandApproved",
    "CommandRejected",
    "CommandDispatched",
    "CommandAcknowledged",
    "CommandExecuted",
    "CommandFailed",
    "CommandTimedOut",
    "ExecutionVerified",
    "VerificationFailed",
    "CommandCompleted",
    "CommandCancelled",
]


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandCreated(DomainEvent):
    action: ActionType
    idempotency_key: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandValidated(DomainEvent):
    """PLANNED -> POLICY_VALIDATED passed."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalRequested(DomainEvent):
    approval_request_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandApproved(DomainEvent):
    operator_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandRejected(DomainEvent):
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandDispatched(DomainEvent):
    """DISPATCHED."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandAcknowledged(DomainEvent):
    """ACKNOWLEDGED."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandExecuted(DomainEvent):
    outcome: ExecutionOutcome


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandFailed(DomainEvent):
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandTimedOut(DomainEvent):
    stage: str  # "approval" | "execution"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionVerified(DomainEvent):
    """EXECUTED -> VERIFIED."""


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationFailed(DomainEvent):
    """An event, not the shared_kernel exception of the same name — never
    imported together in the same module (see the Phase 5 plan's note)."""

    expected: str
    observed: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandCompleted(DomainEvent):
    """VERIFIED -> COMPLETED. Terminal success."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandCancelled(DomainEvent):
    reason: str
