"""Domain events the Telemetry context emits (Doc 8 §6.1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from solarops.shared_kernel import DomainEvent

__all__ = ["TelemetryIngested", "EnergyStateUpdated", "AssetOffline"]


@dataclass(frozen=True, slots=True, kw_only=True)
class TelemetryIngested(DomainEvent):
    """A raw reading was received from a ``TelemetrySource``."""

    reading_timestamp: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class EnergyStateUpdated(DomainEvent):
    """The site's current ``EnergyState`` changed."""

    state_timestamp: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetOffline(DomainEvent):
    """An asset (or the whole site) is considered offline: stale or faulted reading."""

    reason: str
