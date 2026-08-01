from datetime import datetime, timedelta

from solarops.shared_kernel import GridStatus
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig


def make_twin(**site_overrides):
    site_config = SiteConfig(update_interval_seconds=300, **site_overrides)
    simulator_config = SimulatorConfig(random_seed=7)
    return DigitalTwin(
        site_config=site_config,
        simulator_config=simulator_config,
        start_time=datetime(2026, 7, 27, 0, 0),
    )


def test_tick_advances_simulation_clock():
    twin = make_twin()
    first = twin.tick()
    second = twin.tick()
    assert second.timestamp - first.timestamp == timedelta(seconds=300)


def test_full_day_run_produces_expected_number_of_states():
    twin = make_twin()
    states = twin.run(steps=288)  # 24h at 5-minute resolution
    assert len(states) == 288
    assert all(0.0 <= s.battery_soc.value <= 100.0 for s in states)
    assert all(s.solar_power.value >= 0.0 for s in states)


def test_solar_generation_peaks_during_daylight_hours():
    twin = make_twin()
    states = twin.run(steps=288)
    midday_state = next(s for s in states if s.timestamp.hour == 12)
    midnight_state = next(s for s in states if s.timestamp.hour == 0)
    assert midday_state.solar_power.value > midnight_state.solar_power.value


def test_grid_outage_fault_appears_in_fault_codes():
    twin = make_twin()
    twin.inject_fault("grid", "OUTAGE")
    state = twin.tick()
    assert "GRID_OUTAGE" in state.fault_codes
    assert state.grid_status is GridStatus.OUTAGE


def test_grid_power_never_goes_negative_even_with_large_solar_surplus():
    # This site's grid connection is a one-way, non-net-metered utility
    # supply (e.g. NEPA) — it never buys power back. A tiny load against a
    # large solar array guarantees a surplus at midday with nothing to
    # absorb it (battery isn't commanded to charge), which used to produce
    # a negative ("export") grid_power_kw before this was clamped.
    twin = make_twin(
        solar_capacity_kw=500.0,
        building_baseline_load_kw=0.5,
        building_peak_load_kw=1.0,
    )
    states = twin.run(steps=288)  # 24h at 5-minute resolution
    assert all(s.grid_power.value >= 0.0 for s in states)
