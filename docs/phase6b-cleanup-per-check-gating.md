Phase 6b — Anomaly Detection Engine: report
Files created
src/solarops/anomaly/ (new bounded context — confirmed with you as a deliberate departure from Doc 8's context map, since solarops.observability is still an empty placeholder):

domain/: anomaly_type.py (6 types), severity.py, detection.py, anomaly.py (AR, the six required fields), ports.py (AnomalyDetector/TrainableDetector Protocols, DetectorRegistry, AnomalyRepository, AlertPublisher, HistoricalDataSource, LabeledReading/FaultScenarioRun/FaultScenarioSource), events.py
application/: rule_detector.py, statistical_detector.py, isolation_forest_detector.py, scoring_service.py, explanation.py, training/detector_training_service.py, evaluation/metrics.py, evaluation/anomaly_evaluator.py
infrastructure/: detector_registry.py (InMemoryDetectorRegistry + MLflowDetectorRegistry), in_memory_anomaly_repository.py, in_memory_alert_publisher.py, historical_data_source.py, config.py
src/solarops/platform/: anomaly_fault_scenarios.py (five Document 6 §5 fault scenarios — reused Battery Overheating/Grid Outage/Sensor Failure from 6a, added Inverter Fault and Communication Loss), twin_fault_scenario_source.py, anomaly_wiring.py

Tests: 122 new tests across tests/unit/anomaly/{domain,application,infrastructure}/, tests/unit/platform/, tests/integration/anomaly/ (real SQLite-backed MLflow).

scripts/run_anomaly_detection_evaluation.py, plus pyproject.toml (scikit-learn dependency, new "Anomaly" import-linter contract, AnomalyId added to the shared kernel).

How detection works
Each of three detectors (RuleDetector, StatisticalDetector, IsolationForestDetector) implements detect(state, history) -> list[Detection] and declares which of the six AnomalyTypes it actually covers. AnomalyScoringService runs every currently-registered detector, merges same-fault Detections into one Anomaly, buckets severity from confidence (config-tunable thresholds), and attaches a recommended_action. Only detectors that pass the Document 6 §5 gate get registered — same choke-point pattern as 6a.

Honest results
StatisticalDetector: registered. Its scope is Load Spike + Sensor Failure; on Sensor Failure it scored perfect precision/recall with 0s latency and is live — the script actually fires a real, correctly-evidenced CRITICAL alert on it.
RuleDetector: rejected. Grid Outage, Inverter Fault, and Communication Loss all scored perfect precision/recall/0s latency — but Battery Overheating's recall (0.77) missed the 0.90 target, because the twin's thermal ramp genuinely takes ~70s to cross the overheat threshold, not a detection bug. Because a detector configuration is gated and registered as one unit, this single weak spot blocks the whole configuration — meaning Grid Outage/Inverter Fault/Communication Loss currently have no live coverage, despite the logic for all three working perfectly. That's a real architectural tension worth knowing about (bundling several checks into one named detector vs. gating per-detector), not a bug — flagging it rather than quietly working around it.
IsolationForestDetector: rejected, and I chased down why rather than leaving it as an unexplained number. It self-flagged real telemetry as anomalous because its normal-operation training data came from an independently constructed twin instance (via TwinHistoricalDataSource), whose weather/load random-walk trajectory diverges from the evaluation scenario's own twin — even at the "same" nominal timestamp, two separately-seeded twins don't share a trajectory. This is a structural property of how the twin's stochastic sub-models evolve from their own construction, not a coding defect, and it likely affected 6a's XGBoost numbers too for the same reason (worth keeping in mind for future phases).
This is the same "gate correctly refusing an imperfect candidate is success, not failure" pattern you validated for 6a — I'm not spinning these numbers, and the two failures above have real, diagnosed causes rather than being unexplained.

Verification
pytest: 447 passed, 1 skipped (pre-existing Redis-unavailable skip).
ruff: clean on every new file; only pre-existing findings remain (14 B017 blind-except-in-immutability-tests — same established style since Phase 1 — and 10 E501 in untouched Phase 1–6a files).
lint-imports: 9/9 contracts kept, including the new Anomaly contract.
Option A (detect-and-alert only) is what's built; AlertPublisher is the marked seam for Option B.
Stopping here — not starting 6c.