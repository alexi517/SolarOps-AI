from solarops.forecast.infrastructure.config import ForecastConfig


def test_default_horizons_match_brief():
    config = ForecastConfig()
    assert config.horizons_minutes == (15, 30, 60, 360)
    assert config.max_horizon_minutes == 360


def test_named_horizons_maps_labels_to_minutes():
    config = ForecastConfig()
    assert config.named_horizons == {"15min": 15, "30min": 30, "1h": 60, "6h": 360}


def test_targets_are_configurable_not_hardcoded():
    config = ForecastConfig(solar_mae_target_pct=5.0)
    assert config.solar_mae_target_pct == 5.0
    assert ForecastConfig().solar_mae_target_pct == 8.0
