"""RiskAssessment — outcome of RiskAssessor (Doc 8 §6.4), driving the CESF §8 approval path."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from solarops.shared_kernel import RiskLevel

__all__ = ["RiskAssessment"]


class RiskAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    level: RiskLevel
    factors: tuple[str, ...] = Field(default_factory=tuple)
    assessed_at: datetime

    @field_validator("assessed_at")
    @classmethod
    def _assessed_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("RiskAssessment.assessed_at must be timezone-aware")
        return value
