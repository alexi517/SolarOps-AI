"""DecisionContext — the inputs the optimisation engine reasons over (Phase 6c brief §3)."""

from __future__ import annotations

from dataclasses import dataclass, field

from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["DecisionContext"]


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """Current state, whatever forecasts are actually registered, and read-only
    operating constraints. Never assume all three ``ForecastKind``s are present —
    brief §6: only Solar is production-registered today (6a).

    ``active_anomaly_count`` (Phase 6d): a plain count, never an Anomaly/
    AnomalyType object — Decision's import contract forbids depending on the
    Anomaly context, so this is deliberately primitive data passed in by the
    composition root (``platform/api_composition.py``), which is the one
    place allowed to see both. Defaults to 0: contexts built without a real
    anomaly signal (``workflow/``, most tests) stay honest about not having
    one rather than fabricating it.
    """

    energy_state: EnergyState
    operating_constraints: OperatingConstraints
    available_forecasts: dict[ForecastKind, Forecast] = field(default_factory=dict)
    active_anomaly_count: int = 0

    def forecast_for(self, kind: ForecastKind) -> Forecast | None:
        return self.available_forecasts.get(kind)
