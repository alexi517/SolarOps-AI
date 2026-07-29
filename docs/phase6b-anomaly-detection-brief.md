# Phase 6b Brief — Anomaly Detection Engine

**For:** Claude Code (or manual execution)
**Scope:** Anomaly detection only. Optimisation engine (6c) follows.
**Source of truth:** the architecture documents. Behaviour that the documents
specify is used as-is; the one genuine design fork is surfaced in section 6, not
invented.

**IMPORTANT — save this file to `docs/phase6b-anomaly-detection-brief.md` before
building.** Read it alongside `docs/08-domain-driven-design-spec.md` and
`docs/06-AI-Evaluation-Framework.md` (§5 is the anomaly evaluation spec).

## 0. Principles to preserve
- Anomaly detection **reasons only** — it observes and reports; it never issues
  commands or touches the twin. (See section 6 for the one decision to confirm.)
- Every detection is **explainable** and **observable** (emits an event, carries
  its evidence).
- Detectors are **pluggable** behind one interface — rules, statistical baseline,
  and Isolation Forest are interchangeable and composable.
- **No detector is released** unless it passes the Document 6 §5 gate (section 5).

## 1. Where it lives
A new bounded context: `src/solarops/anomaly/` (mirrors the Forecast context's
shape). It reads `EnergyState`/history (Open Host Service from Telemetry) and
raises `Anomaly`/`Alert`. Import rule: `solarops.anomaly` may depend on
`shared_kernel` and `telemetry` only. Confirm with `lint-imports`.

## 2. The six anomaly types to detect (from the PRD/ASDS task list)
Battery overheating, sensor failure, communication loss, unexpected load spikes,
inverter faults, grid instability.

## 3. Domain (`anomaly/domain/`)
- `anomaly.py` — `Anomaly` aggregate root / VO. **Every anomaly carries exactly
  these fields** (per the task list): `anomaly_type`, `severity`, `confidence`,
  `affected_asset`, `supporting_evidence`, `recommended_action`.
- `anomaly_type.py` — enum of the six types.
- `severity.py` — severity enum (e.g. INFO / WARNING / CRITICAL) — keep the scale
  in config so it's tunable.
- `detection.py` — a `Detection` VO (one detector's raw finding) vs. the unified
  `Anomaly` (after scoring/merging).
- `ports.py` — `AnomalyDetector` (Protocol: `detect(state, history) -> list[Detection]`),
  `AnomalyRepository`, `AlertPublisher`.
- `events.py` — `AnomalyDetected`, `AlertRaised`.

## 4. Application (`anomaly/application/`)
- Detectors, each implementing `AnomalyDetector`:
  - `rule_detector.py` — deterministic threshold rules (e.g. battery temp over
    limit, grid status not connected, inverter status in a fault mode). Thresholds
    in config, never hardcoded.
  - `statistical_detector.py` — statistical baseline (e.g. rolling mean/stddev;
    a reading beyond N sigma is anomalous — for load spikes, sensor dropouts).
  - `isolation_forest_detector.py` — the first ML detector (scikit-learn
    IsolationForest), trained on twin-generated normal-operation history.
- `scoring_service.py` — **unified anomaly scoring:** runs all detectors, merges
  their `Detection`s into `Anomaly`s, assigns `severity` and `confidence`, and
  attaches `supporting_evidence` and a `recommended_action`. This is where the six
  required fields are populated.
- `explanation.py` — builds the human-readable root-cause explanation /
  `recommended_action` text.
- `evaluation/anomaly_evaluator.py` — the Document 6 §5 gate (section 5).

## 5. Evaluation & release gate (from Document 6 §5)
- **Fault scenarios:** battery overheating, grid outage, sensor failure, inverter
  fault, communication loss (reuse the twin benchmark scenarios / fault injection
  from the simulation context; add any missing).
- **Metrics:** Precision, Recall, F1, False Positive Rate, Detection Latency.
- **Release targets (the gate, tunable in config):** Precision > 0.90,
  Recall > 0.90, Detection Delay < 10 s.
- **The gate:** a detector configuration is accepted only if it meets those
  targets across the fault scenarios and introduces no regression vs the previous
  release. Same choke-point pattern as 6a — one place decides pass/fail.
- **Observability (§13):** log metrics/versions to MLflow; traces to Langfuse.

## 6. The one design fork — CONFIRM before building
What happens when an anomaly is detected?
- **Option A (DEFAULT — build this):** *detect and alert only.* The anomaly is
  recorded, scored, and published as an `Alert` (to the Observability context /
  a log). Anomaly detection stays a pure observer, fully decoupled from control.
- **Option B (enhancement — do NOT build unless the ASDS/PRD calls for it):**
  anomalies also become inputs to the decision engine (6c), so e.g. "battery
  overheating" can drive a "stop charging" recommendation. More powerful, but it
  couples anomaly detection into the decision loop.

Build **Option A** now. Leave a clearly-marked seam where Option B would attach
(the `AlertPublisher`/event stream is that seam). If the documents specify
Option B, stop and flag it before wiring it.

## 7. Training data note
Same as 6a: the Isolation Forest trains on twin-generated normal-operation
history via a `HistoricalDataSource`, wired at the platform composition root. The
anomaly context must not import `simulation`.

## 8. Definition of done (6b)
- The six anomaly types are detectable; every `Anomaly` carries all six required
  fields.
- Rule, statistical, and Isolation-Forest detectors all implement one interface
  and are combined by the scoring service.
- The Document 6 §5 evaluation gate runs against the fault scenarios, checks the
  targets, and enforces no-regression; results logged to MLflow.
- Detection is alert-only (Option A), with the seam for Option B marked.
- End-to-end script: inject each fault into the twin, show it detected with
  severity/confidence/evidence/recommended-action, and print an evaluation report.
- `pytest`, `ruff`, `lint-imports` green, with the new anomaly import contract.
- **Report:** files created, a plain-English summary of how an anomaly is detected
  and scored, the honest evaluation numbers (which detectors passed/failed), and
  test results. Stop before 6c.