import random
from dataclasses import dataclass

NOMINAL_VOLTAGE_V = 415.0
NOMINAL_FREQUENCY_HZ = 50.0


@dataclass
class GridOutput:
    status: str
    voltage_v: float
    frequency_hz: float
    power_kw: float


class GridModel:
    """Simulates the utility grid connection: availability, voltage, and frequency."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self._status = "CONNECTED"

    def step(self, requested_power_kw: float) -> GridOutput:
        """requested_power_kw: positive = import from grid, negative = export to grid."""
        if self._status == "OUTAGE":
            return GridOutput(status=self._status, voltage_v=0.0, frequency_hz=0.0, power_kw=0.0)

        if self._status == "UNSTABLE":
            voltage_v = NOMINAL_VOLTAGE_V + self._rng.uniform(-30.0, 30.0)
            frequency_hz = NOMINAL_FREQUENCY_HZ + self._rng.uniform(-0.5, 0.5)
        else:
            voltage_v = NOMINAL_VOLTAGE_V + self._rng.uniform(-2.0, 2.0)
            frequency_hz = NOMINAL_FREQUENCY_HZ + self._rng.uniform(-0.05, 0.05)

        return GridOutput(
            status=self._status,
            voltage_v=round(voltage_v, 1),
            frequency_hz=round(frequency_hz, 3),
            power_kw=round(requested_power_kw, 2),
        )

    def inject_fault(self, fault: str | None) -> None:
        """fault: 'OUTAGE', 'UNSTABLE', or None to clear."""
        self._status = fault or "CONNECTED"
