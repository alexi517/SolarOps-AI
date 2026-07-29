from dataclasses import dataclass

OVERTEMP_THRESHOLD_C = 70.0


@dataclass
class InverterOutput:
    status: str
    temp_c: float
    output_kw: float


class InverterModel:
    """Converts DC input (solar + battery discharge) to AC output for the building/grid.

    Enforces rated capacity as a hard cap ("overload protection") and trips into
    a FAULT_OVERTEMP state if simulated operating temperature exceeds its limit.
    """

    def __init__(self, rated_capacity_kw: float, efficiency: float):
        self.rated_capacity_kw = rated_capacity_kw
        self.efficiency = efficiency
        self._status = "NORMAL"
        self._temp_c = 25.0

    def step(self, dc_input_kw: float, ambient_temp_c: float) -> InverterOutput:
        if self._status in ("SHUTDOWN", "FAULT_COMM_LOSS"):
            output_kw = 0.0
        else:
            output_kw = min(max(0.0, dc_input_kw) * self.efficiency, self.rated_capacity_kw)

        load_fraction = output_kw / self.rated_capacity_kw if self.rated_capacity_kw > 0 else 0.0
        target_temp_c = ambient_temp_c + load_fraction * 25.0
        self._temp_c += (target_temp_c - self._temp_c) * 0.15

        if self._status == "NORMAL" and self._temp_c > OVERTEMP_THRESHOLD_C:
            self._status = "FAULT_OVERTEMP"
            output_kw = 0.0

        return InverterOutput(status=self._status, temp_c=round(self._temp_c, 2), output_kw=round(output_kw, 2))

    def inject_fault(self, fault: str | None) -> None:
        """fault: 'FAULT_OVERTEMP', 'FAULT_OVERVOLTAGE', 'FAULT_COMM_LOSS', 'SHUTDOWN', or None to clear."""
        self._status = fault or "NORMAL"
