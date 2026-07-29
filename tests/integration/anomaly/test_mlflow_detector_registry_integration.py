"""MLflowDetectorRegistry against a real, temp-file SQLite tracking store.

No server process — self-contained, so unlike the Redis integration test this
one always runs, never skipped.
"""

from __future__ import annotations

from mlflow.tracking import MlflowClient

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.infrastructure.detector_registry import MLflowDetectorRegistry

GRID = frozenset({AnomalyType.GRID_INSTABILITY})


class _FakeDetector:
    def __init__(self, name: str) -> None:
        self.name = name
        self.version = "v1"

    def detect(self, state, history):  # noqa: ANN001
        return []


def test_register_stores_the_detector_for_in_process_lookup(tmp_path):
    db_path = tmp_path / "mlflow.db"
    registry = MLflowDetectorRegistry(
        tracking_uri=f"sqlite:///{db_path}", experiment_name="test-anomaly"
    )
    detector = _FakeDetector("rule-detector")

    registry.register(detector, GRID, {AnomalyType.GRID_INSTABILITY: {"recall": 0.95}})

    assert registry.get_active() == [detector]
    assert registry.covered_types("rule-detector") == GRID
    assert registry.get_metrics_by_type("rule-detector") == {
        AnomalyType.GRID_INSTABILITY: {"recall": 0.95}
    }


def test_register_logs_a_real_mlflow_run_with_params_and_metrics(tmp_path):
    db_path = tmp_path / "mlflow.db"
    tracking_uri = f"sqlite:///{db_path}"
    registry = MLflowDetectorRegistry(tracking_uri=tracking_uri, experiment_name="test-anomaly")
    detector = _FakeDetector("rule-detector")

    registry.register(detector, GRID, {AnomalyType.GRID_INSTABILITY: {"recall": 0.95}})

    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name("test-anomaly")
    assert experiment is not None

    runs = client.search_runs([experiment.experiment_id])
    assert len(runs) == 1
    run = runs[0]
    assert run.data.params["detector_name"] == "rule-detector"
    assert run.data.params["covered_types"] == "GRID_INSTABILITY"
    assert run.data.metrics["grid_instability_recall"] == 0.95


def test_register_creates_a_model_registry_version(tmp_path):
    db_path = tmp_path / "mlflow.db"
    tracking_uri = f"sqlite:///{db_path}"
    registry = MLflowDetectorRegistry(tracking_uri=tracking_uri, experiment_name="test-anomaly")

    metrics_v1 = {AnomalyType.GRID_INSTABILITY: {"recall": 0.9}}
    metrics_v2 = {AnomalyType.GRID_INSTABILITY: {"recall": 0.95}}
    registry.register(_FakeDetector("rule-detector"), GRID, metrics_v1)
    registry.register(_FakeDetector("rule-detector"), GRID, metrics_v2)

    client = MlflowClient(tracking_uri=tracking_uri)
    versions = client.search_model_versions("name='solarops-anomaly-rule-detector'")
    assert len(versions) == 2
