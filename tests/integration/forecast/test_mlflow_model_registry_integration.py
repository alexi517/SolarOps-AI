"""MLflowModelRegistry against a real, temp-file SQLite tracking store.

No server process — self-contained, so unlike the Redis integration test this
one always runs, never skipped.
"""

from __future__ import annotations

from mlflow.tracking import MlflowClient

from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.model_registry import MLflowModelRegistry
from solarops.forecast.infrastructure.models.solar_baseline import SolarBaseline


def make_registry(tmp_path) -> MLflowModelRegistry:
    db_path = tmp_path / "mlflow.db"
    return MLflowModelRegistry(tracking_uri=f"sqlite:///{db_path}", experiment_name="test-forecast")


def test_register_stores_the_model_for_in_process_lookup(tmp_path):
    registry = make_registry(tmp_path)
    model = SolarBaseline()

    registry.register(model, {"solar_mae_pct": 4.2})

    assert registry.get_current(ForecastKind.SOLAR_GENERATION) is model
    assert registry.get_current_metrics(ForecastKind.SOLAR_GENERATION) == {"solar_mae_pct": 4.2}


def test_register_logs_a_real_mlflow_run_with_params_and_metrics(tmp_path):
    db_path = tmp_path / "mlflow.db"
    tracking_uri = f"sqlite:///{db_path}"
    registry = MLflowModelRegistry(tracking_uri=tracking_uri, experiment_name="test-forecast")
    model = SolarBaseline()

    registry.register(model, {"solar_mae_pct": 4.2})

    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name("test-forecast")
    assert experiment is not None

    runs = client.search_runs([experiment.experiment_id])
    assert len(runs) == 1
    run = runs[0]
    assert run.data.params["model_name"] == "solar-baseline"
    assert run.data.params["kind"] == ForecastKind.SOLAR_GENERATION.value
    assert run.data.metrics["solar_mae_pct"] == 4.2


def test_register_creates_a_model_registry_version(tmp_path):
    db_path = tmp_path / "mlflow.db"
    tracking_uri = f"sqlite:///{db_path}"
    registry = MLflowModelRegistry(tracking_uri=tracking_uri, experiment_name="test-forecast")

    registry.register(SolarBaseline(), {"solar_mae_pct": 4.2})
    registry.register(SolarBaseline(), {"solar_mae_pct": 3.9})

    client = MlflowClient(tracking_uri=tracking_uri)
    versions = client.search_model_versions("name='solarops-solar_generation'")
    assert len(versions) == 2
