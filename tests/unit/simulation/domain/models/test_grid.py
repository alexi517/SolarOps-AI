from solarops.simulation.domain.models.grid import GridModel


def test_connected_grid_reports_near_nominal_voltage_and_frequency():
    grid = GridModel(seed=1)
    output = grid.step(requested_power_kw=10.0)
    assert output.status == "CONNECTED"
    assert 400.0 < output.voltage_v < 430.0
    assert 49.5 < output.frequency_hz < 50.5
    assert output.power_kw == 10.0


def test_outage_zeroes_voltage_frequency_and_power():
    grid = GridModel(seed=1)
    grid.inject_fault("OUTAGE")
    output = grid.step(requested_power_kw=10.0)
    assert output.status == "OUTAGE"
    assert output.voltage_v == 0.0
    assert output.frequency_hz == 0.0
    assert output.power_kw == 0.0


def test_unstable_widens_voltage_and_frequency_variance():
    grid = GridModel(seed=1)
    grid.inject_fault("UNSTABLE")
    readings = [grid.step(requested_power_kw=0.0) for _ in range(30)]
    voltages = [r.voltage_v for r in readings]
    assert max(voltages) - min(voltages) > 10.0


def test_clearing_fault_restores_connected():
    grid = GridModel(seed=1)
    grid.inject_fault("OUTAGE")
    grid.inject_fault(None)
    output = grid.step(requested_power_kw=5.0)
    assert output.status == "CONNECTED"
