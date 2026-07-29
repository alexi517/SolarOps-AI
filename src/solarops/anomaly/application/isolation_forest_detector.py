"""IsolationForestDetector — first ML detector, proves the ``TrainableDetector``
interface (brief §4).

Trains unsupervised on twin-generated normal-operation history (no labels)
via ``HistoricalDataSource``; flags any tick scikit-learn's ``IsolationForest``
scores as an outlier against that learned baseline. Reduces ``EnergyState`` to
a small numeric feature vector locally — no need for Forecast's ``FeatureSet``
machinery (Anomaly can't import Forecast, and this is the only ML detector
here).

IsolationForest itself only says "this reading is unusual," not *which* of
the six ``AnomalyType``s it is. Attribution is a disclosed heuristic, not
something the brief specifies: whichever input feature deviates furthest (in
standard deviations from the training-set mean) decides the reported type —
each feature maps to the one type/asset it's most naturally about. This
detector never reports ``COMMUNICATION_LOSS`` (a discrete status change, not
a continuous-feature outlier) — ``RuleDetector`` already covers that
deterministically; detectors are combined for complementary coverage, not
each individually complete.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import numpy as np
from sklearn.ensemble import IsolationForest

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.detection import Detection
from solarops.anomaly.domain.ports import FitResult
from solarops.anomaly.infrastructure.config import AnomalyConfig
from solarops.shared_kernel import AssetId, AssetType
from solarops.telemetry.domain.energy_state import EnergyState

__all__ = ["IsolationForestDetector"]

_FeatureEntry = tuple[str, Callable[[EnergyState], float], AnomalyType, AssetType]

# (feature name, vectoriser, attributed AnomalyType, attributed AssetType)
_FEATURES: tuple[_FeatureEntry, ...] = (
    (
        "solar_power_kw",
        lambda s: s.solar_power.value,
        AnomalyType.SENSOR_FAILURE,
        AssetType.SOLAR_PV,
    ),
    (
        "battery_soc_pct",
        lambda s: s.battery_soc.value,
        AnomalyType.BATTERY_OVERHEATING,
        AssetType.BATTERY,
    ),
    (
        "battery_temp_c",
        lambda s: s.battery_temp.value,
        AnomalyType.BATTERY_OVERHEATING,
        AssetType.BATTERY,
    ),
    (
        "battery_power_kw",
        lambda s: s.battery_power.value,
        AnomalyType.BATTERY_OVERHEATING,
        AssetType.BATTERY,
    ),
    (
        "inverter_output_kw",
        lambda s: s.inverter_output.value,
        AnomalyType.INVERTER_FAULT,
        AssetType.INVERTER,
    ),
    (
        "grid_voltage_v",
        lambda s: s.grid_voltage.value,
        AnomalyType.GRID_INSTABILITY,
        AssetType.GRID,
    ),
    (
        "grid_frequency_hz",
        lambda s: s.grid_frequency.value,
        AnomalyType.GRID_INSTABILITY,
        AssetType.GRID,
    ),
    (
        "building_load_kw",
        lambda s: s.building_load.value,
        AnomalyType.LOAD_SPIKE,
        AssetType.BUILDING_LOAD,
    ),
)


def _vectorize(state: EnergyState) -> list[float]:
    return [vectoriser(state) for _, vectoriser, _, _ in _FEATURES]


def _asset_id(asset_type: AssetType) -> AssetId:
    return AssetId(f"ASSET-{asset_type.value.lower()}-1")


class IsolationForestDetector:
    name = "isolation-forest-detector"
    version = "v1"
    supported_types = frozenset(anomaly_type for _, _, anomaly_type, _ in _FEATURES)

    def __init__(self, config: AnomalyConfig) -> None:
        self._config = config
        self._model: IsolationForest | None = None
        self._feature_mean: np.ndarray | None = None
        self._feature_std: np.ndarray | None = None

    @property
    def is_fitted(self) -> bool:
        return self._model is not None

    def fit(self, normal_history: list[EnergyState]) -> FitResult:
        if not normal_history:
            raise ValueError(f"{self.name}: cannot fit on empty normal-operation history")

        rows = np.array([_vectorize(s) for s in normal_history])
        model = IsolationForest(
            n_estimators=self._config.isolation_forest_n_estimators,
            contamination=self._config.isolation_forest_contamination,
            random_state=self._config.isolation_forest_random_state,
        )
        model.fit(rows)
        self._model = model
        self._feature_mean = rows.mean(axis=0)
        self._feature_std = rows.std(axis=0)
        return FitResult(trained_on=len(normal_history), trained_at=datetime.now(UTC))

    def detect(self, state: EnergyState, history: list[EnergyState]) -> list[Detection]:
        if self._model is None or self._feature_mean is None or self._feature_std is None:
            raise RuntimeError(f"{self.name} has not been fitted yet")

        row = np.array(_vectorize(state))
        prediction = self._model.predict(row.reshape(1, -1))[0]  # 1 = normal, -1 = anomalous
        if prediction != -1:
            return []

        # decision_function: more negative = more anomalous
        raw_score = self._model.decision_function(row.reshape(1, -1))[0]
        confidence = float(min(1.0, max(0.0, -raw_score * 2)))

        safe_std = np.where(self._feature_std == 0, 1.0, self._feature_std)
        z_scores = (row - self._feature_mean) / safe_std
        worst_index = int(np.argmax(np.abs(z_scores)))
        feature_name, _, anomaly_type, asset_type = _FEATURES[worst_index]

        return [
            Detection(
                anomaly_type=anomaly_type,
                confidence=confidence,
                affected_asset=_asset_id(asset_type),
                evidence=(
                    f"isolation forest outlier (score={raw_score:.3f}); "
                    f"most deviant feature: {feature_name}={row[worst_index]:.2f} "
                    f"({z_scores[worst_index]:+.1f} sigma from training baseline)"
                ),
                detector_name=self.name,
                detector_version=self.version,
                detected_at=state.timestamp,
            )
        ]
