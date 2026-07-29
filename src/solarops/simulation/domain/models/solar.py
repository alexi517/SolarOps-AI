from dataclasses import dataclass

DC_BUS_VOLTAGE_V = 600.0
STANDARD_TEST_IRRADIANCE_W_M2 = 1000.0
REFERENCE_TEMP_C = 25.0
TEMP_DERATE_PER_DEGREE = 0.004


@dataclass
class SolarOutput:
    power_kw: float
    voltage_v: float
    current_a: float


class SolarArrayModel:
    """Simulates a PV array's DC power output given irradiance and ambient temperature."""

    def __init__(self, capacity_kw: float):
        self.capacity_kw = capacity_kw
        self._degradation_factor = 1.0
        self._offline = False

    def step(self, irradiance_w_m2: float, ambient_temp_c: float) -> SolarOutput:
        if self._offline:
            return SolarOutput(power_kw=0.0, voltage_v=0.0, current_a=0.0)

        irradiance_factor = max(0.0, irradiance_w_m2 / STANDARD_TEST_IRRADIANCE_W_M2)
        temp_derate = 1.0 - max(0.0, ambient_temp_c - REFERENCE_TEMP_C) * TEMP_DERATE_PER_DEGREE

        power_kw = self.capacity_kw * irradiance_factor * temp_derate * self._degradation_factor
        power_kw = max(0.0, power_kw)

        voltage_v = DC_BUS_VOLTAGE_V if power_kw > 0 else 0.0
        current_a = (power_kw * 1000.0 / voltage_v) if voltage_v > 0 else 0.0

        return SolarOutput(power_kw=round(power_kw, 2), voltage_v=voltage_v, current_a=round(current_a, 2))

    def inject_fault(self, fault: str | None) -> None:
        """fault: 'OFFLINE', 'PANEL_DEGRADATION', or None to clear."""
        if fault == "OFFLINE":
            self._offline = True
        elif fault == "PANEL_DEGRADATION":
            self._offline = False
            self._degradation_factor = 0.6
        elif fault is None:
            self._offline = False
            self._degradation_factor = 1.0
