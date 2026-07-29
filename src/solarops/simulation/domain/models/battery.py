from dataclasses import dataclass


@dataclass
class BatteryOutput:
    soc_pct: float
    soh_pct: float
    temp_c: float
    power_kw: float  # positive = charging, negative = discharging
    mode: str
    cycle_count: float


class BatteryModel:
    """Simulates a BESS: state of charge, state of health, and thermal behaviour.

    Charge/discharge requests are always clamped to the site's configured SOC
    and power limits -- the model itself is a hard physical constraint, separate
    from (and upstream of) the AI's Safety Validation Agent.
    """

    def __init__(
        self,
        capacity_kwh: float,
        max_charge_kw: float,
        max_discharge_kw: float,
        min_soc_pct: float,
        max_soc_pct: float,
        starting_soc_pct: float,
        max_temp_c: float,
        round_trip_efficiency: float,
    ):
        self.capacity_kwh = capacity_kwh
        self.max_charge_kw = max_charge_kw
        self.max_discharge_kw = max_discharge_kw
        self.min_soc_pct = min_soc_pct
        self.max_soc_pct = max_soc_pct
        self.max_temp_c = max_temp_c
        self.round_trip_efficiency = round_trip_efficiency

        self._soc_pct = starting_soc_pct
        self._soh_pct = 100.0
        self._temp_c = 25.0
        self._cumulative_throughput_kwh = 0.0

        self._mode = "IDLE"
        self._requested_power_kw = 0.0
        self._fault: str | None = None

    def set_command(self, mode: str, power_kw: float | None = None) -> None:
        """mode: 'IDLE', 'CHARGING', or 'DISCHARGING'."""
        self._mode = mode
        if mode == "CHARGING":
            self._requested_power_kw = min(power_kw if power_kw is not None else self.max_charge_kw, self.max_charge_kw)
        elif mode == "DISCHARGING":
            self._requested_power_kw = min(power_kw if power_kw is not None else self.max_discharge_kw, self.max_discharge_kw)
        else:
            self._requested_power_kw = 0.0

    def step(self, ambient_temp_c: float, dt_seconds: float) -> BatteryOutput:
        dt_hours = dt_seconds / 3600.0
        usable_capacity_kwh = self.capacity_kwh * (self._soh_pct / 100.0)

        actual_power_kw = 0.0

        if self._mode == "CHARGING" and usable_capacity_kwh > 0:
            headroom_kwh = usable_capacity_kwh * (self.max_soc_pct - self._soc_pct) / 100.0
            requested_energy_kwh = self._requested_power_kw * dt_hours
            energy_in_kwh = min(requested_energy_kwh, max(0.0, headroom_kwh))

            one_way_efficiency = self.round_trip_efficiency**0.5
            energy_stored_kwh = energy_in_kwh * one_way_efficiency

            self._soc_pct = min(self.max_soc_pct, self._soc_pct + (energy_stored_kwh / usable_capacity_kwh) * 100.0)
            self._cumulative_throughput_kwh += energy_in_kwh
            actual_power_kw = energy_in_kwh / dt_hours if dt_hours > 0 else 0.0

        elif self._mode == "DISCHARGING" and usable_capacity_kwh > 0:
            available_kwh = usable_capacity_kwh * (self._soc_pct - self.min_soc_pct) / 100.0
            requested_energy_kwh = self._requested_power_kw * dt_hours
            energy_out_kwh = min(requested_energy_kwh, max(0.0, available_kwh))

            self._soc_pct = max(self.min_soc_pct, self._soc_pct - (energy_out_kwh / usable_capacity_kwh) * 100.0)
            self._cumulative_throughput_kwh += energy_out_kwh
            actual_power_kw = -(energy_out_kwh / dt_hours) if dt_hours > 0 else 0.0

        rated_power_kw = max(self.max_charge_kw, self.max_discharge_kw, 1.0)
        target_temp_c = ambient_temp_c + (abs(actual_power_kw) / rated_power_kw) * 15.0
        if self._fault == "OVERHEATING":
            target_temp_c = self.max_temp_c + 5.0
        self._temp_c += (target_temp_c - self._temp_c) * 0.1

        equivalent_full_cycles = (
            self._cumulative_throughput_kwh / (2 * self.capacity_kwh) if self.capacity_kwh > 0 else 0.0
        )
        self._soh_pct = max(0.0, 100.0 - equivalent_full_cycles * 0.02)

        reported_mode = self._mode if actual_power_kw != 0 else "IDLE"

        return BatteryOutput(
            soc_pct=round(self._soc_pct, 2),
            soh_pct=round(self._soh_pct, 2),
            temp_c=round(self._temp_c, 2),
            power_kw=round(actual_power_kw, 2),
            mode=reported_mode,
            cycle_count=round(equivalent_full_cycles, 3),
        )

    def inject_fault(self, fault: str | None) -> None:
        """fault: 'OVERHEATING' or None to clear."""
        self._fault = fault
