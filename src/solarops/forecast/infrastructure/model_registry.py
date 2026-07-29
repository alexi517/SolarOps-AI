"""ModelRegistry implementations (brief §4) — in-memory default, MLflow-backed integration.

``InMemoryModelRegistry`` is the always-tested path every unit test uses.
``MLflowModelRegistry`` additionally logs every registration to a local
SQLite-backed MLflow tracking store (Document 6 §13: model versions, metrics,
hyperparameters) — see its own docstring for exactly what it does and does not
do.
"""

from __future__ import annotations

import contextlib

import mlflow
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.domain.ports import ForecastModel

__all__ = ["InMemoryModelRegistry", "MLflowModelRegistry"]


class InMemoryModelRegistry:
    """Dict-backed ModelRegistry — no external service, used by every unit test."""

    def __init__(self) -> None:
        self._current: dict[ForecastKind, ForecastModel] = {}
        self._metrics: dict[ForecastKind, dict[str, float]] = {}

    def get_current(self, kind: ForecastKind) -> ForecastModel | None:
        return self._current.get(kind)

    def register(self, model: ForecastModel, metrics: dict[str, float]) -> None:
        self._current[model.kind] = model
        self._metrics[model.kind] = dict(metrics)

    def get_current_metrics(self, kind: ForecastKind) -> dict[str, float] | None:
        return self._metrics.get(kind)


class MLflowModelRegistry:
    """Real MLflow tracking + Model Registry, backed by a local SQLite file.

    MLflow's Model Registry API requires a database-backed tracking store —
    ``sqlite:///<path>`` needs no server process, the same "no infra to stand
    up" shape as every other real adapter in this codebase.

    What this class actually serves from ``get_current()`` is an in-process
    cache of the same model object that was registered — round-tripping each
    of this phase's custom model classes through MLflow's generic pyfunc
    format so a *reloaded* model could serve predictions is out of scope for
    6a. What it genuinely provides is versioned experiment tracking: every
    registration creates an MLflow run (params, metrics) and a Model Registry
    version, inspectable independently of this process.
    """

    def __init__(self, tracking_uri: str, experiment_name: str = "solarops-forecast") -> None:
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        self._client = MlflowClient(tracking_uri=tracking_uri)
        self._current: dict[ForecastKind, ForecastModel] = {}
        self._metrics: dict[ForecastKind, dict[str, float]] = {}

    def get_current(self, kind: ForecastKind) -> ForecastModel | None:
        return self._current.get(kind)

    def register(self, model: ForecastModel, metrics: dict[str, float]) -> None:
        registered_name = f"solarops-{model.kind.value.lower()}"
        with mlflow.start_run(run_name=f"{model.name}-{model.version}") as run:
            mlflow.log_param("model_name", model.name)
            mlflow.log_param("model_version", model.version)
            mlflow.log_param("kind", model.kind.value)
            for metric_name, value in metrics.items():
                mlflow.log_metric(metric_name, value)

            self._ensure_registered_name(registered_name)
            self._client.create_model_version(
                name=registered_name,
                source=f"runs:/{run.info.run_id}",
                run_id=run.info.run_id,
            )

        self._current[model.kind] = model
        self._metrics[model.kind] = dict(metrics)

    def get_current_metrics(self, kind: ForecastKind) -> dict[str, float] | None:
        return self._metrics.get(kind)

    def _ensure_registered_name(self, name: str) -> None:
        # already exists -> fine, we're adding a new version to it
        with contextlib.suppress(MlflowException):
            self._client.create_registered_model(name)
