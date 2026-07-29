"""SafetyValidator — the final technical gate (Doc 8 §6.4, CESF §7). Never relaxed.

Reads the current ``EnergyState`` (via Telemetry's ``StateStore`` port — the
same Open Host Service relationship Decision uses, Doc 8 §4) and the intended
action, and evaluates every hard limit in ``SafetyLimits`` relevant to that
action. Fail-safe (ADR-012): anything that prevents evaluation — no current
state, no limits, an internal error — raises ``FailSafeTriggered`` rather than
returning a assessment. That is a structurally different signal from "evaluated
and failed" (``SafetyAssessment(passed=False, ...)``): both must block a
command, but the pipeline (Part B) needs to tell "we checked and it's unsafe"
apart from "we couldn't check at all."
"""

from __future__ import annotations

from solarops.safety.domain.command_intent import CommandIntent
from solarops.safety.domain.ports import SafetyLimitsProvider
from solarops.safety.domain.safety_assessment import SafetyAssessment
from solarops.safety.domain.safety_limits import SafetyLimits
from solarops.shared_kernel import ActionType, AssetOperatingMode, Clock, FailSafeTriggered
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.telemetry.domain.ports import StateStore

_BATTERY_POWER_ACTIONS = frozenset({ActionType.CHARGE_BATTERY, ActionType.DISCHARGE_BATTERY})
_INVERTER_RELEVANT_ACTIONS = _BATTERY_POWER_ACTIONS | frozenset(
    {ActionType.IMPORT_FROM_GRID, ActionType.EXPORT_TO_GRID}
)
_GRID_RELEVANT_ACTIONS = frozenset({ActionType.IMPORT_FROM_GRID, ActionType.EXPORT_TO_GRID})


class SafetyValidator:
    def __init__(
        self,
        limits_provider: SafetyLimitsProvider,
        state_store: StateStore,
        clock: Clock,
    ) -> None:
        self._limits_provider = limits_provider
        self._state_store = state_store
        self._clock = clock

    def validate(self, intent: CommandIntent) -> SafetyAssessment:
        limits = self._limits_provider.get_limits(intent.site_id)
        if limits is None:
            raise FailSafeTriggered("safety limits unavailable")

        state = self._state_store.get(intent.site_id)
        if state is None:
            raise FailSafeTriggered("current EnergyState unavailable")

        try:
            failed_checks = self._evaluate(intent, state, limits)
        except FailSafeTriggered:
            raise
        except Exception as exc:  # never pass on uncertainty
            raise FailSafeTriggered(f"safety validator internal error: {exc}") from exc

        return SafetyAssessment(
            passed=not failed_checks,
            failed_checks=tuple(failed_checks),
            evaluated_at=self._clock.now(),
        )

    def _evaluate(
        self, intent: CommandIntent, state: EnergyState, limits: SafetyLimits
    ) -> list[str]:
        failed: list[str] = []

        # Emergency mode blocks unconditionally, regardless of action.
        if intent.asset_operating_mode is AssetOperatingMode.EMERGENCY:
            failed.append(f"asset {intent.asset_id} is in EMERGENCY operating mode")

        if intent.action is ActionType.SHED_LOAD:
            fraction = intent.params.get("fraction", 0.0)
            if fraction > limits.building_max_shed_fraction:
                failed.append(
                    f"requested shed fraction {fraction:.2f} exceeds the hard safety "
                    f"ceiling {limits.building_max_shed_fraction:.2f} (never relaxed)"
                )

        if (
            intent.action in _BATTERY_POWER_ACTIONS
            and state.battery_temp.value > limits.battery_max_temp.value
        ):
            failed.append(
                f"battery temperature {state.battery_temp.value:.1f}°C exceeds max "
                f"{limits.battery_max_temp.value:.1f}°C"
            )

        if intent.action is ActionType.CHARGE_BATTERY:
            if state.battery_soc.value >= limits.battery_max_soc.value:
                failed.append(
                    f"battery SOC {state.battery_soc.value:.1f}% already at/above max "
                    f"{limits.battery_max_soc.value:.1f}%"
                )
            power_kw = intent.params.get("power_kw")
            if power_kw is not None and power_kw > limits.battery_max_charge_power.value:
                failed.append(
                    f"requested charge power {power_kw:.1f}kW exceeds max "
                    f"{limits.battery_max_charge_power.value:.1f}kW"
                )

        if intent.action is ActionType.DISCHARGE_BATTERY:
            if state.battery_soc.value <= limits.battery_min_soc.value:
                failed.append(
                    f"battery SOC {state.battery_soc.value:.1f}% already at/below min "
                    f"{limits.battery_min_soc.value:.1f}%"
                )
            power_kw = intent.params.get("power_kw")
            if power_kw is not None and power_kw > limits.battery_max_discharge_power.value:
                failed.append(
                    f"requested discharge power {power_kw:.1f}kW exceeds max "
                    f"{limits.battery_max_discharge_power.value:.1f}kW"
                )

        if intent.action in _INVERTER_RELEVANT_ACTIONS:
            if state.inverter_status not in limits.inverter_allowed_statuses:
                failed.append(f"inverter status {state.inverter_status} is not in the allowed set")
            if state.inverter_output.value > limits.inverter_max_power.value:
                failed.append(
                    f"inverter output {state.inverter_output.value:.1f}kW exceeds max "
                    f"{limits.inverter_max_power.value:.1f}kW"
                )

        if intent.action in _GRID_RELEVANT_ACTIONS:
            if state.grid_status != limits.grid_required_status:
                failed.append(
                    f"grid status {state.grid_status} does not meet required "
                    f"{limits.grid_required_status}"
                )
            voltage_delta = abs(state.grid_voltage.value - limits.grid_nominal_voltage.value)
            if voltage_delta > limits.grid_voltage_tolerance.value:
                failed.append(
                    f"grid voltage {state.grid_voltage.value:.1f}V outside tolerance "
                    f"({limits.grid_nominal_voltage.value:.1f}V ± "
                    f"{limits.grid_voltage_tolerance.value:.1f}V)"
                )
            frequency_delta = abs(state.grid_frequency.value - limits.grid_nominal_frequency.value)
            if frequency_delta > limits.grid_frequency_tolerance.value:
                failed.append(
                    f"grid frequency {state.grid_frequency.value:.3f}Hz outside tolerance "
                    f"({limits.grid_nominal_frequency.value:.1f}Hz ± "
                    f"{limits.grid_frequency_tolerance.value:.2f}Hz)"
                )

        return failed
