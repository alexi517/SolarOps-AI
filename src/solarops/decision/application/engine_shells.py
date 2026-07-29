"""Class shells against the ``OptimisationEngine`` interface (brief §1/§3).

Not implemented yet — proves the interface accommodates the v1->v4 roadmap
(constraint optimisation, model-predictive control, reinforcement learning)
without anything downstream changing when they land. Same pattern as
Forecast's ``infrastructure/models/shells.py`` (Phase 6a).
"""

from __future__ import annotations

from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.domain.ranked_recommendations import RankedRecommendations

__all__ = ["ConstraintOptimiser", "MpcOptimiser", "RlOptimiser"]


class _UnimplementedEngineShell:
    version = "unimplemented"

    def recommend(self, context: DecisionContext) -> RankedRecommendations:
        raise NotImplementedError(f"{self.name} is not implemented yet (Phase 6c brief §1/§3)")


class ConstraintOptimiser(_UnimplementedEngineShell):
    """v2 — OR-Tools constraint optimisation."""

    name = "constraint-optimiser"


class MpcOptimiser(_UnimplementedEngineShell):
    """v3 — model-predictive control."""

    name = "mpc-optimiser"


class RlOptimiser(_UnimplementedEngineShell):
    """v4 — reinforcement learning. Explicit placeholder per brief §3."""

    name = "rl-optimiser"
