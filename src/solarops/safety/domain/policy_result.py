"""PolicyResult — outcome of PolicyValidator (Doc 8 §6.5 names this VO; not in
the brief's Part A file list, added to fill that naming gap — see the Phase 5
plan's "gap I'm filling" note). Attached to a Command once Part B builds it.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["PolicyResult"]


class PolicyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    violations: tuple[str, ...] = Field(default_factory=tuple)
    evaluated_at: datetime

    @field_validator("evaluated_at")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("PolicyResult.evaluated_at must be timezone-aware")
        return value
