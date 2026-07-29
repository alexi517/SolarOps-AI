from solarops.platform.benchmark_scenarios import benchmark_scenario_definitions
from solarops.simulation.infrastructure.config import SiteConfig

EXPECTED_NAMES = {
    "Clear Day",
    "Cloud Front",
    "Evening Peak",
    "Grid Outage",
    "Battery Overheating",
    "Sensor Failure",
}


def test_all_six_document_6_scenarios_present():
    definitions = benchmark_scenario_definitions()
    assert {d.name for d in definitions} == EXPECTED_NAMES


def test_exactly_three_are_primary():
    definitions = benchmark_scenario_definitions()
    primary = {d.name for d in definitions if d.is_primary}
    assert primary == {"Clear Day", "Cloud Front", "Evening Peak"}


def test_robustness_scenarios_carry_a_fault():
    definitions = {d.name: d for d in benchmark_scenario_definitions()}
    assert definitions["Grid Outage"].faults == (("grid", "OUTAGE"),)
    assert definitions["Battery Overheating"].faults == (("battery", "OVERHEATING"),)
    assert definitions["Sensor Failure"].faults == (("solar", "OFFLINE"),)


def test_build_twin_applies_faults():
    definitions = {d.name: d for d in benchmark_scenario_definitions()}
    twin = definitions["Grid Outage"].build_twin()
    state = twin.tick()
    assert state.grid_status.value == "OUTAGE"


def test_build_twin_applies_weather_override():
    definitions = {d.name: d for d in benchmark_scenario_definitions()}
    twin = definitions["Cloud Front"].build_twin()
    state = twin.tick()
    assert state.cloud_cover_pct == 70.0


def test_uses_provided_site_config():
    custom = SiteConfig(site_id="custom-site")
    definitions = benchmark_scenario_definitions(custom)
    assert all(d.scenario.site_config.site_id == "custom-site" for d in definitions)
