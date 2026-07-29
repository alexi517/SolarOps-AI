"""SolarOps AI — Shared Kernel.

The minimal set of value objects, enums, events, exceptions, and the clock port
that every bounded context shares (Document 8, section 8). It depends on nothing
outside the standard library, and nothing else in ``solarops`` may leak *into*
it — a rule enforced by the import-linter contract in ``pyproject.toml``.

Import from here rather than the submodules, e.g.::

    from solarops.shared_kernel import CommandId, Power, RiskLevel, Clock
"""

from __future__ import annotations

from .clock import Clock, FixedClock, SystemClock
from .enums import (
    ActionType,
    ApprovalOutcome,
    AssetOperatingMode,
    AssetType,
    BatteryMode,
    CommandStatus,
    ExecutionOutcome,
    GridStatus,
    InverterStatus,
    RiskLevel,
)
from .events import DomainEvent, EventEnvelope
from .exceptions import (
    ApprovalRequired,
    AssetUnavailableError,
    DomainError,
    DuplicateCommandError,
    FailSafeTriggered,
    InvalidStateTransition,
    PolicyViolation,
    RiskRejected,
    SafetyViolation,
    SolarOpsError,
    UnsafeStateError,
    VerificationFailed,
)
from .ids import (
    AlertId,
    AnomalyId,
    ApprovalRequestId,
    AssetId,
    AuditEntryId,
    CommandId,
    EventId,
    ForecastId,
    Identifier,
    IncidentId,
    OperatorId,
    PolicyId,
    RecommendationId,
    ScenarioId,
    SiteId,
)
from .units import (
    Current,
    Energy,
    Frequency,
    Power,
    Quantity,
    StateOfCharge,
    Temperature,
    Voltage,
)

__all__ = [
    # clock
    "Clock",
    "SystemClock",
    "FixedClock",
    # enums
    "AssetType",
    "AssetOperatingMode",
    "BatteryMode",
    "InverterStatus",
    "GridStatus",
    "ActionType",
    "CommandStatus",
    "RiskLevel",
    "ExecutionOutcome",
    "ApprovalOutcome",
    # events
    "DomainEvent",
    "EventEnvelope",
    # exceptions
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
    # ids
    "Identifier",
    "SiteId",
    "AssetId",
    "CommandId",
    "RecommendationId",
    "PolicyId",
    "ApprovalRequestId",
    "OperatorId",
    "IncidentId",
    "ForecastId",
    "ScenarioId",
    "AnomalyId",
    "AlertId",
    "AuditEntryId",
    "EventId",
    # units
    "Quantity",
    "Power",
    "Energy",
    "StateOfCharge",
    "Temperature",
    "Voltage",
    "Current",
    "Frequency",
]
