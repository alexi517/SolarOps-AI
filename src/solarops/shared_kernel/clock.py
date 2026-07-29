
"""Clock abstraction.

The domain never calls ``datetime.now()`` directly. Instead it depends on a
``Clock`` port, so tests can pin time and the Digital Twin can drive simulated
time forward deterministically. All clocks return timezone-aware UTC datetimes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable

__all__ = ["Clock", "SystemClock", "FixedClock"]


@runtime_checkable
class Clock(Protocol):
    """A source of the current time."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC datetime."""
        ...


class SystemClock:
    """The real wall clock, in UTC."""

    __slots__ = ()

    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """A controllable clock for tests and simulation.

    Starts pinned at ``moment`` and only moves when explicitly told to, via
    :meth:`set` or :meth:`advance`. Rejects naive datetimes so time zones can
    never silently go missing.
    """

    __slots__ = ("_moment",)

    def __init__(self, moment: datetime) -> None:
        self._moment = self._as_aware_utc(moment)

    @staticmethod
    def _as_aware_utc(moment: datetime) -> datetime:
        if moment.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        return moment.astimezone(UTC)

    def now(self) -> datetime:
        return self._moment

    def set(self, moment: datetime) -> None:
        self._moment = self._as_aware_utc(moment)

    def advance(self, delta: timedelta) -> None:
        self._moment = self._moment + delta
