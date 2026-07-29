"""Domain events the Safety context emits (Doc 8 §6.4)."""

from __future__ import annotations

from dataclasses import dataclass

from solarops.shared_kernel import DomainEvent, RiskLevel

__all__ = ["PolicyViolated", "CommandBlockedBySafety", "RiskAssessed"]


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyViolated(DomainEvent):
    """A planned command failed one or more operational policy checks."""

    violations: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandBlockedBySafety(DomainEvent):
    """A planned command failed one or more hard safety checks."""

    failed_checks: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class RiskAssessed(DomainEvent):
    """A planned command was classified into a RiskLevel."""

    level: RiskLevel
    factors: tuple[str, ...]
