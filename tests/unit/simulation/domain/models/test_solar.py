from solarops.simulation.domain.models.solar import SolarArrayModel


def test_zero_irradiance_gives_zero_power():
    array = SolarArrayModel(capacity_kw=100.0)
    output = array.step(irradiance_w_m2=0.0, ambient_temp_c=25.0)
    assert output.power_kw == 0.0
    assert output.voltage_v == 0.0


def test_full_irradiance_at_reference_temp_approaches_capacity():
    array = SolarArrayModel(capacity_kw=100.0)
    output = array.step(irradiance_w_m2=1000.0, ambient_temp_c=25.0)
    assert output.power_kw == 100.0


def test_high_temperature_derates_output():
    array = SolarArrayModel(capacity_kw=100.0)
    output = array.step(irradiance_w_m2=1000.0, ambient_temp_c=45.0)
    assert output.power_kw < 100.0


def test_offline_fault_forces_zero_output():
    array = SolarArrayModel(capacity_kw=100.0)
    array.inject_fault("OFFLINE")
    output = array.step(irradiance_w_m2=1000.0, ambient_temp_c=25.0)
    assert output.power_kw == 0.0

    array.inject_fault(None)
    output_after = array.step(irradiance_w_m2=1000.0, ambient_temp_c=25.0)
    assert output_after.power_kw == 100.0


def test_panel_degradation_reduces_output():
    array = SolarArrayModel(capacity_kw=100.0)
    array.inject_fault("PANEL_DEGRADATION")
    output = array.step(irradiance_w_m2=1000.0, ambient_temp_c=25.0)
    assert output.power_kw == 60.0
