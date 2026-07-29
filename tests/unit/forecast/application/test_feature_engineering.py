from datetime import UTC, datetime

import pytest

from solarops.forecast.application.feature_engineering import build_features
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.shared_kernel import Power, SiteId, StateOfCharge
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_state(**overrides) -> EnergyState:
    telemetry = make_telemetry(site_id=SITE_ID, **overrides)
    return EnergyState.from_telemetry(telemetry, any_asset_offline=False)


def test_solar_features_match_configured_names():
    config = ForecastConfig()
    current = make_state(solar_power=Power(55.0), cloud_cover_pct=20.0)
    features = build_features(ForecastKind.SOLAR_GENERATION, current, [], config)

    assert set(features.values.keys()) == set(config.solar_features)
    assert features.values["solar_power_kw"] == 55.0
    assert features.values["cloud_cover_pct"] == 20.0
    assert features.kind is ForecastKind.SOLAR_GENERATION
    assert features.as_of == current.timestamp


def test_load_features_match_configured_names():
    config = ForecastConfig()
    current = make_state(building_load=Power(30.0))
    features = build_features(ForecastKind.BUILDING_LOAD, current, [], config)

    assert set(features.values.keys()) == set(config.load_features)
    assert features.values["building_load_kw"] == 30.0


def test_trailing_average_computed_from_history():
    config = ForecastConfig()
    history = [
        make_state(timestamp=NOW, solar_power=Power(10.0)),
        make_state(timestamp=NOW, solar_power=Power(20.0)),
    ]
    current = make_state(solar_power=Power(30.0))
    features = build_features(ForecastKind.SOLAR_GENERATION, current, history, config)

    assert features.values["solar_power_trailing_avg_kw"] == 15.0


def test_trailing_average_is_zero_with_no_history():
    config = ForecastConfig()
    current = make_state(solar_power=Power(30.0))
    features = build_features(ForecastKind.SOLAR_GENERATION, current, [], config)

    assert features.values["solar_power_trailing_avg_kw"] == 0.0


def test_peak_observed_considers_history_and_current():
    config = ForecastConfig()
    history = [
        make_state(timestamp=NOW, building_load=Power(20.0)),
        make_state(timestamp=NOW, building_load=Power(40.0)),
    ]
    current = make_state(building_load=Power(55.0))
    features = build_features(ForecastKind.BUILDING_LOAD, current, history, config)

    assert features.values["building_load_peak_observed_kw"] == 55.0


def test_occupancy_proxy_relative_to_peak_observed():
    config = ForecastConfig()
    history = [
        make_state(timestamp=NOW, building_load=Power(20.0)),
        make_state(timestamp=NOW, building_load=Power(40.0)),
    ]
    current = make_state(building_load=Power(20.0))
    features = build_features(ForecastKind.BUILDING_LOAD, current, history, config)

    assert features.values["occupancy_proxy"] == 0.5


def test_rejects_battery_soc_kind():
    config = ForecastConfig()
    current = make_state(battery_soc=StateOfCharge(50.0))
    with pytest.raises(ValueError, match="BatterySocForecaster"):
        build_features(ForecastKind.BATTERY_SOC, current, [], config)
