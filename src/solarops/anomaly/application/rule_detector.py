"""RuleDetector — deterministic threshold checks (Phase 6b brief §4).

Covers the fault types with an unambiguous fixed-threshold signature: battery
overheating, grid instability, and inverter faults (communication loss is
its own sub-case, checked first since ``FAULT_COMM_LOSS`` is also a fault
status). Load spikes and sensor dropouts need a notion of "expected" derived
from recent history — that's ``statistical_detector.py``'s job.

``detected_at`` is read off ``state.timestamp`` rather than a wall clock: a
detection is timestamped to when the condition was observed, in whatever
clock produced that reading (twin-simulated time during evaluation, real time
in production) — this is also what makes detection-latency measurement
against the twin's simulated clock meaningful.
"""

from __future__ import annotations

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.detection import Detection
from solarops.anomaly.infrastructure.config import AnomalyConfig
from solarops.shared_kernel import AssetId, AssetType
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["RuleDetector"]


def _asset_id(asset_type: AssetType) -> AssetId:
    return AssetId(f"ASSET-{asset_type.value.lower()}-1")


class RuleDetector:
    name = "rule-detector"
    version = "v1"
    supported_types = frozenset(
        {
            AnomalyType.BATTERY_OVERHEATING,
            AnomalyType.GRID_INSTABILITY,
            AnomalyType.COMMUNICATION_LOSS,
            AnomalyType.INVERTER_FAULT,
        }
    )

    def __init__(self, config: AnomalyConfig) -> None:
        self._config = config

    def detect(self, state: EnergyState, history: list[EnergyState]) -> list[Detection]:
        detections: list[Detection] = []

        if state.battery_temp.value > self._config.battery_overheat_temp_c:
            detections.append(
                Detection(
                    anomaly_type=AnomalyType.BATTERY_OVERHEATING,
                    confidence=1.0,
                    affected_asset=_asset_id(AssetType.BATTERY),
                    evidence=(
                        f"battery_temp={state.battery_temp.value:.1f}C > "
                        f"{self._config.battery_overheat_temp_c:.1f}C"
                    ),
                    detector_name=self.name,
                    detector_version=self.version,
                    detected_at=state.timestamp,
                )
            )

        if state.grid_status.value in self._config.grid_instability_statuses:
            detections.append(
                Detection(
                    anomaly_type=AnomalyType.GRID_INSTABILITY,
                    confidence=1.0,
                    affected_asset=_asset_id(AssetType.GRID),
                    evidence=f"grid_status={state.grid_status.value}",
                    detector_name=self.name,
                    detector_version=self.version,
                    detected_at=state.timestamp,
                )
            )

        if state.inverter_status.value in self._config.inverter_comm_loss_statuses:
            detections.append(
                Detection(
                    anomaly_type=AnomalyType.COMMUNICATION_LOSS,
                    confidence=1.0,
                    affected_asset=_asset_id(AssetType.INVERTER),
                    evidence=f"inverter_status={state.inverter_status.value}",
                    detector_name=self.name,
                    detector_version=self.version,
                    detected_at=state.timestamp,
                )
            )
        elif state.inverter_status.value in self._config.inverter_fault_statuses:
            detections.append(
                Detection(
                    anomaly_type=AnomalyType.INVERTER_FAULT,
                    confidence=1.0,
                    affected_asset=_asset_id(AssetType.INVERTER),
                    evidence=f"inverter_status={state.inverter_status.value}",
                    detector_name=self.name,
                    detector_version=self.version,
                    detected_at=state.timestamp,
                )
            )

        return detections
