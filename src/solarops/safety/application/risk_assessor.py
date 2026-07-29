"""RiskAssessor — classifies an action into a RiskLevel (Doc 8 §6.4, CESF §8).

The brief calls this "the one component with genuine design latitude" — CESF
lists risk *factors*, not a formula. This is a v1, transparent, table-driven
heuristic implementing the brief's suggested mapping verbatim, one rule per
factor, checked top-down: the first tier whose conditions match wins.

``forecast_uncertainty`` defaults to ``None`` because the Forecast context
doesn't exist until Phase 6 (brief's own note). Judgment call, documented here:
"unknown -> treat conservatively" is implemented as *not* letting a missing
value count as evidence of safety (it never lowers the tier) — but it also
doesn't unconditionally force every v1 command to HIGH, which would make
MEDIUM/LOW unreachable before Phase 6 exists. It only actively pushes toward
HIGH when a real uncertainty value is supplied and is itself high.
"""

from __future__ import annotations

from solarops.safety.domain.command_intent import CommandIntent
from solarops.safety.domain.policy import Policy
from solarops.safety.domain.risk_assessment import RiskAssessment
from solarops.safety.domain.safety_assessment import SafetyAssessment
from solarops.safety.domain.safety_limits import SafetyLimits
from solarops.shared_kernel import (
    ActionType,
    AssetOperatingMode,
    Clock,
    GridStatus,
    InverterStatus,
    RiskLevel,
)
from solarops.telemetry.domain.energy_state import EnergyState

_FAULT_STATUSES = frozenset(
    {
        InverterStatus.FAULT_OVERTEMP,
        InverterStatus.FAULT_OVERVOLTAGE,
        InverterStatus.FAULT_COMM_LOSS,
        InverterStatus.SHUTDOWN,
    }
)
_GRID_RELEVANT_ACTIONS = frozenset({ActionType.IMPORT_FROM_GRID, ActionType.EXPORT_TO_GRID})

# Tunable thresholds — see module docstring: this is the component with
# explicit design latitude.
_CRITICAL_MARGIN_FRACTION = 0.05  # within 5% of a hard limit, even though it passed
_MEDIUM_MARGIN_FRACTION = 0.25  # below this, but not CRITICAL -> HIGH's neighbour, MEDIUM
_LARGE_POWER_SWING_FRACTION = 0.50  # > 50% of rated power
_HIGH_FORECAST_UNCERTAINTY = 0.30  # only meaningful once Phase 6 supplies a real value


class RiskAssessor:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def assess(
        self,
        intent: CommandIntent,
        state: EnergyState,
        policy: Policy,
        limits: SafetyLimits,
        safety_assessment: SafetyAssessment,
        forecast_uncertainty: float | None = None,
    ) -> RiskAssessment:
        factors: list[str] = []
        level = self._classify(
            intent, state, policy, limits, safety_assessment, forecast_uncertainty, factors
        )
        return RiskAssessment(level=level, factors=tuple(factors), assessed_at=self._clock.now())

    def _classify(
        self,
        intent: CommandIntent,
        state: EnergyState,
        policy: Policy,
        limits: SafetyLimits,
        safety_assessment: SafetyAssessment,
        forecast_uncertainty: float | None,
        factors: list[str],
    ) -> RiskLevel:
        # --- CRITICAL ---
        if not safety_assessment.passed:
            factors.append("safety assessment did not pass")
            return RiskLevel.CRITICAL
        if state.inverter_status in _FAULT_STATUSES:
            factors.append(f"asset fault/offline: inverter status is {state.inverter_status}")
            return RiskLevel.CRITICAL
        if intent.asset_operating_mode is AssetOperatingMode.EMERGENCY:
            factors.append(f"asset {intent.asset_id} is in EMERGENCY operating mode")
            return RiskLevel.CRITICAL
        if state.any_asset_offline:
            factors.append("EnergyState reports an asset offline")
            return RiskLevel.CRITICAL
        margin = self._battery_margin_fraction(intent, state, limits)
        if margin is not None and margin < _CRITICAL_MARGIN_FRACTION:
            factors.append(f"action sits within {margin:.1%} of a hard limit, despite passing")
            return RiskLevel.CRITICAL
        grid_down = state.grid_status is not GridStatus.CONNECTED
        if intent.action in _GRID_RELEVANT_ACTIONS and grid_down:
            factors.append(f"grid-dependent action during grid {state.grid_status}")
            return RiskLevel.CRITICAL

        # --- HIGH ---
        high_factors: list[str] = []
        if (
            intent.action is ActionType.DISCHARGE_BATTERY
            and state.battery_soc.value <= policy.min_battery_soc.value
        ):
            high_factors.append("battery reserve would drop to/below the policy floor")
        power_kw = intent.params.get("power_kw")
        rated = self._rated_power(intent.action, limits)
        if power_kw is not None and rated is not None and rated > 0:
            swing_fraction = power_kw / rated
            if swing_fraction > _LARGE_POWER_SWING_FRACTION:
                high_factors.append(f"large power swing: {swing_fraction:.0%} of rated power")
        if forecast_uncertainty is not None and forecast_uncertainty > _HIGH_FORECAST_UNCERTAINTY:
            high_factors.append(f"high forecast uncertainty ({forecast_uncertainty:.0%})")
        if policy.maintenance_mode:
            high_factors.append("asset is in MAINTENANCE mode")
        if high_factors:
            factors.extend(high_factors)
            return RiskLevel.HIGH

        # --- MEDIUM vs LOW ---
        if margin is not None and margin < _MEDIUM_MARGIN_FRACTION:
            factors.append(f"moderate safety margin ({margin:.0%})")
            return RiskLevel.MEDIUM

        factors.append("routine action, comfortable margin, normal operating state")
        return RiskLevel.LOW

    @staticmethod
    def _rated_power(action: ActionType, limits: SafetyLimits):
        if action is ActionType.CHARGE_BATTERY:
            return limits.battery_max_charge_power.value
        if action is ActionType.DISCHARGE_BATTERY:
            return limits.battery_max_discharge_power.value
        return None

    @staticmethod
    def _battery_margin_fraction(
        intent: CommandIntent, state: EnergyState, limits: SafetyLimits
    ) -> float | None:
        """Fraction of the battery's usable SOC range remaining before the
        relevant hard limit, for the two actions where that's meaningful."""
        soc_range = limits.battery_max_soc.value - limits.battery_min_soc.value
        if soc_range <= 0:
            return None
        if intent.action is ActionType.CHARGE_BATTERY:
            return (limits.battery_max_soc.value - state.battery_soc.value) / soc_range
        if intent.action is ActionType.DISCHARGE_BATTERY:
            return (state.battery_soc.value - limits.battery_min_soc.value) / soc_range
        return None
