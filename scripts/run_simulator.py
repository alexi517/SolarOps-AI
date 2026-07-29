"""Manual smoke test: run the Digital Twin for a simulated day and print key moments."""

from datetime import datetime

from solarops.platform.twin_hardware_interface import SimulatedHardwareInterface
from solarops.shared_kernel import ActionType, AssetId, ScenarioId
from solarops.simulation.application.scenario_runner import ScenarioRunner
from solarops.simulation.domain.scenario import Scenario
from solarops.simulation.domain.simulation_state import SimulationState
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig

BATTERY_ASSET_ID = AssetId("ASSET-battery-1")


def print_snapshot(label: str, state: SimulationState) -> None:
    print(f"\n[{label}] {state.timestamp.strftime('%H:%M')}")
    print(f"  solar={state.solar_power.value:6.1f}kW  battery_soc={state.battery_soc.value:5.1f}%  "
          f"battery_mode={state.battery_mode:<11} load={state.building_load.value:6.1f}kW  "
          f"grid={state.grid_status:<10} grid_power={state.grid_power.value:6.1f}kW  "
          f"faults={state.fault_codes}")


def main() -> None:
    scenario = Scenario(
        scenario_id=ScenarioId.generate(),
        name="day-long-smoke-test",
        # 5-minute resolution for a readable demo
        site_config=SiteConfig(update_interval_seconds=300),
        simulator_config=SimulatorConfig(random_seed=42),
        start_time=datetime(2026, 7, 25, 0, 0),
    )
    runner = ScenarioRunner(scenario)
    hardware = SimulatedHardwareInterface(runner.twin)

    print("=== SolarOps AI Digital Twin: simulated day, 5-minute resolution ===")

    states = []
    for step in range(288):  # 24h
        if step == 96:  # 08:00 — start charging from morning solar
            outcome = hardware.send(
                asset_id=BATTERY_ASSET_ID,
                action=ActionType.CHARGE_BATTERY,
                params={"power_kw": 30.0},
            )
            print(f"\n>>> COMMAND @ step {step}: CHARGE_BATTERY -> {outcome}")
        if step == 144:  # 12:00 — simulate sudden cloud cover
            runner.twin.inject_weather_fault(85.0)
            print(f"\n>>> FAULT INJECTED @ step {step}: cloud cover -> 85%")
        if step == 156:  # 13:00 — clear the cloud fault
            runner.twin.inject_weather_fault(None)
            print(f"\n>>> FAULT CLEARED @ step {step}: cloud cover override released")
        if step == 216:  # 18:00 — evening peak, start discharging to cover load
            outcome = hardware.send(
                asset_id=BATTERY_ASSET_ID,
                action=ActionType.DISCHARGE_BATTERY,
                params={"power_kw": 25.0},
            )
            print(f"\n>>> COMMAND @ step {step}: DISCHARGE_BATTERY -> {outcome}")

        state = runner.twin.tick()
        states.append(state)

        if step % 24 == 0:  # print every 2 simulated hours
            print_snapshot(f"step {step}", state)

    print("\n=== Day summary ===")
    print(f"Peak solar output: {max(s.solar_power.value for s in states):.1f} kW")
    print(f"Min battery SOC:   {min(s.battery_soc.value for s in states):.1f}%")
    print(f"Max battery SOC:   {max(s.battery_soc.value for s in states):.1f}%")
    print(f"Final battery SOH: {states[-1].battery_soh_pct:.3f}%")
    grid_import_kwh = sum(max(0.0, s.grid_power.value) for s in states) * 300 / 3600
    grid_export_kwh = sum(max(0.0, -s.grid_power.value) for s in states) * 300 / 3600
    print(f"Total grid import: {grid_import_kwh:.1f} kWh")
    print(f"Total grid export: {grid_export_kwh:.1f} kWh")


if __name__ == "__main__":
    main()
