"""SafetyAssessment — outcome of SafetyValidator (Doc 8 §6.4): the final technical gate."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["SafetyAssessment"]


class SafetyAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    failed_checks: tuple[str, ...] = Field(default_factory=tuple)
    evaluated_at: datetime

    @field_validator("evaluated_at")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("SafetyAssessment.evaluated_at must be timezone-aware")
        return value
