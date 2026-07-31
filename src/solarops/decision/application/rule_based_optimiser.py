"""RuleBasedOptimiser — v1 optimisation engine, deterministic rules (Phase 6c brief §5).

Reasons only — never issues commands (rule 0). Priority 1 (safety) is a
**filter**, not a generator: it never itself proposes an action, it vetoes
unsafe candidates from priorities 2-5 and supplies the fallback
(``HOLD_BATTERY``, or ``SHED_LOAD`` if even holding is untenable during an
outage) when everything else is vetoed. Priorities 2-5 each independently
propose at most one candidate from current ``EnergyState`` (+ solar forecast,
when registered) and ``OperatingConstraints``. Surviving candidates are
ranked by priority number ascending — that ranking *is*
``RankedRecommendations``, and it doubles as each recommendation's
"alternatives considered" explanation (Document 6 §8): vetoed candidates
become the ``risks`` — a documented reason nothing was fabricated to hide a
gap, everywhere the solar-only forecast constraint (brief §6) applies.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from solarops.decision.application.confidence_estimator import ConfidenceEstimator
from solarops.decision.domain.confidence import ConfidenceBand, ConfidenceEstimate
from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.decision.domain.ranked_recommendations import RankedRecommendations
from solarops.decision.domain.recommendation import Recommendation
from solarops.decision.infrastructure.config import RuleEngineConfig
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.shared_kernel import ActionType, Clock, GridStatus, RecommendationId
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["RuleBasedOptimiser"]

_PRIORITY_LABELS: dict[int, str] = {
    2: "reliable power to loads",
    3: "battery health",
    4: "solar self-consumption",
    5: "minimise imported energy/cost",
}

_LOW_CONFIDENCE_ESCALATION_NOTE = (
    "Confidence is Low — this recommendation will require human approval "
    "regardless of its assessed risk level."
)


@dataclass(frozen=True, slots=True)
class _Candidate:
    action: ActionType
    params: dict
    priority: int
    expected_benefit: str
    why: str
    evidence: tuple[str, ...]


class RuleBasedOptimiser:
    """v1: a deterministic rule engine. Implements ``OptimisationEngine``."""

    name = "rule-based-optimiser"
    version = "v1"

    def __init__(self, config: RuleEngineConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock
        self._confidence_estimator = ConfidenceEstimator(config, clock)

    def recommend(self, context: DecisionContext) -> RankedRecommendations:
        candidates = [
            candidate
            for candidate in (
                self._reliability_candidate(context),
                self._battery_health_candidate(context),
                self._self_consumption_candidate(context),
                self._cost_candidate(context),
            )
            if candidate is not None
        ]

        safe, vetoed = self._apply_safety_filter(candidates, context)
        safe.sort(key=lambda c: c.priority)  # domain priority order — never disturbed

        if not safe:
            safe = [self._safe_default(context, vetoed)]

        # Document 9 §12 — conservative under uncertainty: under Low
        # confidence, take a *smaller version of the same top-priority
        # action* rather than a large one — never substitutes a different,
        # lower-priority candidate. Reordering across candidates was the
        # first design here; dropped because it let a minor priority
        # (cost-minimisation, priority 5) leapfrog a more important one
        # (battery health, priority 3) purely for being numerically
        # smaller, which isn't "conservative," just "small." Priority 2
        # (reliability) is exempt too: it's driven by current telemetry
        # (grid status, current SOC/load), never by forecasts, so
        # forecast-driven uncertainty is no reason to shrink "keep the
        # lights on during an outage."
        confidence = self._confidence_estimator.estimate(context)
        if confidence.band is ConfidenceBand.LOW and safe[0].priority != 2:
            safe[0] = self._make_conservative(safe[0])

        forecast_notes = self._forecast_availability_notes(context)
        recommendations = tuple(
            self._to_recommendation(candidate, context, safe, vetoed, forecast_notes, confidence)
            for candidate in safe
        )
        return RankedRecommendations(recommendations=recommendations)

    def _make_conservative(self, candidate: _Candidate) -> _Candidate:
        """Scales a CHARGE_BATTERY/DISCHARGE_BATTERY candidate's own power
        down by ``confidence_low_conservative_scale`` — same action, smaller
        magnitude. SHED_LOAD is left alone: a *smaller* shed during a grid
        outage means *less* protection for the battery, not more, so
        "smaller = safer" doesn't hold for it. HOLD_BATTERY is already zero
        impact."""
        if candidate.action not in (ActionType.CHARGE_BATTERY, ActionType.DISCHARGE_BATTERY):
            return candidate
        original = candidate.params.get("power_kw", 0.0)
        if original <= 0:
            return candidate
        scaled = round(original * self._config.confidence_low_conservative_scale, 2)
        note = (
            f"confidence is Low — reduced from {original:.1f}kW to {scaled:.1f}kW "
            "as a precaution (Document 9 §12)"
        )
        return replace(
            candidate,
            params={**candidate.params, "power_kw": scaled},
            evidence=(*candidate.evidence, note),
        )

    # --- priority 2: reliable power to loads ---
    def _reliability_candidate(self, context: DecisionContext) -> _Candidate | None:
        state = context.energy_state
        constraints = context.operating_constraints
        if state.grid_status is GridStatus.CONNECTED or state.building_load.value <= 0:
            return None

        margin = state.battery_soc.value - constraints.min_battery_soc.value
        if margin >= self._config.reliability_min_discharge_margin_pct:
            power = min(state.building_load.value, constraints.battery_max_discharge_power.value)
            return _Candidate(
                action=ActionType.DISCHARGE_BATTERY,
                params={"power_kw": round(power, 2)},
                priority=2,
                expected_benefit="Keeps building load served during a grid outage.",
                why="Grid is down and the battery has enough reserve to cover building load.",
                evidence=(
                    f"grid_status={state.grid_status}",
                    f"building_load={state.building_load.value:.1f}kW",
                    f"battery_soc={state.battery_soc.value:.1f}% "
                    f"({margin:.1f}pp above the policy minimum)",
                ),
            )

        fraction = self._config.load_shed_fraction_on_outage
        return _Candidate(
            action=ActionType.SHED_LOAD,
            params={"fraction": fraction},
            priority=2,
            expected_benefit="Protects the remaining reserve during a grid outage.",
            why=(
                "Grid is down and the battery cannot safely cover building load "
                "without breaching its reserve."
            ),
            evidence=(
                f"grid_status={state.grid_status}",
                f"battery_soc={state.battery_soc.value:.1f}%, "
                f"only {margin:.1f}pp above the policy minimum",
            ),
        )

    # --- priority 3: battery health ---
    def _battery_health_candidate(self, context: DecisionContext) -> _Candidate | None:
        state = context.energy_state
        constraints = context.operating_constraints
        soc = state.battery_soc.value

        if soc < self._config.battery_healthy_min_soc_pct:
            surplus = max(state.solar_power.value - state.building_load.value, 0.0)
            if surplus <= 0 and state.grid_status is not GridStatus.CONNECTED:
                # Nothing to charge from: no solar surplus, and the grid — the
                # only other source this rule considers — is down.
                return None
            power = surplus if surplus > 0 else self._config.reserve_charge_power_kw
            power = min(power, constraints.battery_max_charge_power.value)
            source = "solar surplus" if surplus > 0 else "grid (no solar surplus available)"
            return _Candidate(
                action=ActionType.CHARGE_BATTERY,
                params={"power_kw": round(power, 2)},
                priority=3,
                expected_benefit="Restores the battery to its healthy reserve band.",
                why=f"Battery SOC is below the healthy reserve band; topping up from {source}.",
                evidence=(
                    f"battery_soc={soc:.1f}% < healthy min "
                    f"{self._config.battery_healthy_min_soc_pct:.1f}%",
                ),
            )

        if (
            soc > self._config.battery_healthy_max_soc_pct
            and state.building_load.value > 0
            and state.grid_status is not GridStatus.CONNECTED
        ):
            power = min(state.building_load.value, constraints.battery_max_discharge_power.value)
            return _Candidate(
                action=ActionType.DISCHARGE_BATTERY,
                params={"power_kw": round(power, 2)},
                priority=3,
                expected_benefit="Brings the battery back within its healthy operating band.",
                why=(
                    "Battery SOC is above the healthy band; using the surplus "
                    "reserve to serve load."
                ),
                evidence=(
                    f"battery_soc={soc:.1f}% > healthy max "
                    f"{self._config.battery_healthy_max_soc_pct:.1f}%",
                ),
            )
        return None

    # --- priority 4: maximise solar self-consumption ---
    def _self_consumption_candidate(self, context: DecisionContext) -> _Candidate | None:
        state = context.energy_state
        constraints = context.operating_constraints
        net = state.solar_power.value - state.building_load.value
        forecast_note = self._solar_forecast_note(context)
        extra_evidence = () if forecast_note is None else (forecast_note,)

        if net > self._config.self_consumption_min_surplus_kw:
            power = min(net, constraints.battery_max_charge_power.value)
            return _Candidate(
                action=ActionType.CHARGE_BATTERY,
                params={"power_kw": round(power, 2)},
                priority=4,
                expected_benefit="Maximises use of on-site solar instead of exporting it.",
                why=(
                    "Solar generation exceeds building load; storing the surplus "
                    "beats exporting it."
                ),
                evidence=(
                    f"solar_power={state.solar_power.value:.1f}kW, "
                    f"building_load={state.building_load.value:.1f}kW, surplus={net:.1f}kW",
                    *extra_evidence,
                ),
            )

        grid_needs_help = state.grid_status is not GridStatus.CONNECTED
        if net < -self._config.self_consumption_min_surplus_kw and grid_needs_help:
            deficit = -net
            power = min(deficit, constraints.battery_max_discharge_power.value)
            return _Candidate(
                action=ActionType.DISCHARGE_BATTERY,
                params={"power_kw": round(power, 2)},
                priority=4,
                expected_benefit="Uses stored solar to cover the deficit instead of importing.",
                why="Building load exceeds solar generation; using stored solar beats importing.",
                evidence=(
                    f"solar_power={state.solar_power.value:.1f}kW, "
                    f"building_load={state.building_load.value:.1f}kW, deficit={deficit:.1f}kW",
                    *extra_evidence,
                ),
            )
        return None

    # --- priority 5: minimise imported energy and cost ---
    def _cost_candidate(self, context: DecisionContext) -> _Candidate | None:
        state = context.energy_state
        constraints = context.operating_constraints
        if state.grid_status is GridStatus.CONNECTED:
            # Grid-priority policy: with a healthy, connected grid, the battery
            # rests entirely rather than being cycled to shave import cost.
            # Cost-based discharge only makes sense once the grid itself is
            # already the reason for concern (down or unstable) — priority 2
            # already covers that case.
            return None
        if state.grid_power.value <= 0:
            return None  # not importing

        margin = state.battery_soc.value - constraints.min_battery_soc.value
        if margin < self._config.cost_discharge_margin_pct:
            return None

        power = min(
            state.grid_power.value,
            self._config.cost_discharge_power_kw,
            constraints.battery_max_discharge_power.value,
        )
        return _Candidate(
            action=ActionType.DISCHARGE_BATTERY,
            params={"power_kw": round(power, 2)},
            priority=5,
            expected_benefit="Reduces imported energy cost using spare battery margin.",
            why=(
                "Site is importing from the grid and the battery has spare margin; "
                "discharging a modest amount offsets cost."
            ),
            evidence=(
                f"grid_power={state.grid_power.value:.1f}kW (importing)",
                f"battery_soc={state.battery_soc.value:.1f}% "
                f"({margin:.1f}pp above the policy minimum)",
            ),
        )

    # --- priority 1: safety — filters, never generates ---
    def _apply_safety_filter(
        self, candidates: list[_Candidate], context: DecisionContext
    ) -> tuple[list[_Candidate], list[tuple[_Candidate, str]]]:
        safe: list[_Candidate] = []
        vetoed: list[tuple[_Candidate, str]] = []
        constraints = context.operating_constraints
        state = context.energy_state

        for candidate in candidates:
            reason = self._veto_reason(candidate, constraints, state)
            if reason is None:
                safe.append(candidate)
            else:
                vetoed.append((candidate, reason))
        return safe, vetoed

    @staticmethod
    def _veto_reason(
        candidate: _Candidate, constraints: OperatingConstraints, state: EnergyState
    ) -> str | None:
        if candidate.action is ActionType.CHARGE_BATTERY:
            if state.battery_soc.value >= constraints.max_battery_soc.value:
                return (
                    f"battery_soc={state.battery_soc.value:.1f}% already at/over "
                    f"policy max {constraints.max_battery_soc.value:.1f}%"
                )
            if state.battery_temp.value >= constraints.battery_max_temp.value:
                return (
                    f"battery_temp={state.battery_temp.value:.1f}C at/over max "
                    f"{constraints.battery_max_temp.value:.1f}C"
                )
            if constraints.maintenance_mode:
                return "site is in maintenance mode; charging is not permitted"

        if candidate.action is ActionType.DISCHARGE_BATTERY:
            if state.battery_soc.value <= constraints.min_battery_soc.value:
                return (
                    f"battery_soc={state.battery_soc.value:.1f}% already at/under "
                    f"policy min {constraints.min_battery_soc.value:.1f}%"
                )
            if state.battery_temp.value >= constraints.battery_max_temp.value:
                return (
                    f"battery_temp={state.battery_temp.value:.1f}C at/over max "
                    f"{constraints.battery_max_temp.value:.1f}C"
                )

        if candidate.action is ActionType.SHED_LOAD:
            fraction = candidate.params.get("fraction", 0.0)
            if fraction > constraints.max_shed_fraction:
                return (
                    f"requested shed fraction {fraction:.2f} exceeds policy ceiling "
                    f"{constraints.max_shed_fraction:.2f}"
                )

        return None

    def _safe_default(
        self, context: DecisionContext, vetoed: list[tuple[_Candidate, str]]
    ) -> _Candidate:
        state = context.energy_state
        constraints = context.operating_constraints
        grid_down = state.grid_status is not GridStatus.CONNECTED
        evidence = tuple(f"vetoed: {c.action} — {reason}" for c, reason in vetoed)

        if grid_down and constraints.max_shed_fraction > 0:
            fraction = min(self._config.load_shed_fraction_on_outage, constraints.max_shed_fraction)
            return _Candidate(
                action=ActionType.SHED_LOAD,
                params={"fraction": round(fraction, 3)},
                priority=1,
                expected_benefit="Protects remaining power when no other action is currently safe.",
                why=(
                    "No other action is currently safe, and the grid is down; "
                    "shedding load protects what power remains."
                ),
                evidence=evidence,
            )

        if vetoed:
            return _Candidate(
                action=ActionType.HOLD_BATTERY,
                params={},
                priority=1,
                expected_benefit="Avoids making an unsafe move.",
                why="No other action is currently safe; holding avoids making an unsafe move.",
                evidence=evidence,
            )

        return _Candidate(
            action=ActionType.HOLD_BATTERY,
            params={},
            priority=5,
            expected_benefit=(
                "Avoids unnecessary battery cycling when nothing is currently beneficial."
            ),
            why="No beneficial action identified this cycle; holding avoids unnecessary cycling.",
            evidence=(),
        )

    # --- explanation assembly (Document 6 §8, Document 9 §8/§9) ---
    def _to_recommendation(
        self,
        candidate: _Candidate,
        context: DecisionContext,
        safe: list[_Candidate],
        vetoed: list[tuple[_Candidate, str]],
        forecast_notes: tuple[str, ...],
        confidence: ConfidenceEstimate,
    ) -> Recommendation:
        others = [c for c in safe if c is not candidate]
        alternatives = tuple(
            f"{c.action.value} (serves: {_PRIORITY_LABELS.get(c.priority, 'safety')}) "
            f"— not chosen, lower priority"
            for c in others
        ) + tuple(
            f"{c.action.value} — considered but vetoed: {reason}" for c, reason in vetoed
        )
        risks = tuple(f"vetoed alternative {c.action.value}: {reason}" for c, reason in vetoed)

        why_now = (
            f"Evaluated against the current reading at "
            f"{context.energy_state.timestamp.isoformat()}."
        )
        if confidence.band is ConfidenceBand.LOW:
            why_now += f" {_LOW_CONFIDENCE_ESCALATION_NOTE}"

        return Recommendation(
            recommendation_id=RecommendationId.generate(),
            site_id=context.energy_state.site_id,
            action=candidate.action,
            params=candidate.params,
            confidence=confidence.score,
            expected_benefit=candidate.expected_benefit,
            reason=candidate.why,
            generated_at=self._clock.now(),
            why_now=why_now,
            evidence=candidate.evidence + forecast_notes,
            alternatives=alternatives,
            risks=risks,
            confidence_band=confidence.band,
            confidence_factors=confidence.factors,
        )

    def _forecast_availability_notes(self, context: DecisionContext) -> tuple[str, ...]:
        notes: list[str] = []
        if context.forecast_for(ForecastKind.BUILDING_LOAD) is None:
            notes.append("load forecast unavailable; using current load only")
        if context.forecast_for(ForecastKind.BATTERY_SOC) is None:
            notes.append("battery SOC forecast unavailable; using current SOC only")
        return tuple(notes)

    def _solar_forecast_note(self, context: DecisionContext) -> str | None:
        forecast = context.forecast_for(ForecastKind.SOLAR_GENERATION)
        if forecast is None:
            return "solar forecast unavailable; using current solar reading only"
        point = forecast.at_horizon(30)
        return f"solar forecast +30min: {point.value}"
