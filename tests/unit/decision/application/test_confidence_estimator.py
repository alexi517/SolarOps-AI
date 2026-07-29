from datetime import UTC, datetime, timedelta

from solarops.decision.application.confidence_estimator import ConfidenceEstimator
from solarops.decision.domain.confidence import ConfidenceBand
from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.decision.infrastructure.config import RuleEngineConfig
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_metadata import ForecastMetadata
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.shared_kernel import (
    FixedClock,
    ForecastId,
    Power,
    SiteId,
    StateOfCharge,
    Temperature,
)
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_state(*, timestamp: datetime = NOW, **overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, timestamp=timestamp, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def make_constraints() -> OperatingConstraints:
    return OperatingConstraints(
        max_battery_soc=StateOfCharge(95.0),
        min_battery_soc=StateOfCharge(10.0),
        battery_max_temp=Temperature(45.0),
        battery_max_charge_power=Power(50.0),
        battery_max_discharge_power=Power(50.0),
        maintenance_mode=False,
        max_shed_fraction=0.3,
    )


def make_forecast(kind: ForecastKind, *, confidence: float | None = 0.9) -> Forecast:
    return Forecast(
        forecast_id=ForecastId.generate(),
        site_id=SITE_ID,
        kind=kind,
        horizon_minutes=60,
        points=(ForecastPoint(timestamp=NOW, value=Power(10.0)),),
        metadata=ForecastMetadata(
            model_name="m",
            model_version="v1",
            generated_at=NOW,
            horizon_minutes=60,
            resolution_minutes=15,
            confidence=confidence,
        ),
    )


def make_context(**overrides) -> DecisionContext:
    defaults = dict(
        energy_state=make_state(),
        operating_constraints=make_constraints(),
        available_forecasts={},
        active_anomaly_count=0,
    )
    defaults.update(overrides)
    return DecisionContext(**defaults)


def make_estimator(**config_overrides) -> ConfidenceEstimator:
    return ConfidenceEstimator(RuleEngineConfig(**config_overrides), FixedClock(NOW))


def test_all_inputs_fresh_complete_available_yields_high_confidence():
    context = make_context(
        available_forecasts={
            ForecastKind.SOLAR_GENERATION: make_forecast(ForecastKind.SOLAR_GENERATION),
            ForecastKind.BUILDING_LOAD: make_forecast(ForecastKind.BUILDING_LOAD),
            ForecastKind.BATTERY_SOC: make_forecast(ForecastKind.BATTERY_SOC),
        }
    )
    estimate = make_estimator().estimate(context)
    assert estimate.band is ConfidenceBand.HIGH
    assert estimate.score > 0.90


def test_no_forecasts_registered_reduces_confidence_below_high():
    context = make_context()
    estimate = make_estimator().estimate(context)
    assert estimate.band is not ConfidenceBand.HIGH
    assert any("forecast" in f for f in estimate.factors)


def test_stale_state_reduces_confidence_versus_fresh_state():
    fresh = make_estimator().estimate(make_context(energy_state=make_state(timestamp=NOW)))
    stale = make_estimator().estimate(
        make_context(energy_state=make_state(timestamp=NOW - timedelta(minutes=30)))
    )
    assert stale.score < fresh.score
    assert any("stale" in f or "old" in f for f in stale.factors)


def test_very_stale_state_is_low_confidence():
    context = make_context(energy_state=make_state(timestamp=NOW - timedelta(hours=1)))
    estimate = make_estimator().estimate(context)
    assert estimate.band is ConfidenceBand.LOW


def test_active_anomalies_reduce_confidence():
    calm = make_estimator().estimate(make_context(active_anomaly_count=0))
    disturbed = make_estimator().estimate(make_context(active_anomaly_count=2))
    assert disturbed.score < calm.score
    assert any("2 active anomalies" in f for f in disturbed.factors)


def test_missing_forecast_metadata_confidence_uses_the_configured_fallback():
    context = make_context(
        available_forecasts={
            ForecastKind.SOLAR_GENERATION: make_forecast(
                ForecastKind.SOLAR_GENERATION, confidence=None
            ),
        }
    )
    estimate = make_estimator().estimate(context)
    # Registered-but-unrated (0.7 fallback) must score higher than unregistered (0.3).
    baseline = make_estimator().estimate(make_context())
    assert estimate.score > baseline.score


def test_weights_are_configurable():
    context = make_context(active_anomaly_count=5)
    default_estimate = make_estimator().estimate(context)
    lenient_estimate = make_estimator(confidence_weight_anomaly_presence=0.0).estimate(context)
    assert lenient_estimate.score != default_estimate.score
