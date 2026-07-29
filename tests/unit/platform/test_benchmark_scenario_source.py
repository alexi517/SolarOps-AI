from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.config import ForecastConfig
from solarops.platform.benchmark_scenario_source import TwinBenchmarkScenarioSource
from solarops.simulation.infrastructure.config import SiteConfig


def make_source(**config_overrides) -> TwinBenchmarkScenarioSource:
    config = ForecastConfig(lookback_hours=2.0, **config_overrides)
    site_config = SiteConfig(
        site_id="site-001", update_interval_seconds=config.resolution_minutes * 60
    )
    return TwinBenchmarkScenarioSource(config, site_config)


def test_scenario_names_returns_all_six():
    source = make_source()
    assert len(source.scenario_names()) == 6


def test_run_produces_examples_for_all_three_kinds():
    source = make_source()
    run = source.run("Clear Day")
    assert run.is_primary is True
    for kind in ForecastKind:
        assert len(run.examples[kind]) > 0


def test_run_examples_cover_all_configured_horizons():
    config = ForecastConfig(lookback_hours=2.0)
    site_config = SiteConfig(
        site_id="site-001", update_interval_seconds=config.resolution_minutes * 60
    )
    source = TwinBenchmarkScenarioSource(config, site_config)
    run = source.run("Clear Day")
    horizons_seen = {ex.horizon_minutes for ex in run.examples[ForecastKind.SOLAR_GENERATION]}
    assert horizons_seen == set(config.horizons_minutes)


def test_robustness_scenario_marked_not_primary():
    source = make_source()
    run = source.run("Grid Outage")
    assert run.is_primary is False


def test_battery_soc_examples_carry_current_soc_and_averages():
    source = make_source()
    run = source.run("Clear Day")
    example = run.examples[ForecastKind.BATTERY_SOC][0]
    assert set(example.features.values.keys()) == {
        "current_soc_pct",
        "avg_expected_solar_kw",
        "avg_expected_load_kw",
    }
