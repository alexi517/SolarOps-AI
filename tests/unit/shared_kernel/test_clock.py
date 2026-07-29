"""Tests for the clock abstraction."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from solarops.shared_kernel.clock import Clock, FixedClock, SystemClock


def test_system_clock_returns_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_system_clock_satisfies_the_protocol() -> None:
    assert isinstance(SystemClock(), Clock)
    assert isinstance(FixedClock(datetime(2026, 1, 1, tzinfo=UTC)), Clock)


def test_fixed_clock_is_pinned() -> None:
    moment = datetime(2026, 7, 25, 9, 30, tzinfo=UTC)
    clock = FixedClock(moment)
    assert clock.now() == moment
    assert clock.now() == moment  # does not move on its own


def test_fixed_clock_set_and_advance() -> None:
    clock = FixedClock(datetime(2026, 7, 25, 9, 0, tzinfo=UTC))
    clock.advance(timedelta(hours=1, minutes=30))
    assert clock.now() == datetime(2026, 7, 25, 10, 30, tzinfo=UTC)
    clock.set(datetime(2027, 1, 1, tzinfo=UTC))
    assert clock.now() == datetime(2027, 1, 1, tzinfo=UTC)


def test_fixed_clock_normalises_to_utc() -> None:
    eastern = timezone(timedelta(hours=-5))
    clock = FixedClock(datetime(2026, 7, 25, 7, 0, tzinfo=eastern))
    # 07:00 -05:00 == 12:00 UTC
    assert clock.now() == datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def test_fixed_clock_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError):
        FixedClock(datetime(2026, 7, 25, 9, 0))  # no tzinfo
