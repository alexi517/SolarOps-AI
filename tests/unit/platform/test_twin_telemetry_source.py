from datetime import datetime

import pytest

from solarops.platform.twin_telemetry_source import TwinTelemetrySource
from solarops.shared_kernel import GridStatus, InverterStatus, SiteId
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.infrastructure.config import SiteConfig


def make_source(**site_overrides):
    twin = DigitalTwin(
        site_config=SiteConfig(site_id="site-001", update_interval_seconds=300, **site_overrides),
        start_time=datetime(2026, 7, 27, 0, 0),
    )
    return TwinTelemetrySource(twin), twin


def test_read_returns_telemetry_with_aware_timestamp_and_matching_site():
    source, _twin = make_source()
    telemetry = source.read(SiteId("site-001"))

    assert telemetry.site_id == SiteId("site-001")
    assert telemetry.timestamp.tzinfo is not None


def test_read_advances_the_twin_one_tick_per_call():
    source, _twin = make_source()
    first = source.read(SiteId("site-001"))
    second = source.read(SiteId("site-001"))
    assert second.timestamp > first.timestamp


def test_read_rejects_mismatched_site_id():
    source, _twin = make_source()
    with pytest.raises(ValueError, match="site-001"):
        source.read(SiteId("some-other-site"))


def test_enum_fields_carry_through_unchanged():
    source, _twin = make_source()
    telemetry = source.read(SiteId("site-001"))
    assert telemetry.grid_status is GridStatus.CONNECTED
    assert telemetry.inverter_status is InverterStatus.NORMAL
