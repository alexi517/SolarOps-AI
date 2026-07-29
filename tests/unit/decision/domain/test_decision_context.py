from datetime import UTC, datetime

from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.forecast_metadata import ForecastMetadata
from solarops.forecast.domain.forecast_point import ForecastPoint
from solarops.shared_kernel import ForecastId, Power, SiteId, StateOfCharge, Temperature
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_state() -> EnergyState:
    return EnergyState.from_telemetry(
        make_telemetry(site_id=SITE_ID, timestamp=NOW), any_asset_offline=False
    )


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


def make_forecast() -> Forecast:
    return Forecast(
        forecast_id=ForecastId.generate(),
        site_id=SITE_ID,
        kind=ForecastKind.SOLAR_GENERATION,
        horizon_minutes=60,
        points=(ForecastPoint(timestamp=NOW, value=Power(10.0)),),
        metadata=ForecastMetadata(
            model_name="m", model_version="v1", generated_at=NOW,
            horizon_minutes=60, resolution_minutes=15,
        ),
    )


def test_forecast_for_returns_none_when_absent():
    context = DecisionContext(energy_state=make_state(), operating_constraints=make_constraints())
    assert context.forecast_for(ForecastKind.SOLAR_GENERATION) is None


def test_active_anomaly_count_defaults_to_zero():
    context = DecisionContext(energy_state=make_state(), operating_constraints=make_constraints())
    assert context.active_anomaly_count == 0


def test_active_anomaly_count_can_be_set_explicitly():
    context = DecisionContext(
        energy_state=make_state(), operating_constraints=make_constraints(), active_anomaly_count=3
    )
    assert context.active_anomaly_count == 3


def test_forecast_for_returns_the_registered_forecast():
    forecast = make_forecast()
    context = DecisionContext(
        energy_state=make_state(),
        operating_constraints=make_constraints(),
        available_forecasts={ForecastKind.SOLAR_GENERATION: forecast},
    )
    assert context.forecast_for(ForecastKind.SOLAR_GENERATION) is forecast
    assert context.forecast_for(ForecastKind.BUILDING_LOAD) is None
