from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.platform.anomaly_fault_scenarios import anomaly_fault_scenario_definitions
from solarops.simulation.infrastructure.config import SiteConfig

EXPECTED_NAMES = {
    "Battery Overheating",
    "Grid Outage",
    "Sensor Failure",
    "Inverter Fault",
    "Communication Loss",
}


def test_all_five_document_6_fault_scenarios_present():
    definitions = anomaly_fault_scenario_definitions()
    assert {d.name for d in definitions} == EXPECTED_NAMES


def test_each_scenario_maps_to_its_expected_anomaly_type():
    definitions = {d.name: d for d in anomaly_fault_scenario_definitions()}
    assert definitions["Battery Overheating"].expected_type is AnomalyType.BATTERY_OVERHEATING
    assert definitions["Grid Outage"].expected_type is AnomalyType.GRID_INSTABILITY
    assert definitions["Sensor Failure"].expected_type is AnomalyType.SENSOR_FAILURE
    assert definitions["Inverter Fault"].expected_type is AnomalyType.INVERTER_FAULT
    assert definitions["Communication Loss"].expected_type is AnomalyType.COMMUNICATION_LOSS


def test_communication_loss_and_inverter_fault_use_distinct_fault_codes():
    definitions = {d.name: d for d in anomaly_fault_scenario_definitions()}
    assert definitions["Communication Loss"].fault_code == "FAULT_COMM_LOSS"
    assert definitions["Inverter Fault"].fault_code == "FAULT_OVERTEMP"
    assert definitions["Communication Loss"].fault_target == "inverter"
    assert definitions["Inverter Fault"].fault_target == "inverter"


def test_uses_provided_site_config():
    custom = SiteConfig(site_id="custom-site")
    definitions = anomaly_fault_scenario_definitions(custom)
    assert all(d.scenario.site_config.site_id == "custom-site" for d in definitions)
