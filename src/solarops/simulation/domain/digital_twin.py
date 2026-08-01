"""DigitalTwin — aggregate root (Document 8 §6.6).

Deterministic physics engine for a simulated commercial solar site. Ties the
weather, solar, battery, inverter, grid, and building-load models into a single
``tick()`` that produces a ``SimulationState``, and exposes plain domain verbs
for the actions those models support.

This module knows nothing about ``HardwareInterface`` or ``ActionType`` — the
translation from the Execution context's vocabulary into these domain verbs is
an anticorruption-layer concern that lives in ``infrastructure/hardware_interface.py``
(ADR-015), keeping this aggregate a pure domain object per the hexagonal layering
in §9.1.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from solarops.shared_kernel import (
    BatteryMode,
    Current,
    Frequency,
    GridStatus,
    InverterStatus,
    Power,
    SiteId,
    StateOfCharge,
    Temperature,
    Voltage,
)
from solarops.simulation.domain.models.battery import BatteryModel
from solarops.simulation.domain.models.building_load import BuildingLoadModel
from solarops.simulation.domain.models.grid import GridModel
from solarops.simulation.domain.models.inverter import InverterModel
from solarops.simulation.domain.models.solar import SolarArrayModel
from solarops.simulation.domain.models.weather import WeatherModel
from solarops.simulation.domain.simulation_state import SimulationState
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig

FaultTarget = Literal["solar", "battery", "inverter", "grid", "sensor"]


class DigitalTwin:
    """Orchestrates one simulated commercial solar site.

    Composes the weather, solar, battery, inverter, grid, and building-load
    models into a single tick that produces a ``SimulationState``, and applies
    commands/faults between ticks.
    """

    def __init__(
        self,
        site_config: SiteConfig | None = None,
        simulator_config: SimulatorConfig | None = None,
        start_time: datetime | None = None,
    ):
        self.site_config = site_config or SiteConfig()
        self.simulator_config = simulator_config or SimulatorConfig()
        self._time = start_time or datetime.now(UTC)
        self._dt_seconds = self.site_config.update_interval_seconds

        seed = self.simulator_config.random_seed
        self.weather = WeatherModel(seed=seed)
        self.solar = SolarArrayModel(capacity_kw=self.site_config.solar_capacity_kw)
        self.battery = BatteryModel(
            capacity_kwh=self.site_config.battery_capacity_kwh,
            max_charge_kw=self.site_config.battery_max_charge_kw,
            max_discharge_kw=self.site_config.battery_max_discharge_kw,
            min_soc_pct=self.site_config.battery_min_soc_pct,
            max_soc_pct=self.site_config.battery_max_soc_pct,
            starting_soc_pct=self.site_config.battery_starting_soc_pct,
            max_temp_c=self.site_config.battery_max_temp_c,
            round_trip_efficiency=self.site_config.battery_round_trip_efficiency,
        )
        self.inverter = InverterModel(
            rated_capacity_kw=self.site_config.inverter_rated_capacity_kw,
            efficiency=self.site_config.inverter_efficiency,
        )
        self.grid = GridModel(seed=seed)
        self.building = BuildingLoadModel(
            baseline_kw=self.site_config.building_baseline_load_kw,
            peak_kw=self.site_config.building_peak_load_kw,
            seed=seed,
        )

    # --- domain verbs (replace the old Command/execute_command surface) ---

    def charge_battery(self, power: Power | None = None) -> None:
        self.battery.set_command("CHARGING", power.value if power is not None else None)

    def discharge_battery(self, power: Power | None = None) -> None:
        self.battery.set_command("DISCHARGING", power.value if power is not None else None)

    def hold_battery(self) -> None:
        self.battery.set_command("IDLE")

    def shed_load(self, fraction: float = 0.2) -> None:
        self.building.shed_load(fraction)

    def restore_load(self) -> None:
        self.building.restore_load()

    def inject_fault(self, target: FaultTarget, fault: str | None) -> None:
        if target == "solar":
            self.solar.inject_fault(fault)
        elif target == "battery":
            self.battery.inject_fault(fault)
        elif target == "inverter":
            self.inverter.inject_fault(fault)
        elif target == "grid":
            self.grid.inject_fault(fault)
        elif target == "sensor":
            self.weather.inject_cloud_cover(None)

    def inject_weather_fault(self, cloud_cover_pct: float | None) -> None:
        self.weather.inject_cloud_cover(cloud_cover_pct)

    # --- simulation clock ---

    def tick(self) -> SimulationState:
        weather = self.weather.step(self._time)
        solar_out = self.solar.step(weather.irradiance_w_m2, weather.ambient_temp_c)
        battery_out = self.battery.step(weather.ambient_temp_c, self._dt_seconds)

        battery_discharge_kw = max(0.0, -battery_out.power_kw)
        dc_input_kw = solar_out.power_kw + battery_discharge_kw
        inverter_out = self.inverter.step(dc_input_kw, weather.ambient_temp_c)

        building_load_kw = self.building.step(self._time)

        battery_charge_draw_kw = max(0.0, battery_out.power_kw)
        net_ac_available_kw = inverter_out.output_kw - battery_charge_draw_kw
        # Never negative (never "export"): this site's grid connection is a
        # one-way, non-net-metered utility supply (e.g. NEPA) — it has no
        # mechanism to buy power back. Any solar surplus the battery isn't
        # absorbing is curtailed here rather than fed backward into the grid.
        grid_power_kw = max(0.0, building_load_kw - net_ac_available_kw)
        grid_out = self.grid.step(grid_power_kw)

        fault_codes: list[str] = []
        if inverter_out.status != "NORMAL":
            fault_codes.append(inverter_out.status)
        if grid_out.status != "CONNECTED":
            fault_codes.append(f"GRID_{grid_out.status}")
        if battery_out.temp_c > self.site_config.battery_max_temp_c:
            fault_codes.append("BATTERY_OVERTEMP")

        state = SimulationState(
            timestamp=self._time,
            site_id=SiteId(self.site_config.site_id),
            solar_power=Power(solar_out.power_kw),
            solar_voltage=Voltage(solar_out.voltage_v),
            solar_current=Current(solar_out.current_a),
            irradiance_w_m2=weather.irradiance_w_m2,
            cloud_cover_pct=weather.cloud_cover_pct,
            ambient_temp=Temperature(weather.ambient_temp_c),
            battery_soc=StateOfCharge(battery_out.soc_pct),
            battery_soh_pct=battery_out.soh_pct,
            battery_temp=Temperature(battery_out.temp_c),
            battery_power=Power(battery_out.power_kw),
            battery_mode=BatteryMode(battery_out.mode),
            battery_cycle_count=battery_out.cycle_count,
            inverter_status=InverterStatus(inverter_out.status),
            inverter_temp=Temperature(inverter_out.temp_c),
            inverter_output=Power(inverter_out.output_kw),
            grid_status=GridStatus(grid_out.status),
            grid_voltage=Voltage(grid_out.voltage_v),
            grid_frequency=Frequency(grid_out.frequency_hz),
            grid_power=Power(grid_out.power_kw),
            building_load=Power(building_load_kw),
            fault_codes=fault_codes,
        )

        self._time += timedelta(seconds=self._dt_seconds)
        return state

    def run(self, steps: int) -> list[SimulationState]:
        return [self.tick() for _ in range(steps)]
