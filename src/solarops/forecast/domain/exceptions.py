"""Forecast-specific domain exceptions.

Not named in the Phase 6a brief's file list — added because a forecaster asked
to produce a prediction before any model has passed the evaluation gate (§6)
needs to fail loudly rather than silently return nothing, the same
"never invent a silent default" principle this codebase applies everywhere
else. Mirrors the style of ``shared_kernel.exceptions`` (a reason string,
never a bare stdlib exception for a business-rule situation).
"""

from __future__ import annotations

from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.shared_kernel import DomainError

__all__ = ["NoRegisteredModel"]


class NoRegisteredModel(DomainError):
    """No model has been registered for this ForecastKind yet."""

    def __init__(self, kind: ForecastKind) -> None:
        self.kind = kind
        super().__init__(f"No registered model for {kind} — forecast cannot be produced")
