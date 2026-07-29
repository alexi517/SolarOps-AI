from solarops.simulation.domain.models.battery import BatteryModel


def make_battery(**overrides):
    defaults = dict(
        capacity_kwh=200.0,
        max_charge_kw=50.0,
        max_discharge_kw=50.0,
        min_soc_pct=10.0,
        max_soc_pct=95.0,
        starting_soc_pct=50.0,
        max_temp_c=45.0,
        round_trip_efficiency=0.92,
    )
    defaults.update(overrides)
    return BatteryModel(**defaults)


def test_charging_increases_soc():
    battery = make_battery()
    battery.set_command("CHARGING")
    output = battery.step(ambient_temp_c=25.0, dt_seconds=300)
    assert output.soc_pct > 50.0
    assert output.power_kw > 0
    assert output.mode == "CHARGING"


def test_discharging_decreases_soc():
    battery = make_battery()
    battery.set_command("DISCHARGING")
    output = battery.step(ambient_temp_c=25.0, dt_seconds=300)
    assert output.soc_pct < 50.0
    assert output.power_kw < 0
    assert output.mode == "DISCHARGING"


def test_soc_never_exceeds_max_soc_even_with_long_charging():
    battery = make_battery(starting_soc_pct=94.0)
    battery.set_command("CHARGING")
    for _ in range(200):
        output = battery.step(ambient_temp_c=25.0, dt_seconds=300)
    assert output.soc_pct <= 95.0


def test_soc_never_drops_below_min_soc_even_with_long_discharging():
    battery = make_battery(starting_soc_pct=11.0)
    battery.set_command("DISCHARGING")
    for _ in range(200):
        output = battery.step(ambient_temp_c=25.0, dt_seconds=300)
    assert output.soc_pct >= 10.0


def test_idle_mode_leaves_soc_unchanged():
    battery = make_battery()
    output = battery.step(ambient_temp_c=25.0, dt_seconds=300)
    assert output.soc_pct == 50.0
    assert output.power_kw == 0.0
    assert output.mode == "IDLE"


def test_overheating_fault_raises_temperature_over_time():
    battery = make_battery()
    battery.inject_fault("OVERHEATING")
    output = None
    for _ in range(20):
        output = battery.step(ambient_temp_c=25.0, dt_seconds=300)
    assert output.temp_c > battery.max_temp_c


def test_cycle_count_accumulates_with_throughput():
    battery = make_battery()
    battery.set_command("CHARGING")
    battery.step(ambient_temp_c=25.0, dt_seconds=300)
    battery.set_command("DISCHARGING")
    output = battery.step(ambient_temp_c=25.0, dt_seconds=300)
    assert output.cycle_count > 0.0
