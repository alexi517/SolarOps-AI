"""ConfidenceBand / ConfidenceEstimate — Document 9 §8 (Phase 6d brief).

A calculated [0, 1] score, banded into High/Medium/Low, plus the factors
that produced it — attached to every ``Recommendation`` so an operator (or
the approval path) never has to trust an unexplained number.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["ConfidenceBand", "ConfidenceEstimate"]


class ConfidenceBand(StrEnum):
    """Document 9 §8: High > 0.90, Medium 0.70-0.90, Low < 0.70 (exact
    thresholds live in ``RuleEngineConfig``, not hardcoded here)."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True, slots=True)
class ConfidenceEstimate:
    """The output of ``ConfidenceEstimator.estimate()`` — one per decision
    cycle (see ``rule_based_optimiser.py``'s docstring for why it's not
    computed per-candidate)."""

    score: float
    band: ConfidenceBand
    factors: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"ConfidenceEstimate.score must be within [0,1], got {self.score}")
        if not self.factors:
            raise ValueError(
                "ConfidenceEstimate.factors must not be empty — always explain the score"
            )
