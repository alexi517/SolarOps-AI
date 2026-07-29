"""Domain enumerations — part of the ubiquitous language.

Most enums are ``StrEnum`` so they serialise to stable, human-readable strings.
``RiskLevel`` is ordered because thresholds compare against it, and it carries
the CESF risk policy (Document 7, section 8) as properties so the rule lives in
exactly one place.
"""

from __future__ import annotations

from enum import Enum, StrEnum
from functools import total_ordering

__all__ = [
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
]


class AssetType(StrEnum):
    """The controllable/observable units at a site."""

    BATTERY = "BATTERY"
    INVERTER = "INVERTER"
    SOLAR_PV = "SOLAR_PV"
    GRID = "GRID"
    BUILDING_LOAD = "BUILDING_LOAD"


class AssetOperatingMode(StrEnum):
    """Coarse operating mode of an asset, used by policy and safety checks."""

    NORMAL = "NORMAL"
    MAINTENANCE = "MAINTENANCE"
    EMERGENCY = "EMERGENCY"
    OFFLINE = "OFFLINE"


class BatteryMode(StrEnum):
    """A battery's current charge/discharge mode.

    Shared vocabulary: both Simulation (the Digital Twin, which produces it)
    and Telemetry (which ingests it) must agree on its meaning, so it lives
    here rather than being duplicated per context (Document 8, section 8).
    """

    IDLE = "IDLE"
    CHARGING = "CHARGING"
    DISCHARGING = "DISCHARGING"


class InverterStatus(StrEnum):
    """An inverter's current health/fault status. Shared vocabulary — see ``BatteryMode``."""

    NORMAL = "NORMAL"
    FAULT_OVERTEMP = "FAULT_OVERTEMP"
    FAULT_OVERVOLTAGE = "FAULT_OVERVOLTAGE"
    FAULT_COMM_LOSS = "FAULT_COMM_LOSS"
    SHUTDOWN = "SHUTDOWN"


class GridStatus(StrEnum):
    """The utility grid connection's current status. Shared vocabulary — see ``BatteryMode``."""

    CONNECTED = "CONNECTED"
    OUTAGE = "OUTAGE"
    UNSTABLE = "UNSTABLE"


class ActionType(StrEnum):
    """The intent a Recommendation expresses and a Command executes.

    These describe *what* to do, never *how* — the how is the Execution
    context's concern.
    """

    CHARGE_BATTERY = "CHARGE_BATTERY"
    DISCHARGE_BATTERY = "DISCHARGE_BATTERY"
    HOLD_BATTERY = "HOLD_BATTERY"
    CURTAIL_SOLAR = "CURTAIL_SOLAR"
    IMPORT_FROM_GRID = "IMPORT_FROM_GRID"
    EXPORT_TO_GRID = "EXPORT_TO_GRID"
    SET_INVERTER_MODE = "SET_INVERTER_MODE"
    SHED_LOAD = "SHED_LOAD"
    RESTORE_LOAD = "RESTORE_LOAD"
    NO_OP = "NO_OP"


class CommandStatus(StrEnum):
    """States in the Command lifecycle (Document 8, section 7).

    Progress states move a command forward through the pipeline; terminal
    states end it — exactly one of them, ``COMPLETED``, is success.
    """

    # --- progress states ---
    CREATED = "CREATED"
    PLANNED = "PLANNED"
    POLICY_VALIDATED = "POLICY_VALIDATED"
    SAFETY_VALIDATED = "SAFETY_VALIDATED"
    RISK_ASSESSED = "RISK_ASSESSED"
    AUTO_APPROVED = "AUTO_APPROVED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    DISPATCHED = "DISPATCHED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    # --- terminal: success ---
    COMPLETED = "COMPLETED"
    # --- terminal: failure ---
    REJECTED_BY_POLICY = "REJECTED_BY_POLICY"
    BLOCKED_BY_SAFETY = "BLOCKED_BY_SAFETY"
    REJECTED_BY_RISK = "REJECTED_BY_RISK"
    REJECTED_BY_OPERATOR = "REJECTED_BY_OPERATOR"
    DISPATCH_FAILED = "DISPATCH_FAILED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    TIMED_OUT = "TIMED_OUT"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_STATES

    @property
    def is_success(self) -> bool:
        return self is CommandStatus.COMPLETED

    @property
    def is_failure(self) -> bool:
        return self in _FAILURE_STATES


_FAILURE_STATES: frozenset[CommandStatus] = frozenset(
    {
        CommandStatus.REJECTED_BY_POLICY,
        CommandStatus.BLOCKED_BY_SAFETY,
        CommandStatus.REJECTED_BY_RISK,
        CommandStatus.REJECTED_BY_OPERATOR,
        CommandStatus.DISPATCH_FAILED,
        CommandStatus.EXECUTION_FAILED,
        CommandStatus.TIMED_OUT,
        CommandStatus.VERIFICATION_FAILED,
        CommandStatus.CANCELLED,
    }
)

_TERMINAL_STATES: frozenset[CommandStatus] = _FAILURE_STATES | {CommandStatus.COMPLETED}


@total_ordering
class RiskLevel(Enum):
    """Risk classification with a strict severity ordering.

    Ordering lets code write ``risk >= RiskLevel.HIGH``. The approval policy
    from CESF section 8 is encoded here so it is defined once:

    * LOW      -> auto-execute
    * MEDIUM   -> auto-execute, but notify the operator
    * HIGH     -> manual approval required
    * CRITICAL -> rejected automatically
    """

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self.value < other.value

    @property
    def requires_manual_approval(self) -> bool:
        return self is RiskLevel.HIGH

    @property
    def is_auto_rejected(self) -> bool:
        return self is RiskLevel.CRITICAL

    @property
    def requires_notification(self) -> bool:
        return self in (RiskLevel.MEDIUM, RiskLevel.HIGH)

    @property
    def is_auto_executable(self) -> bool:
        """True when the command may proceed without waiting for a human."""
        return self in (RiskLevel.LOW, RiskLevel.MEDIUM)


class ExecutionOutcome(StrEnum):
    """Result of handing a command to the Hardware Interface (CESF section 10)."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"

    @property
    def is_success(self) -> bool:
        return self is ExecutionOutcome.SUCCESS


class ApprovalOutcome(StrEnum):
    """A human operator's decision on an approval request (CESF section 9)."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    EXPIRED = "EXPIRED"
