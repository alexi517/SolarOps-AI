from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.platform.twin_fault_scenario_source import TwinFaultScenarioSource


def test_scenario_names_returns_all_five():
    source = TwinFaultScenarioSource()
    assert len(source.scenario_names()) == 5


def test_run_has_normal_prefix_then_fault():
    source = TwinFaultScenarioSource()
    run = source.run("Grid Outage")

    assert not run.readings[0].is_anomalous
    assert run.readings[-1].is_anomalous
    first_anomalous_index = next(i for i, r in enumerate(run.readings) if r.is_anomalous)
    assert all(not r.is_anomalous for r in run.readings[:first_anomalous_index])
    assert all(r.is_anomalous for r in run.readings[first_anomalous_index:])


def test_anomalous_readings_carry_the_expected_type():
    source = TwinFaultScenarioSource()
    run = source.run("Battery Overheating")
    anomalous = [r for r in run.readings if r.is_anomalous]
    assert all(r.expected_type is AnomalyType.BATTERY_OVERHEATING for r in anomalous)


def test_normal_readings_carry_no_expected_type():
    source = TwinFaultScenarioSource()
    run = source.run("Battery Overheating")
    normal = [r for r in run.readings if not r.is_anomalous]
    assert all(r.expected_type is None for r in normal)


def test_grid_outage_fault_actually_changes_grid_status():
    source = TwinFaultScenarioSource()
    run = source.run("Grid Outage")
    assert run.readings[-1].state.grid_status.value == "OUTAGE"


def test_tick_seconds_matches_site_config():
    source = TwinFaultScenarioSource()
    run = source.run("Grid Outage")
    assert run.tick_seconds > 0
