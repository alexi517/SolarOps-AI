from datetime import UTC, datetime

from solarops.anomaly.application.evaluation.anomaly_evaluator import AnomalyEvaluator
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.detection import Detection
from solarops.anomaly.domain.ports import FaultScenarioRun, LabeledReading
from solarops.anomaly.infrastructure.config import AnomalyConfig
from solarops.shared_kernel import AssetId, SiteId
from solarops.telemetry.domain.energy_state import EnergyState

from ...telemetry.domain.test_telemetry import make_telemetry

SITE_ID = SiteId("SITE-1")
NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
ASSET = AssetId("ASSET-grid-1")


def make_state() -> EnergyState:
    return EnergyState.from_telemetry(
        make_telemetry(site_id=SITE_ID, timestamp=NOW), any_asset_offline=False
    )


def make_run(
    name: str,
    expected_type: AnomalyType,
    normal_ticks: int,
    fault_ticks: int,
    tick_seconds: float = 5.0,
) -> FaultScenarioRun:
    readings = [
        LabeledReading(state=make_state(), is_anomalous=False, expected_type=None)
        for _ in range(normal_ticks)
    ] + [
        LabeledReading(state=make_state(), is_anomalous=True, expected_type=expected_type)
        for _ in range(fault_ticks)
    ]
    return FaultScenarioRun(
        scenario_name=name,
        expected_type=expected_type,
        readings=tuple(readings),
        tick_seconds=tick_seconds,
    )


class _FakeScenarioSource:
    def __init__(self, runs: dict[str, FaultScenarioRun]) -> None:
        self._runs = runs

    def scenario_names(self) -> list[str]:
        return list(self._runs.keys())

    def run(self, scenario_name: str) -> FaultScenarioRun:
        return self._runs[scenario_name]


def _detection(anomaly_type: AnomalyType) -> Detection:
    return Detection(
        anomaly_type=anomaly_type, confidence=1.0, affected_asset=ASSET,
        evidence="x", detector_name="fake", detector_version="v1", detected_at=NOW,
    )


class _FiresFromIndex:
    name = "fires-from-index"
    version = "v1"
    supported_types = frozenset({AnomalyType.GRID_INSTABILITY})

    def __init__(
        self, fire_from_index: int, anomaly_type: AnomalyType = AnomalyType.GRID_INSTABILITY
    ) -> None:
        self._fire_from_index = fire_from_index
        self._anomaly_type = anomaly_type

    def detect(self, state, history) -> list[Detection]:  # noqa: ANN001
        if len(history) >= self._fire_from_index:
            return [_detection(self._anomaly_type)]
        return []


class _NeverFires:
    name = "never-fires"
    version = "v1"
    supported_types = frozenset({AnomalyType.GRID_INSTABILITY})

    def detect(self, state, history) -> list[Detection]:  # noqa: ANN001
        return []


class _AlwaysFires:
    name = "always-fires"
    version = "v1"
    supported_types = frozenset({AnomalyType.GRID_INSTABILITY})

    def detect(self, state, history) -> list[Detection]:  # noqa: ANN001
        return [_detection(AnomalyType.GRID_INSTABILITY)]


class _PartialDetector:
    """Fires correctly on GRID_INSTABILITY, never on INVERTER_FAULT — the
    per-type-gating fixture: one detector, two supported types, only one
    genuinely works."""

    name = "partial-detector"
    version = "v1"
    supported_types = frozenset({AnomalyType.GRID_INSTABILITY, AnomalyType.INVERTER_FAULT})

    def detect(self, state, history) -> list[Detection]:  # noqa: ANN001
        if len(history) >= 5:
            return [_detection(AnomalyType.GRID_INSTABILITY)]
        return []


def test_immediate_correct_detection_passes():
    config = AnomalyConfig(
        precision_target=0.9, recall_target=0.9, detection_delay_target_seconds=10.0
    )
    run = make_run("S1", AnomalyType.GRID_INSTABILITY, normal_ticks=5, fault_ticks=10)
    source = _FakeScenarioSource({"S1": run})
    evaluator = AnomalyEvaluator(source, config)

    report = evaluator.evaluate(_FiresFromIndex(fire_from_index=5), previous_metrics=None)

    assert report.scenario_results[0].passed is True
    assert report.covered_types == {AnomalyType.GRID_INSTABILITY}
    assert report.scenario_results[0].detection_latency_seconds == 0.0


def test_never_detecting_fails_on_recall():
    config = AnomalyConfig(precision_target=0.9, recall_target=0.9)
    run = make_run("S1", AnomalyType.GRID_INSTABILITY, normal_ticks=5, fault_ticks=10)
    source = _FakeScenarioSource({"S1": run})
    evaluator = AnomalyEvaluator(source, config)

    report = evaluator.evaluate(_NeverFires(), previous_metrics=None)

    assert report.covered_types == frozenset()
    assert report.uncovered_types == {AnomalyType.GRID_INSTABILITY}
    assert report.scenario_results[0].recall == 0.0


def test_always_firing_fails_on_precision_via_false_positives():
    config = AnomalyConfig(precision_target=0.9, recall_target=0.9)
    run = make_run("S1", AnomalyType.GRID_INSTABILITY, normal_ticks=5, fault_ticks=10)
    source = _FakeScenarioSource({"S1": run})
    evaluator = AnomalyEvaluator(source, config)

    report = evaluator.evaluate(_AlwaysFires(), previous_metrics=None)

    assert report.covered_types == frozenset()
    assert report.scenario_results[0].precision < 0.9


def test_slow_detection_fails_on_latency_target():
    config = AnomalyConfig(
        precision_target=0.9, recall_target=0.9, detection_delay_target_seconds=10.0
    )
    run = make_run(
        "S1", AnomalyType.GRID_INSTABILITY, normal_ticks=5, fault_ticks=10, tick_seconds=5.0
    )
    source = _FakeScenarioSource({"S1": run})
    evaluator = AnomalyEvaluator(source, config)

    # fault starts at index 5; firing from index 8 -> latency = 3 ticks * 5s = 15s > 10s target
    report = evaluator.evaluate(_FiresFromIndex(fire_from_index=8), previous_metrics=None)

    assert report.scenario_results[0].detection_latency_seconds == 15.0
    assert report.covered_types == frozenset()


def test_regression_against_previous_release_blocks_that_type():
    config = AnomalyConfig(precision_target=0.5, recall_target=0.5)
    run = make_run("S1", AnomalyType.GRID_INSTABILITY, normal_ticks=5, fault_ticks=10)
    source = _FakeScenarioSource({"S1": run})
    evaluator = AnomalyEvaluator(source, config)

    previous_metrics = {AnomalyType.GRID_INSTABILITY: {"recall": 1.5}}
    detector = _FiresFromIndex(fire_from_index=5)
    report = evaluator.evaluate(detector, previous_metrics=previous_metrics)

    assert report.scenario_results[0].regressed is True
    assert report.covered_types == frozenset()


def test_metrics_by_type_captures_only_covered_types():
    config = AnomalyConfig(precision_target=0.5, recall_target=0.5)
    run = make_run("S1", AnomalyType.GRID_INSTABILITY, normal_ticks=5, fault_ticks=10)
    source = _FakeScenarioSource({"S1": run})
    evaluator = AnomalyEvaluator(source, config)

    report = evaluator.evaluate(_FiresFromIndex(fire_from_index=5), previous_metrics=None)

    assert report.metrics_by_type == {
        AnomalyType.GRID_INSTABILITY: {"precision": 1.0, "recall": 1.0}
    }


def test_partial_pass_covers_only_the_type_that_genuinely_works():
    config = AnomalyConfig(precision_target=0.9, recall_target=0.9)
    runs = {
        "Grid": make_run("Grid", AnomalyType.GRID_INSTABILITY, normal_ticks=5, fault_ticks=10),
        "Inverter": make_run(
            "Inverter", AnomalyType.INVERTER_FAULT, normal_ticks=5, fault_ticks=10
        ),
    }
    source = _FakeScenarioSource(runs)
    evaluator = AnomalyEvaluator(source, config)

    report = evaluator.evaluate(_PartialDetector(), previous_metrics=None)

    assert report.covered_types == {AnomalyType.GRID_INSTABILITY}
    assert report.uncovered_types == {AnomalyType.INVERTER_FAULT}
