"""DetectorRegistry implementations (brief §4) — in-memory default, MLflow-backed integration.

Mirrors ``forecast.infrastructure.model_registry`` exactly, keyed by detector
name rather than a forecast kind — ``get_active()`` returns every currently
-registered detector. Coverage is tracked per ``AnomalyType`` (cleanup pass,
docs/phase6b-cleanup-per-check-gating.md): a detector can be active while
covering only some of the fault types it's able to detect.
"""

from __future__ import annotations

import contextlib

import mlflow
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.ports import AnomalyDetector

__all__ = ["InMemoryDetectorRegistry", "MLflowDetectorRegistry"]


class InMemoryDetectorRegistry:
    """Dict-backed DetectorRegistry — no external service, used by every unit test."""

    def __init__(self) -> None:
        self._active: dict[str, AnomalyDetector] = {}
        self._covered_types: dict[str, frozenset[AnomalyType]] = {}
        self._metrics_by_type: dict[str, dict[AnomalyType, dict[str, float]]] = {}

    def get_active(self) -> list[AnomalyDetector]:
        return list(self._active.values())

    def covered_types(self, detector_name: str) -> frozenset[AnomalyType]:
        return self._covered_types.get(detector_name, frozenset())

    def register(
        self,
        detector: AnomalyDetector,
        covered_types: frozenset[AnomalyType],
        metrics_by_type: dict[AnomalyType, dict[str, float]],
    ) -> None:
        self._active[detector.name] = detector
        self._covered_types[detector.name] = covered_types
        self._metrics_by_type[detector.name] = dict(metrics_by_type)

    def get_metrics_by_type(self, detector_name: str) -> dict[AnomalyType, dict[str, float]]:
        return dict(self._metrics_by_type.get(detector_name, {}))


class MLflowDetectorRegistry:
    """Real MLflow tracking + Model Registry, backed by a local SQLite file.

    Same shape and same disclosed limitation as
    ``forecast.infrastructure.model_registry.MLflowModelRegistry``: what
    serves ``get_active()`` is an in-process cache of the registered detector
    objects, not a reloaded MLflow artifact — what MLflow genuinely provides
    here is versioned experiment tracking (Document 6 §13). Per-type metrics
    are logged with the type name as a prefix (e.g. ``grid_instability_recall``)
    so a single MLflow run still captures the whole detector's coverage.
    """

    def __init__(self, tracking_uri: str, experiment_name: str = "solarops-anomaly") -> None:
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        self._client = MlflowClient(tracking_uri=tracking_uri)
        self._active: dict[str, AnomalyDetector] = {}
        self._covered_types: dict[str, frozenset[AnomalyType]] = {}
        self._metrics_by_type: dict[str, dict[AnomalyType, dict[str, float]]] = {}

    def get_active(self) -> list[AnomalyDetector]:
        return list(self._active.values())

    def covered_types(self, detector_name: str) -> frozenset[AnomalyType]:
        return self._covered_types.get(detector_name, frozenset())

    def register(
        self,
        detector: AnomalyDetector,
        covered_types: frozenset[AnomalyType],
        metrics_by_type: dict[AnomalyType, dict[str, float]],
    ) -> None:
        registered_name = f"solarops-anomaly-{detector.name}"
        with mlflow.start_run(run_name=f"{detector.name}-{detector.version}") as run:
            mlflow.log_param("detector_name", detector.name)
            mlflow.log_param("detector_version", detector.version)
            mlflow.log_param(
                "covered_types", ",".join(sorted(t.value for t in covered_types))
            )
            for anomaly_type, metrics in metrics_by_type.items():
                prefix = anomaly_type.value.lower()
                for metric_name, value in metrics.items():
                    mlflow.log_metric(f"{prefix}_{metric_name}", value)

            self._ensure_registered_name(registered_name)
            self._client.create_model_version(
                name=registered_name,
                source=f"runs:/{run.info.run_id}",
                run_id=run.info.run_id,
            )

        self._active[detector.name] = detector
        self._covered_types[detector.name] = covered_types
        self._metrics_by_type[detector.name] = dict(metrics_by_type)

    def get_metrics_by_type(self, detector_name: str) -> dict[AnomalyType, dict[str, float]]:
        return dict(self._metrics_by_type.get(detector_name, {}))

    def _ensure_registered_name(self, name: str) -> None:
        # already exists -> fine, we're adding a new version to it
        with contextlib.suppress(MlflowException):
            self._client.create_registered_model(name)
