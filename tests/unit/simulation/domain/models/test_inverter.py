from solarops.simulation.domain.models.inverter import InverterModel


def test_output_scales_with_dc_input_and_efficiency():
    inverter = InverterModel(rated_capacity_kw=120.0, efficiency=0.97)
    output = inverter.step(dc_input_kw=50.0, ambient_temp_c=25.0)
    assert output.output_kw == round(50.0 * 0.97, 2)
    assert output.status == "NORMAL"


def test_output_capped_at_rated_capacity():
    inverter = InverterModel(rated_capacity_kw=120.0, efficiency=0.97)
    output = inverter.step(dc_input_kw=1000.0, ambient_temp_c=25.0)
    assert output.output_kw <= 120.0


def test_shutdown_fault_forces_zero_output():
    inverter = InverterModel(rated_capacity_kw=120.0, efficiency=0.97)
    inverter.inject_fault("SHUTDOWN")
    output = inverter.step(dc_input_kw=50.0, ambient_temp_c=25.0)
    assert output.output_kw == 0.0
    assert output.status == "SHUTDOWN"


def test_clearing_fault_restores_normal_operation():
    inverter = InverterModel(rated_capacity_kw=120.0, efficiency=0.97)
    inverter.inject_fault("SHUTDOWN")
    inverter.step(dc_input_kw=50.0, ambient_temp_c=25.0)
    inverter.inject_fault(None)
    output = inverter.step(dc_input_kw=50.0, ambient_temp_c=25.0)
    assert output.status == "NORMAL"
    assert output.output_kw > 0.0


def test_sustained_high_load_trips_overtemp():
    inverter = InverterModel(rated_capacity_kw=120.0, efficiency=0.97)
    output = None
    for _ in range(50):
        output = inverter.step(dc_input_kw=120.0, ambient_temp_c=50.0)
    assert output.status == "FAULT_OVERTEMP"
