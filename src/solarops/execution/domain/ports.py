"""Ports the Execution context depends on.

Defined in domain, implemented in infrastructure (Doc 8 §9.1).

``HardwareInterface`` moved here from ``simulation/infrastructure/`` (Phase 5
brief, B.1): Execution owns the port it depends on, so it never needs to
import Simulation to type its own dependency. ``SimulatedHardwareInterface``
(the Twin's conformance to this Protocol) now lives at
``platform/twin_hardware_interface.py`` — the composition root, which may
import both Execution (for the Protocol) and Simulation (for the twin).
"""

from __future__ import annotations

from typing import Protocol

from solarops.execution.domain.approval_request import ApprovalRequest
from solarops.execution.domain.command import Command
from solarops.shared_kernel import (
    ActionType,
    ApprovalRequestId,
    AssetId,
    CommandId,
    ExecutionOutcome,
    SiteId,
)
from solarops.telemetry.domain.energy_state import EnergyState


class HardwareInterface(Protocol):
    def send(self, *, asset_id: AssetId, action: ActionType, params: dict) -> ExecutionOutcome: ...


class CommandRepository(Protocol):
    def get(self, command_id: CommandId) -> Command | None: ...

    def get_by_idempotency_key(self, idempotency_key: str) -> Command | None: ...

    def list_by_site(self, site_id: SiteId) -> list[Command]: ...

    def save(self, command: Command) -> None: ...


class ApprovalRequestRepository(Protocol):
    def get(self, approval_request_id: ApprovalRequestId) -> ApprovalRequest | None: ...

    def get_pending_for_command(self, command_id: CommandId) -> ApprovalRequest | None: ...

    def list_pending_by_site(self, site_id: SiteId) -> list[ApprovalRequest]: ...

    def save(self, request: ApprovalRequest) -> None: ...


class TelemetryReader(Protocol):
    """Reads current EnergyState for verification.

    Deliberately a narrow, Execution-owned Protocol rather than importing
    Telemetry's ``StateStore`` port shape directly (same reasoning as
    ``HardwareInterface``). Phase 3's ``StateManager`` already exposes
    ``get_current(site_id) -> EnergyState | None`` — it satisfies this
    Protocol structurally, no adapter class needed.
    """

    def get_current(self, site_id: SiteId) -> EnergyState | None: ...


class ExecutionMetricsRecorder(Protocol):
    """Phase 7c: the shape ``ExecutionPipeline`` records metrics against.

    Same reasoning as ``HardwareInterface``/``TelemetryReader`` above —
    Execution owns this Protocol so it never needs to import Observability
    to type its own dependency (Observability is forbidden to every context
    by every import-linter contract). The real ``prometheus_client``-backed
    implementation lives at ``platform``'s composition root, which is
    already allowed to import both Execution and Observability.
    """

    def command_issued(self) -> None: ...
    def command_blocked_by_safety(self) -> None: ...
    def command_rejected(self, reason: str) -> None: ...
    def approval_required(self) -> None: ...
    def approval_approved(self) -> None: ...
    def approval_wait_time(self, seconds: float) -> None: ...
    def execution_latency(self, seconds: float) -> None: ...
    def retry_count(self, count: int) -> None: ...
    def command_failed(self) -> None: ...
    def command_timed_out(self, stage: str) -> None: ...
    def verification_failed(self) -> None: ...
    def command_completed(self) -> None: ...
