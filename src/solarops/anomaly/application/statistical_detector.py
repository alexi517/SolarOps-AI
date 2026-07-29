"""StatisticalDetector — rolling baseline + a dropout check (Phase 6b brief §4).

Load spikes: a reading N sigma above the recent rolling mean/stddev of
building load — genuinely statistical. Sensor dropouts: irradiance says the
sun is up but solar output reads exactly zero — a direct signature of a dead
solar sensor (this codebase's stand-in for "sensor failure," per the Phase 6a
plan's disclosed choice of ``inject_fault("solar", "OFFLINE")``), not a
rolling-window computation, but grouped here per the brief's §4 split rather
than in ``rule_detector.py``. A night-time zero reading is *not* flagged —
irradiance is legitimately zero then too, so the "sun is up but output is
zero" mismatch never fires.
"""

from __future__ import annotations

import statistics

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.detection import Detection
from solarops.anomaly.infrastructure.config import AnomalyConfig
from solarops.shared_kernel import AssetId, AssetType
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["StatisticalDetector"]

_DAYLIGHT_IRRADIANCE_THRESHOLD_W_M2 = 50.0


def _asset_id(asset_type: AssetType) -> AssetId:
    return AssetId(f"ASSET-{asset_type.value.lower()}-1")


class StatisticalDetector:
    name = "statistical-detector"
    version = "v1"
    supported_types = frozenset({AnomalyType.LOAD_SPIKE, AnomalyType.SENSOR_FAILURE})

    def __init__(self, config: AnomalyConfig) -> None:
        self._config = config

    def detect(self, state: EnergyState, history: list[EnergyState]) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._load_spike(state, history))
        detections.extend(self._sensor_dropout(state))
        return detections

    def _load_spike(self, state: EnergyState, history: list[EnergyState]) -> list[Detection]:
        if len(history) < self._config.min_history_for_baseline:
            return []

        loads = [s.building_load.value for s in history]
        mean_load = statistics.fmean(loads)
        stddev_load = statistics.pstdev(loads)
        if stddev_load == 0:
            return []

        z_score = (state.building_load.value - mean_load) / stddev_load
        if abs(z_score) <= self._config.load_spike_sigma_threshold:
            return []

        confidence = min(1.0, abs(z_score) / (self._config.load_spike_sigma_threshold * 2))
        return [
            Detection(
                anomaly_type=AnomalyType.LOAD_SPIKE,
                confidence=confidence,
                affected_asset=_asset_id(AssetType.BUILDING_LOAD),
                evidence=(
                    f"building_load={state.building_load.value:.1f}kW, "
                    f"{z_score:+.1f} sigma from recent mean {mean_load:.1f}kW"
                ),
                detector_name=self.name,
                detector_version=self.version,
                detected_at=state.timestamp,
            )
        ]

    def _sensor_dropout(self, state: EnergyState) -> list[Detection]:
        sun_should_be_up = state.irradiance_w_m2 > _DAYLIGHT_IRRADIANCE_THRESHOLD_W_M2
        if not (sun_should_be_up and state.solar_power.value == 0.0):
            return []

        return [
            Detection(
                anomaly_type=AnomalyType.SENSOR_FAILURE,
                confidence=0.9,
                affected_asset=_asset_id(AssetType.SOLAR_PV),
                evidence=(
                    f"irradiance={state.irradiance_w_m2:.0f}W/m2 but solar_power=0.0kW"
                ),
                detector_name=self.name,
                detector_version=self.version,
                detected_at=state.timestamp,
            )
        ]
