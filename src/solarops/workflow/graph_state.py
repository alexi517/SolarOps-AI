"""GraphState — the shared state LangGraph threads through the graph's nodes (Doc 8 §10).

Carries the ``EnergyState`` in and the ``Recommendation`` out. Deliberately
left open (``total=False``) rather than pre-declaring fields for contexts that
don't exist yet — Anomaly and Safety will each add their own key here once
wired into the graph, not before.

``available_forecasts`` (Phase 6c): forward-compatible key for whichever
``Forecast``s a future forecast node populates — today nothing does, so the
decision node degrades gracefully and reasons from current state only,
exactly as Phase 6a's registered-solar-only reality requires (brief §6).
"""

from __future__ import annotations

from typing import TypedDict

from solarops.decision.domain.recommendation import Recommendation
from solarops.forecast.domain.forecast import Forecast
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["GraphState"]


class GraphState(TypedDict, total=False):
    energy_state: EnergyState
    available_forecasts: dict[ForecastKind, Forecast]
    recommendation: Recommendation
