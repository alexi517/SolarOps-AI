"""TelemetryIngestionService — reads one reading and reconstructs EnergyState (Doc 8 §6.1)."""

from __future__ import annotations

from datetime import timedelta

from solarops.shared_kernel import Clock, DomainEvent, GridStatus, InverterStatus, SiteId
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.telemetry.domain.events import AssetOffline, TelemetryIngested
from solarops.telemetry.domain.ports import TelemetrySource
from solarops.telemetry.domain.telemetry import Telemetry

DEFAULT_STALENESS_THRESHOLD = timedelta(seconds=30)


class TelemetryIngestionService:
    """Pulls one reading via the ``TelemetrySource`` port and builds an ``EnergyState``.

    Staleness/offline detection is a deliberately minimal v1 heuristic: it looks
    at the single site-level reading's age and fault indicators, not independent
    per-asset heartbeats (there's only one ``TelemetrySource`` in v1).

    ``check_staleness`` exists because "age" only means something for a source
    that can genuinely fall behind (real hardware whose last-known reading might
    be cached/stale). The simulated ``TwinTelemetrySource`` produces a reading
    synchronously, on demand, every call — it is by definition never stale, no
    matter how much real wall-clock time has passed since the last tick (the
    twin's own simulated clock and the real clock are intentionally
    independent — see ``DigitalTwin``). Comparing the two was a bug, not a
    feature: the platform composition root disables this check when wiring the
    twin, and would re-enable it when a real hardware source is wired instead.
    """

    def __init__(
        self,
        source: TelemetrySource,
        clock: Clock,
        staleness_threshold: timedelta = DEFAULT_STALENESS_THRESHOLD,
        check_staleness: bool = True,
    ) -> None:
        self._source = source
        self._clock = clock
        self._staleness_threshold = staleness_threshold
        self._check_staleness = check_staleness

    def ingest(self, site_id: SiteId) -> tuple[EnergyState, list[DomainEvent]]:
        telemetry = self._source.read(site_id)
        events: list[DomainEvent] = [
            TelemetryIngested(
                aggregate_id=str(site_id),
                aggregate_type="Site",
                reading_timestamp=telemetry.timestamp,
            )
        ]

        offline, reason = self._detect_offline(telemetry)
        if offline:
            events.append(
                AssetOffline(aggregate_id=str(site_id), aggregate_type="Site", reason=reason)
            )

        state = EnergyState.from_telemetry(telemetry, any_asset_offline=offline)
        return state, events

    def _detect_offline(self, telemetry: Telemetry) -> tuple[bool, str]:
        if self._check_staleness:
            age = self._clock.now() - telemetry.timestamp
            if age > self._staleness_threshold:
                return True, (
                    f"reading is {age.total_seconds():.0f}s old "
                    f"(> {self._staleness_threshold.total_seconds():.0f}s threshold)"
                )
        if telemetry.inverter_status in (InverterStatus.FAULT_COMM_LOSS, InverterStatus.SHUTDOWN):
            return True, f"inverter status is {telemetry.inverter_status}"
        if telemetry.grid_status != GridStatus.CONNECTED:
            return True, f"grid status is {telemetry.grid_status}"
        return False, ""
