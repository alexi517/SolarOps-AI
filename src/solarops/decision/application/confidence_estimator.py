"""ConfidenceEstimator — Document 9 §8 (Phase 6d brief §1).

Computes one ``ConfidenceEstimate`` per decision cycle from four weighted
factors, using only data already available to Decision (never a new ML
model, never a new context import — the anomaly count is a plain int
handed in via ``DecisionContext``, see its docstring).
"""

from __future__ import annotations

from solarops.decision.domain.confidence import ConfidenceBand, ConfidenceEstimate
from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.infrastructure.config import RuleEngineConfig
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.shared_kernel import Clock

__all__ = ["ConfidenceEstimator"]


class ConfidenceEstimator:
    def __init__(self, config: RuleEngineConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock

    def estimate(self, context: DecisionContext) -> ConfidenceEstimate:
        factors: list[str] = []

        forecast_score, forecast_factor = self._forecast_certainty(context)
        freshness_score, freshness_factor = self._data_freshness(context)
        completeness_score, completeness_factor = self._input_completeness(context)
        anomaly_score, anomaly_factor = self._anomaly_presence(context)

        for factor in (forecast_factor, freshness_factor, completeness_factor, anomaly_factor):
            if factor is not None:
                factors.append(factor)

        c = self._config
        score = (
            c.confidence_weight_forecast_certainty * forecast_score
            + c.confidence_weight_data_freshness * freshness_score
            + c.confidence_weight_input_completeness * completeness_score
            + c.confidence_weight_anomaly_presence * anomaly_score
        )
        score = max(0.0, min(1.0, score))

        if not factors:
            factors.append(f"all inputs fresh, complete, and available (score {score:.2f})")

        return ConfidenceEstimate(score=score, band=self._band_for(score), factors=tuple(factors))

    def _band_for(self, score: float) -> ConfidenceBand:
        c = self._config
        if score > c.confidence_band_high_threshold:
            return ConfidenceBand.HIGH
        if score < c.confidence_band_low_threshold:
            return ConfidenceBand.LOW
        return ConfidenceBand.MEDIUM

    def _forecast_certainty(self, context: DecisionContext) -> tuple[float, str | None]:
        """How much the recommendation could lean on forecasts, and how
        confident they are — an unavailable forecast contributes a low
        fixed sub-score rather than being skipped, so relying more heavily
        on missing data never looks the same as having it."""
        subscores: list[float] = []
        gaps: list[str] = []
        for kind in ForecastKind:
            forecast = context.forecast_for(kind)
            if forecast is None:
                subscores.append(self._config.confidence_unavailable_forecast_subscore)
                gaps.append(f"{kind.value.lower()} forecast unavailable")
            elif forecast.metadata.confidence is not None:
                subscores.append(forecast.metadata.confidence)
            else:
                subscores.append(self._config.confidence_missing_metadata_subscore)

        score = sum(subscores) / len(subscores)
        factor = f"{'; '.join(gaps)} -> reduced forecast certainty" if gaps else None
        return score, factor

    def _data_freshness(self, context: DecisionContext) -> tuple[float, str | None]:
        c = self._config
        age = (self._clock.now() - context.energy_state.timestamp).total_seconds()

        if age <= c.confidence_state_fresh_seconds:
            return 1.0, None
        if age >= c.confidence_state_stale_seconds:
            return 0.2, f"state reading is {age:.0f}s old -> stale, reduced confidence"

        span = c.confidence_state_stale_seconds - c.confidence_state_fresh_seconds
        fraction = (age - c.confidence_state_fresh_seconds) / span
        score = 1.0 - fraction * 0.8
        return score, f"state reading is {age:.0f}s old -> reduced confidence"

    def _input_completeness(self, context: DecisionContext) -> tuple[float, str | None]:
        """Distinct from forecast certainty: how much of the expected input
        *set* is present at all, regardless of how confident what's there is."""
        kinds = tuple(ForecastKind)
        present = sum(1 for kind in kinds if context.forecast_for(kind) is not None)
        score = present / len(kinds)
        if present < len(kinds):
            missing = len(kinds) - present
            return score, f"{missing}/{len(kinds)} expected forecast inputs missing"
        return score, None

    def _anomaly_presence(self, context: DecisionContext) -> tuple[float, str | None]:
        """Simplification, disclosed: reduces confidence for any active
        anomaly system-wide, not matched to a specific asset — Decision has
        no asset-relevance mapping to a Recommendation today, and building
        one is out of this phase's scope (decision-logic only)."""
        count = context.active_anomaly_count
        if count <= 0:
            return 1.0, None
        c = self._config
        score = max(
            c.confidence_anomaly_min_subscore,
            1.0 - c.confidence_anomaly_penalty_per_anomaly * count,
        )
        plural = "y" if count == 1 else "ies"
        return score, f"{count} active anomal{plural} -> reduced confidence"
