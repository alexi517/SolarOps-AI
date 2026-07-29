"""Phase 6b end-to-end: train, gate, and detect — the pluggable-detector proof.

1. Register the rule and statistical detectors (no training needed) through
   the Document 6 §5 evaluation gate.
2. Train ``IsolationForestDetector`` on twin-generated normal-operation
   history, and run it through the same gate.
3. Inject each of the five fault scenarios into a fresh twin and run
   ``AnomalyScoringService`` (using whichever detector configs the gate
   actually registered) tick by tick, showing the first ``Anomaly`` produced
   for each fault — type, severity, confidence, asset, evidence, and
   recommended action.
4. Print the honest evaluation report: which detector configs passed/failed,
   and why.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from solarops.anomaly.application.evaluation.anomaly_evaluator import (
    AnomalyEvaluator,
    EvaluationReport,
)
from solarops.anomaly.application.isolation_forest_detector import IsolationForestDetector
from solarops.anomaly.application.rule_detector import RuleDetector
from solarops.anomaly.application.scoring_service import AnomalyScoringService
from solarops.anomaly.application.statistical_detector import StatisticalDetector
from solarops.anomaly.application.training.detector_training_service import (
    DetectorTrainingService,
)
from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.infrastructure.detector_registry import InMemoryDetectorRegistry
from solarops.anomaly.infrastructure.in_memory_alert_publisher import InMemoryAlertPublisher
from solarops.anomaly.infrastructure.in_memory_anomaly_repository import (
    InMemoryAnomalyRepository,
)
from solarops.platform.anomaly_wiring import (
    build_anomaly_config,
    build_twin_fault_scenario_source,
    build_twin_historical_data_source,
)
from solarops.platform.twin_fault_scenario_source import TwinFaultScenarioSource
from solarops.shared_kernel import SiteId
from solarops.simulation.infrastructure.config import SiteConfig

SITE_ID = SiteId("site-001")


def _report_line(report: EvaluationReport) -> str:
    lines = [f"  {report.detector_name} {report.detector_version}"]
    for scenario in report.scenario_results:
        status = "LIVE" if scenario.passed else "NOT COVERED"
        latency = (
            f"{scenario.detection_latency_seconds:.1f}s"
            if scenario.detection_latency_seconds is not None
            else "never"
        )
        regression_note = " (regressed)" if scenario.regressed else ""
        lines.append(
            f"    {status:11} {scenario.expected_type.value:20} [{scenario.scenario_name}] "
            f"precision={scenario.precision:.2f} recall={scenario.recall:.2f} "
            f"fpr={scenario.false_positive_rate:.2f} latency={latency} "
            f"ran_ok={scenario.ran_ok}{regression_note}"
        )
    covered = sorted(t.value for t in report.covered_types)
    uncovered = sorted(t.value for t in report.uncovered_types)
    lines.append(f"    covered: {covered or 'none'}")
    lines.append(f"    uncovered: {uncovered or 'none'}")
    return "\n".join(lines)


def main() -> None:
    site_config = SiteConfig(site_id="site-001")
    config = build_anomaly_config(site_config)

    registry = InMemoryDetectorRegistry()
    repository = InMemoryAnomalyRepository()
    alert_publisher = InMemoryAlertPublisher()
    scoring_service = AnomalyScoringService(registry, repository, config)

    scenario_source: TwinFaultScenarioSource = build_twin_fault_scenario_source(site_config)
    evaluator = AnomalyEvaluator(scenario_source, config)
    training_service = DetectorTrainingService(evaluator, registry)

    print("=== Phase 6b: Anomaly Detection Engine - training, evaluation gate, detection ===\n")

    print("--- Registering rule and statistical detectors (no training needed) ---")
    for detector in (RuleDetector(config), StatisticalDetector(config)):
        outcome = training_service.evaluate_and_register(detector)
        print(_report_line(outcome.report))
    print()

    print("--- Training IsolationForestDetector on twin-generated normal-operation history ---")
    historical_source = build_twin_historical_data_source(site_config)
    normal_history = historical_source.get_history(
        SITE_ID,
        as_of=_reference_time(scenario_source),
        lookback=timedelta(hours=config.lookback_hours),
    )
    isolation_forest = IsolationForestDetector(config)
    if normal_history:
        outcome = training_service.train_and_evaluate(isolation_forest, normal_history)
        print(_report_line(outcome.report))
    else:
        print("  No normal-operation history available - skipping Isolation Forest training.")
    print()

    print("--- Live coverage summary (across all registered detectors) ---")
    all_covered: set[AnomalyType] = set()
    for detector in registry.get_active():
        all_covered |= registry.covered_types(detector.name)
    for anomaly_type in AnomalyType:
        status = "LIVE" if anomaly_type in all_covered else "NOT COVERED"
        print(f"  {status:11} {anomaly_type.value}")
    print()

    print(
        "--- Injecting each fault scenario, detecting with the currently-registered detectors ---"
    )
    for scenario_name in scenario_source.scenario_names():
        run = scenario_source.run(scenario_name)
        history = []
        first_anomaly = None
        for reading in run.readings:
            anomalies, events = scoring_service.score(reading.state, history)
            history.append(reading.state)
            if anomalies and first_anomaly is None:
                first_anomaly = anomalies[0]
                for anomaly in anomalies:
                    alert_publisher.publish(anomaly)

        print(f"\n  {scenario_name}:")
        if first_anomaly is None:
            print("    No anomaly detected by the currently-registered detectors.")
            continue
        print(f"    type:               {first_anomaly.anomaly_type}")
        print(f"    severity:           {first_anomaly.severity}")
        print(f"    confidence:         {first_anomaly.confidence:.2f}")
        print(f"    affected_asset:     {first_anomaly.affected_asset}")
        print(f"    supporting_evidence: {first_anomaly.supporting_evidence}")
        print(f"    recommended_action: {first_anomaly.recommended_action}")

    print(
        f"\n--- Alerts published (Option A: detect-and-alert only): "
        f"{len(alert_publisher.published)} ---"
    )


def _reference_time(scenario_source: TwinFaultScenarioSource) -> datetime:
    """A stable 'as_of' reference for pulling normal-operation training history —
    borrows the Battery Overheating scenario's start time as a timestamp only;
    ``TwinHistoricalDataSource`` builds its own fresh, fault-free twin, so
    nothing about that scenario's fault leaks into the training data.
    """
    run = scenario_source.run("Battery Overheating")
    return run.readings[0].state.timestamp


if __name__ == "__main__":
    main()
