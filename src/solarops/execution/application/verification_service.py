"""VerificationService — confirms the expected physical change via telemetry.

Doc 8 §6.5, CESF §12, ADR-011.

Specific, single-reading-checkable rules exist for the three battery actions
(the brief's own example: "battery reports charging"). Every other action gets
a documented, weaker generic check (no active fault codes) rather than a
fabricated specific one — a scoped seam, not a silent gap: building a real
per-action verification rule for every ``ActionType`` needs baseline/before
readings this v1 doesn't capture (e.g. "load actually dropped" needs a
pre-command reading to compare against).
"""

from __future__ import annotations

from solarops.execution.domain.command import Command
from solarops.execution.domain.ports import TelemetryReader
from solarops.execution.domain.verification_result import VerificationResult
from solarops.shared_kernel import ActionType, BatteryMode, Clock

_EXPECTED_BATTERY_MODE: dict[ActionType, BatteryMode] = {
    ActionType.CHARGE_BATTERY: BatteryMode.CHARGING,
    ActionType.DISCHARGE_BATTERY: BatteryMode.DISCHARGING,
    ActionType.HOLD_BATTERY: BatteryMode.IDLE,
}

__all__ = ["VerificationService"]


class VerificationService:
    def __init__(self, telemetry_reader: TelemetryReader, clock: Clock) -> None:
        self._telemetry_reader = telemetry_reader
        self._clock = clock

    def verify(self, command: Command) -> VerificationResult:
        state = self._telemetry_reader.get_current(command.site_id)
        now = self._clock.now()

        if state is None:
            return VerificationResult(
                passed=False,
                expected="a current EnergyState reading",
                observed="no telemetry available",
                verified_at=now,
            )

        expected_mode = _EXPECTED_BATTERY_MODE.get(command.action)
        if expected_mode is not None:
            return VerificationResult(
                passed=state.battery_mode is expected_mode,
                expected=f"battery_mode == {expected_mode}",
                observed=f"battery_mode == {state.battery_mode}",
                verified_at=now,
            )

        return VerificationResult(
            passed=not state.fault_codes,
            expected="no active fault codes",
            observed=f"fault_codes == {state.fault_codes}",
            verified_at=now,
        )
