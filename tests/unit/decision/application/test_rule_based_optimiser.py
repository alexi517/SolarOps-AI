from datetime import UTC, datetime, timedelta

from solarops.decision.application.rule_based_optimiser import RuleBasedOptimiser
from solarops.decision.domain.confidence import ConfidenceBand
from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.decision.infrastructure.config import RuleEngineConfig
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_metadata import ForecastMetadata
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.shared_kernel import (
    ActionType,
    FixedClock,
    ForecastId,
    GridStatus,
    Power,
    SiteId,
    StateOfCharge,
    Temperature,
)
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
# An hour past NOW, while EnergyState stays timestamped at NOW — forces the
# data-freshness factor low deterministically, independent of whether
# forecasts happen to be registered (see the confidence-weight recalibration
# note in decision/infrastructure/config.py: omitting forecasts alone no
# longer reaches Low, on purpose — the system's permanent solar-only state
# should read as ordinary, not alarming).
STALE_LATER = NOW + timedelta(hours=1)


def make_state(**overrides) -> EnergyState:
    defaults = dict(grid_power=Power(0.0))
    defaults.update(overrides)
    telemetry = make_telemetry(site_id=SITE_ID, timestamp=NOW, **defaults)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def make_constraints(**overrides) -> OperatingConstraints:
    defaults = dict(
        max_battery_soc=StateOfCharge(95.0),
        min_battery_soc=StateOfCharge(10.0),
        battery_max_temp=Temperature(45.0),
        battery_max_charge_power=Power(50.0),
        battery_max_discharge_power=Power(50.0),
        maintenance_mode=False,
        max_shed_fraction=0.3,
    )
    defaults.update(overrides)
    return OperatingConstraints(**defaults)


def make_engine(**config_overrides) -> RuleBasedOptimiser:
    return RuleBasedOptimiser(RuleEngineConfig(**config_overrides), FixedClock(NOW))


def make_context(
    state: EnergyState, constraints: OperatingConstraints, **forecasts
) -> DecisionContext:
    return DecisionContext(
        energy_state=state, operating_constraints=constraints, available_forecasts=forecasts
    )


def make_forecast(kind: ForecastKind, value: float) -> Forecast:
    return Forecast(
        forecast_id=ForecastId.generate(),
        site_id=SITE_ID,
        kind=kind,
        horizon_minutes=60,
        points=(ForecastPoint(timestamp=NOW + timedelta(minutes=30), value=Power(value)),),
        metadata=ForecastMetadata(
            model_name="m", model_version="v1", generated_at=NOW,
            horizon_minutes=60, resolution_minutes=15,
        ),
    )


def test_engine_carries_identity():
    engine = make_engine()
    assert engine.name == "rule-based-optimiser"
    assert engine.version == "v1"


def test_solar_surplus_recommends_charge():
    engine = make_engine()
    state = make_state(
        solar_power=Power(80.0), building_load=Power(40.0), battery_soc=StateOfCharge(50.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.CHARGE_BATTERY
    assert ranked.top.params["power_kw"] == 40.0


def test_solar_deficit_with_grid_connected_tops_up_battery_not_discharge():
    # Grid-priority: a connected, healthy grid means the battery never
    # discharges to help — self-consumption's discharge candidate stays
    # gated off (cost-driven discharge only kicks in once the grid itself is
    # the problem, see the unstable-grid test below). But "resting" isn't
    # the same as "doing nothing": with SOC below the healthy ceiling and
    # the grid available, the battery-health rule still tops it up a little
    # from grid — an unreliable grid means every available minute is a
    # chance to build reserve for the next outage.
    engine = make_engine()
    state = make_state(
        solar_power=Power(10.0), building_load=Power(40.0), battery_soc=StateOfCharge(50.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.CHARGE_BATTERY
    assert ranked.top.params["power_kw"] == 10.0  # reserve_charge_power_kw default


def test_solar_deficit_during_unstable_grid_discharges_via_reliability():
    # Same deficit, but the grid is fluctuating — reliability (priority 2)
    # now applies and outranks self-consumption's own discharge candidate.
    engine = make_engine()
    state = make_state(
        solar_power=Power(10.0),
        building_load=Power(40.0),
        battery_soc=StateOfCharge(50.0),
        grid_status=GridStatus.UNSTABLE,
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.DISCHARGE_BATTERY
    assert ranked.top.params["power_kw"] == 40.0  # reliability covers the full load


def test_grid_outage_with_healthy_soc_discharges_for_reliability():
    engine = make_engine()
    state = make_state(
        grid_status=GridStatus.OUTAGE, building_load=Power(30.0), battery_soc=StateOfCharge(50.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.DISCHARGE_BATTERY
    assert "grid" in ranked.top.reason.lower()


def test_grid_outage_with_low_soc_sheds_load():
    engine = make_engine()
    state = make_state(
        grid_status=GridStatus.OUTAGE, building_load=Power(30.0), battery_soc=StateOfCharge(12.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.SHED_LOAD


def test_battery_below_healthy_band_charges_to_restore_reserve():
    engine = make_engine()
    state = make_state(
        solar_power=Power(0.0), building_load=Power(0.0), battery_soc=StateOfCharge(20.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.CHARGE_BATTERY
    assert "healthy" in ranked.top.reason.lower()


def test_battery_above_healthy_band_with_grid_connected_rests():
    # Grid-priority: sitting above the healthy SOC band isn't urgent enough
    # to draw the battery down while the grid is fine and available.
    engine = make_engine()
    state = make_state(
        solar_power=Power(0.0), building_load=Power(10.0), battery_soc=StateOfCharge(90.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.HOLD_BATTERY


def test_battery_above_healthy_band_discharges_during_grid_outage():
    engine = make_engine()
    state = make_state(
        solar_power=Power(0.0),
        building_load=Power(10.0),
        battery_soc=StateOfCharge(90.0),
        grid_status=GridStatus.OUTAGE,
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.DISCHARGE_BATTERY


def test_overheating_vetoes_charge_and_falls_back_to_hold():
    engine = make_engine()
    state = make_state(
        solar_power=Power(80.0), building_load=Power(40.0),
        battery_soc=StateOfCharge(50.0), battery_temp=Temperature(50.0),
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.HOLD_BATTERY
    assert any("CHARGE_BATTERY" in r and "battery_temp" in r for r in ranked.top.risks)


def test_charging_at_max_soc_is_vetoed_in_favour_of_battery_health_discharge():
    engine = make_engine()
    state = make_state(
        solar_power=Power(80.0), building_load=Power(40.0), battery_soc=StateOfCharge(95.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is not ActionType.CHARGE_BATTERY
    assert any("CHARGE_BATTERY" in r and "policy max" in r for r in ranked.top.risks)


def test_at_min_soc_with_grid_connected_only_charges_never_discharges():
    # Grid-priority: with the grid connected, no rule ever proposes
    # discharging at all (reliability, self-consumption's discharge branch,
    # battery-health's discharge branch, and cost all require a
    # down/unstable grid) — battery health's charge candidate is the only
    # thing on the table, no safety veto needed to rule out a discharge.
    engine = make_engine()
    state = make_state(
        solar_power=Power(0.0), building_load=Power(20.0), battery_soc=StateOfCharge(10.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.CHARGE_BATTERY


def test_cost_discharge_never_fires_while_grid_connected():
    # Grid-priority: importing from a healthy, connected grid is never a
    # reason to *discharge* the battery — cost-based discharge (priority 5)
    # stays disabled while the grid is up. It still charges though (battery
    # health, priority 3, wins here): SOC is below the healthy ceiling and
    # the grid can supply the charging power, so topping up is correct even
    # while separately importing to cover the (zero, in this case) load.
    engine = make_engine()
    state = make_state(
        solar_power=Power(0.0),
        building_load=Power(0.0),
        battery_soc=StateOfCharge(50.0),
        grid_power=Power(20.0),
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.CHARGE_BATTERY
    assert "offsets cost" not in ranked.top.reason.lower()


def test_cost_discharge_fires_once_grid_is_unstable_and_importing():
    engine = make_engine()
    state = make_state(
        solar_power=Power(0.0),
        building_load=Power(0.0),
        battery_soc=StateOfCharge(50.0),
        grid_power=Power(20.0),
        grid_status=GridStatus.UNSTABLE,
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.DISCHARGE_BATTERY
    assert "offsets cost" in ranked.top.reason.lower()


def test_maintenance_mode_vetoes_charging():
    engine = make_engine()
    state = make_state(
        solar_power=Power(80.0), building_load=Power(40.0), battery_soc=StateOfCharge(50.0)
    )
    constraints = make_constraints(maintenance_mode=True)
    ranked = engine.recommend(make_context(state, constraints))
    assert ranked.top.action is ActionType.HOLD_BATTERY
    assert any("maintenance mode" in r for r in ranked.top.risks)


def test_shed_fraction_over_ceiling_is_reduced_not_silently_allowed():
    # SOC exactly at the hard minimum: reliability's own discharge branch
    # wouldn't even propose discharging this low (see the reliability tests
    # above), and self-consumption's discharge candidate — which would
    # otherwise survive on its own — gets vetoed here too (soc <= min), so
    # every candidate is genuinely exhausted and the safety fallback runs.
    engine = make_engine(load_shed_fraction_on_outage=0.2)
    state = make_state(
        grid_status=GridStatus.OUTAGE, solar_power=Power(0.0),
        building_load=Power(30.0), battery_soc=StateOfCharge(10.0),
    )
    constraints = make_constraints(max_shed_fraction=0.1)
    ranked = engine.recommend(make_context(state, constraints))
    assert ranked.top.action is ActionType.SHED_LOAD
    assert ranked.top.params["fraction"] == 0.1
    assert any("shed fraction" in r for r in ranked.top.risks)


def test_missing_load_and_battery_soc_forecasts_are_always_noted():
    engine = make_engine()
    state = make_state(battery_soc=StateOfCharge(50.0))
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert "load forecast unavailable; using current load only" in ranked.top.evidence
    assert "battery SOC forecast unavailable; using current SOC only" in ranked.top.evidence


def test_missing_solar_forecast_is_noted_when_self_consumption_fires():
    # SOC held at 90 (above the healthy ceiling) so battery-health's own
    # charge candidate doesn't also apply here and outrank this one — keeps
    # this test isolated to self-consumption's own evidence/forecast note.
    engine = make_engine()
    state = make_state(
        solar_power=Power(80.0), building_load=Power(40.0), battery_soc=StateOfCharge(90.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert "solar forecast unavailable; using current solar reading only" in ranked.top.evidence


def test_registered_solar_forecast_is_used_when_self_consumption_fires():
    # Same isolation reasoning as above.
    engine = make_engine()
    state = make_state(
        solar_power=Power(80.0), building_load=Power(40.0), battery_soc=StateOfCharge(90.0)
    )
    forecast = make_forecast(ForecastKind.SOLAR_GENERATION, 60.0)
    context = DecisionContext(
        energy_state=state,
        operating_constraints=make_constraints(),
        available_forecasts={ForecastKind.SOLAR_GENERATION: forecast},
    )
    ranked = engine.recommend(context)
    assert any("solar forecast +30min" in e for e in ranked.top.evidence)


def test_never_returns_an_empty_ranking():
    engine = make_engine()
    state = make_state(
        solar_power=Power(20.0), building_load=Power(20.0), battery_soc=StateOfCharge(50.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert len(ranked.recommendations) >= 1


def test_steady_state_with_room_to_charge_tops_up_from_grid():
    # Solar exactly covers load (no self-consumption surplus/deficit either
    # way) — but SOC is below the healthy ceiling and grid is available, so
    # battery-health still opportunistically tops it up. Not truly "steady
    # state" once you count reserve-building as a real, ongoing action.
    engine = make_engine()
    state = make_state(
        solar_power=Power(20.0), building_load=Power(20.0), battery_soc=StateOfCharge(50.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.CHARGE_BATTERY
    assert ranked.top.params["power_kw"] == 10.0


def test_steady_state_with_full_battery_defaults_to_hold():
    # Same balanced solar/load, but SOC is already at the healthy ceiling —
    # now there's genuinely nothing to do.
    engine = make_engine()
    state = make_state(
        solar_power=Power(20.0), building_load=Power(20.0), battery_soc=StateOfCharge(85.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.action is ActionType.HOLD_BATTERY


# --- Phase 6d: confidence attached, and conservative-under-uncertainty (§12) ---


def test_recommendation_carries_a_calculated_confidence_band_and_factors():
    engine = make_engine()
    state = make_state(
        solar_power=Power(80.0), building_load=Power(40.0), battery_soc=StateOfCharge(50.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.confidence_band in (
        ConfidenceBand.HIGH,
        ConfidenceBand.MEDIUM,
        ConfidenceBand.LOW,
    )
    assert len(ranked.top.confidence_factors) >= 1


def test_low_confidence_scales_down_the_top_candidates_own_magnitude():
    # battery_health (priority 3) fires solo. Forcing Low confidence via a
    # stale reading (not via omitted forecasts, which no longer reaches Low
    # on its own — see STALE_LATER's docstring above).
    engine = RuleBasedOptimiser(
        RuleEngineConfig(reserve_charge_power_kw=40.0), FixedClock(STALE_LATER)
    )
    state = make_state(
        solar_power=Power(0.0), building_load=Power(0.0), battery_soc=StateOfCharge(20.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.confidence_band is ConfidenceBand.LOW
    assert ranked.top.action is ActionType.CHARGE_BATTERY
    # Same action as always (never replaced by a different, lower-priority
    # candidate) — just scaled down (default confidence_low_conservative_scale
    # is 0.5).
    assert ranked.top.params["power_kw"] == 20.0
    assert "reduced from 40.0kW to 20.0kW" in " ".join(ranked.top.evidence)


def test_normal_confidence_keeps_the_full_magnitude():
    # Identical scenario, fresh reading and all three forecasts registered
    # — confidence comes out well clear of Low, so no scaling applies.
    engine = RuleBasedOptimiser(RuleEngineConfig(reserve_charge_power_kw=40.0), FixedClock(NOW))
    state = make_state(
        solar_power=Power(0.0), building_load=Power(0.0), battery_soc=StateOfCharge(20.0)
    )
    all_kinds = (
        ForecastKind.SOLAR_GENERATION,
        ForecastKind.BUILDING_LOAD,
        ForecastKind.BATTERY_SOC,
    )
    forecasts = {kind: make_forecast(kind, 10.0) for kind in all_kinds}
    context = DecisionContext(
        energy_state=state, operating_constraints=make_constraints(), available_forecasts=forecasts
    )
    ranked = engine.recommend(context)
    assert ranked.top.confidence_band is not ConfidenceBand.LOW
    assert ranked.top.action is ActionType.CHARGE_BATTERY
    assert ranked.top.params["power_kw"] == 40.0


def test_grid_outage_reliability_is_never_scaled_down_by_low_confidence():
    # Reliability (priority 2) is driven by current telemetry, not
    # forecasts — Low confidence from a stale reading must never shrink
    # "keep the lights on during an outage."
    engine = RuleBasedOptimiser(RuleEngineConfig(), FixedClock(STALE_LATER))
    state = make_state(
        grid_status=GridStatus.OUTAGE, building_load=Power(30.0), battery_soc=StateOfCharge(50.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.confidence_band is ConfidenceBand.LOW
    assert ranked.top.action is ActionType.DISCHARGE_BATTERY
    assert ranked.top.params["power_kw"] == 30.0  # full building_load, unscaled
    assert "grid" in ranked.top.reason.lower()


def test_why_now_states_the_low_confidence_escalation_rule():
    engine = RuleBasedOptimiser(RuleEngineConfig(), FixedClock(STALE_LATER))
    state = make_state(
        solar_power=Power(20.0), building_load=Power(20.0), battery_soc=StateOfCharge(50.0)
    )
    ranked = engine.recommend(make_context(state, make_constraints()))
    assert ranked.top.confidence_band is ConfidenceBand.LOW
    assert "require human approval" in ranked.top.why_now.lower()
