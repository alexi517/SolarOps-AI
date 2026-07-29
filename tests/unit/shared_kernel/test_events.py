"""Tests for the domain event base and envelope."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from solarops.shared_kernel.events import DomainEvent, EventEnvelope
from solarops.shared_kernel.ids import EventId


@dataclass(frozen=True, slots=True, kw_only=True)
class BatteryCharged(DomainEvent):
    """A concrete event used only for testing the base."""

    target_soc: float
    # a field without a default, to prove kw_only lets subclasses add required fields
    asset_ref: str


def _make_event() -> BatteryCharged:
    return BatteryCharged(
        aggregate_id="ASSET-1",
        aggregate_type="Asset",
        target_soc=85.0,
        asset_ref="Battery_01",
    )


def test_event_gets_auto_id_and_timestamp() -> None:
    event = _make_event()
    assert isinstance(event.event_id, EventId)
    assert event.occurred_at.tzinfo is not None  # timezone-aware


def test_event_type_derives_from_class_name() -> None:
    assert _make_event().event_type == "BatteryCharged"


def test_events_have_distinct_ids() -> None:
    assert _make_event().event_id != _make_event().event_id


def test_correlation_id_defaults_to_none_and_can_be_set() -> None:
    assert _make_event().correlation_id is None
    correlated = BatteryCharged(
        aggregate_id="ASSET-1",
        aggregate_type="Asset",
        target_soc=85.0,
        asset_ref="Battery_01",
        correlation_id="trace-123",
    )
    assert correlated.correlation_id == "trace-123"


def test_event_is_immutable() -> None:
    event = _make_event()
    with pytest.raises(Exception):
        event.target_soc = 90.0  # type: ignore[misc]


def test_envelope_captures_routing_metadata() -> None:
    event = _make_event()
    envelope = EventEnvelope.of(event)
    assert envelope.event_id == str(event.event_id)
    assert envelope.event_type == "BatteryCharged"
    assert envelope.aggregate_id == "ASSET-1"
    assert envelope.aggregate_type == "Asset"
    assert envelope.occurred_at == event.occurred_at
    assert envelope.correlation_id is None


def test_provided_timestamp_is_respected() -> None:
    when = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
    event = BatteryCharged(
        aggregate_id="ASSET-1",
        aggregate_type="Asset",
        occurred_at=when,
        target_soc=85.0,
        asset_ref="Battery_01",
    )
    assert event.occurred_at == when
