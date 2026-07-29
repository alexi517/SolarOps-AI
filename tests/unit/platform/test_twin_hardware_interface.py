from datetime import datetime

from solarops.platform.twin_hardware_interface import SimulatedHardwareInterface
from solarops.shared_kernel import ActionType, AssetId, BatteryMode, ExecutionOutcome
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig

BATTERY_ASSET_ID = AssetId("ASSET-battery-1")


def make_twin(**site_overrides):
    site_config = SiteConfig(update_interval_seconds=300, **site_overrides)
    simulator_config = SimulatorConfig(random_seed=7)
    return DigitalTwin(
        site_config=site_config,
        simulator_config=simulator_config,
        start_time=datetime(2026, 7, 27, 0, 0),
    )


def test_battery_charge_command_is_reflected_in_next_tick():
    twin = make_twin()
    hardware = SimulatedHardwareInterface(twin)
    outcome = hardware.send(
        asset_id=BATTERY_ASSET_ID,
        action=ActionType.CHARGE_BATTERY,
        params={"power_kw": 20.0},
    )
    assert outcome is ExecutionOutcome.SUCCESS
    state = twin.tick()
    assert state.battery_mode is BatteryMode.CHARGING
    assert state.battery_power.value > 0


def test_unhandled_action_is_blocked():
    twin = make_twin()
    hardware = SimulatedHardwareInterface(twin)
    outcome = hardware.send(asset_id=BATTERY_ASSET_ID, action=ActionType.NO_OP, params={})
    assert outcome is ExecutionOutcome.BLOCKED
