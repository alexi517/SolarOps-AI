"""Builds the LangGraph orchestration graph (Doc 8 §10).

START -> decision -> END. Future phases add nodes upstream (telemetry refresh,
forecast, anomaly detection) and downstream (safety validation, approval) of
"decision" — this is still the minimal graph; Phase 6c only replaces the
brain behind the "decision" node (the Phase 4 stub -> a real
``OptimisationEngine``), the graph shape is unchanged.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from solarops.decision.domain.operating_constraints import OperatingConstraints
from solarops.decision.domain.ports import OptimisationEngine
from solarops.workflow.graph_state import GraphState
from solarops.workflow.nodes import make_decision_node

__all__ = ["build_graph"]


def build_graph(engine: OptimisationEngine, operating_constraints: OperatingConstraints):
    builder = StateGraph(GraphState)
    builder.add_node("decision", make_decision_node(engine, operating_constraints))
    builder.add_edge(START, "decision")
    builder.add_edge("decision", END)
    return builder.compile()
