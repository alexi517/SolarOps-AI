"""Graph nodes — thin wrappers wiring a context's application service into the graph."""

from __future__ import annotations

from collections.abc import Callable

from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.decision.domain.ports import OptimisationEngine
from solarops.workflow.graph_state import GraphState

__all__ = ["make_decision_node"]


def make_decision_node(
    engine: OptimisationEngine, operating_constraints: OperatingConstraints
) -> Callable[[GraphState], dict]:
    """Builds a ``DecisionContext`` from the graph state and asks the real engine
    for its top recommendation — the Phase 4 stub's plumbing, a real brain behind
    it (Phase 6c)."""

    def decision_node(state: GraphState) -> dict:
        context = DecisionContext(
            energy_state=state["energy_state"],
            operating_constraints=operating_constraints,
            available_forecasts=state.get("available_forecasts", {}),
        )
        ranked = engine.recommend(context)
        return {"recommendation": ranked.top}

    return decision_node
