"""Ports the Decision context depends on.

Defined in domain, implemented in infrastructure/application (Doc 8 §9.1).
``OptimisationEngine`` is the roadmap-ready interface (brief §1/§3): v1
(`RuleBasedOptimiser`) implements it now; v2/v3/v4 are unimplemented shells
behind the same interface (``application/engine_shells.py``) so nothing
downstream changes when they eventually land.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.domain.ranked_recommendations import RankedRecommendations

__all__ = ["OptimisationEngine", "BenchmarkContextSource"]


@runtime_checkable
class OptimisationEngine(Protocol):
    """The one interface every optimisation engine version implements."""

    name: str
    version: str

    def recommend(self, context: DecisionContext) -> RankedRecommendations: ...


class BenchmarkContextSource(Protocol):
    """Ground truth for Decision-quality evaluation (brief §7): a ``DecisionContext``
    per Document 6 §9 benchmark scenario. Implemented at the platform composition
    root — spans Simulation and Decision, which is orchestration, neither context
    may import directly.
    """

    def scenario_names(self) -> list[str]: ...

    def context_for(self, scenario_name: str) -> DecisionContext: ...
