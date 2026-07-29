"""SimulatedHardwareInterface — the Digital Twin's conformance to HardwareInterface (ADR-015).

Composition root (Doc 8 §10, §6.8): imports both ``solarops.execution`` (for
the ``HardwareInterface`` Protocol it implements) and ``solarops.simulation``
(for the ``DigitalTwin`` it wraps). This is the only path through which the
AI-facing side may reach the Twin — nothing calls the Twin's domain methods
directly. Moved here from ``simulation/infrastructure/`` (Phase 5 brief, B.1):
Execution owns the port, so it must never need to import Simulation to type
its own dependency, which means the concrete adapter can't live inside
Simulation either.
"""

from __future__ import annotations

from solarops.shared_kernel import ActionType, AssetId, ExecutionOutcome, Power
from solarops.simulation.domain.digital_twin import DigitalTwin

__all__ = ["SimulatedHardwareInterface"]


class SimulatedHardwareInterface:
    """The Digital Twin's implementation of ``HardwareInterface``."""

    def __init__(self, twin: DigitalTwin) -> None:
        self._twin = twin

    def send(self, *, asset_id: AssetId, action: ActionType, params: dict) -> ExecutionOutcome:
        try:
            match action:
                case ActionType.CHARGE_BATTERY:
                    power_kw = params.get("power_kw")
                    self._twin.charge_battery(Power(power_kw) if power_kw is not None else None)
                case ActionType.DISCHARGE_BATTERY:
                    power_kw = params.get("power_kw")
                    self._twin.discharge_battery(Power(power_kw) if power_kw is not None else None)
                case ActionType.HOLD_BATTERY:
                    self._twin.hold_battery()
                case ActionType.SHED_LOAD:
                    self._twin.shed_load(params.get("fraction", 0.2))
                case ActionType.RESTORE_LOAD:
                    self._twin.restore_load()
                case _:
                    return ExecutionOutcome.BLOCKED
        except Exception:
            return ExecutionOutcome.FAILED
        return ExecutionOutcome.SUCCESS
