from datetime import UTC, datetime, timedelta

from solarops.shared_kernel import FixedClock, GridStatus, InverterStatus, SiteId
from solarops.telemetry.application.ingestion_service import TelemetryIngestionService
from solarops.telemetry.domain.events import AssetOffline, TelemetryIngested

from ..domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
READING_TIME = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


class FakeTelemetrySource:
    def __init__(self, telemetry):
        self._telemetry = telemetry

    def read(self, site_id):
        assert site_id == SITE_ID
        return self._telemetry


def make_service(telemetry=None, now=None, staleness_threshold=timedelta(seconds=30)):
    telemetry = telemetry or make_telemetry(site_id=SITE_ID, timestamp=READING_TIME)
    clock = FixedClock(now or READING_TIME)
    return TelemetryIngestionService(FakeTelemetrySource(telemetry), clock, staleness_threshold)


def test_fresh_normal_reading_produces_only_telemetry_ingested():
    service = make_service()
    state, events = service.ingest(SITE_ID)

    assert state.any_asset_offline is False
    assert [type(e) for e in events] == [TelemetryIngested]


def test_stale_reading_marks_offline():
    service = make_service(now=READING_TIME + timedelta(minutes=5))
    state, events = service.ingest(SITE_ID)

    assert state.any_asset_offline is True
    assert [type(e) for e in events] == [TelemetryIngested, AssetOffline]
    assert "old" in events[1].reason


def test_inverter_comm_loss_marks_offline_even_when_fresh():
    telemetry = make_telemetry(
        site_id=SITE_ID, timestamp=READING_TIME, inverter_status=InverterStatus.FAULT_COMM_LOSS
    )
    service = make_service(telemetry=telemetry)
    state, events = service.ingest(SITE_ID)

    assert state.any_asset_offline is True
    assert any(isinstance(e, AssetOffline) for e in events)


def test_grid_outage_marks_offline():
    telemetry = make_telemetry(
        site_id=SITE_ID, timestamp=READING_TIME, grid_status=GridStatus.OUTAGE
    )
    service = make_service(telemetry=telemetry)
    state, events = service.ingest(SITE_ID)

    assert state.any_asset_offline is True
    assert any(isinstance(e, AssetOffline) for e in events)
