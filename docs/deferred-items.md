# Deferred Items

Known gaps surfaced during development, deliberately not fixed in the pass
that found them — tracked here rather than silently worked around.

## 1. Battery Overheating recall misses the 0.90 target (~70s detection latency)

**Found:** Phase 6b (Anomaly Detection Engine).

`RuleDetector`'s Battery Overheating check is correct in principle
(`battery_temp > threshold`), but the Battery Overheating fault scenario's
recall came out to 0.77 against a 0.90 target. The twin's thermal ramp
genuinely takes ~70 seconds to cross the configured overheat threshold after
the fault is injected — this is real simulated physics, not a detector bug —
but the Document 6 §5 detection-delay target (<10s) doesn't leave room for
that ramp. Per the cleanup pass (per-check gating,
`docs/phase6b-cleanup-per-check-gating.md`), Battery Overheating is left
honestly uncovered rather than passed by loosening the threshold.

**Revisit:** either widen the detection window/threshold specifically for
thermal-ramp faults (a slower-onset fault category may warrant its own
latency target), or accept a lower threshold value that fires earlier in the
ramp. Needs a decision on the target itself, not just the code.

## 2. ML detectors trained and evaluated on divergent twin runs

**Found:** Phase 6b (`IsolationForestDetector`); the same root cause likely
also affects Phase 6a's `XGBoostForecaster` numbers.

Training data comes from an independently-constructed `DigitalTwin` instance
(via `TwinHistoricalDataSource`), while evaluation runs against a *different*
twin instance (the benchmark/fault scenario's own twin). Both use the same
random seed, but each twin's stochastic sub-models (weather, building load)
evolve from their own construction — tick count since instantiation, not
absolute simulated calendar time — so two independently-built twins don't
share a trajectory even at the "same" nominal timestamp. This showed up
concretely as `IsolationForestDetector` self-flagging real telemetry as
anomalous: its training baseline's solar/inverter output distribution
differed systematically from the evaluation scenario's, purely because they
came from different twin instances.

**Revisit:** before trusting any ML accuracy number (Isolation Forest here,
XGBoost in 6a), train and evaluate against a shared dataset — either draw
both from the same continuous twin run (train on an earlier segment,
evaluate on a later one), or change the twin's stochastic sub-models to seed
from absolute simulated time rather than construction order, so independently
-built twins at the same nominal moment actually agree.

## 3. Only the Solar forecast is production-registered — Decision reasons without Load/Battery-SOC forecasts

**Found:** Phase 6a (`ForecastEvaluator` gate results); load-bearing on Phase
6c (`RuleBasedOptimiser`).

The Load and Battery-SOC baseline forecasters never cleared the Document 6 §4
accuracy gate in 6a (39-47% MAPE and 14-16% MAE respectively, against 10%/5%
targets), so `ModelRegistry` only ever has a Solar model registered. The v1
rule engine (Phase 6c) was built to degrade gracefully around this: it reads
`EnergyState` (current load, current SOC) directly wherever it would
otherwise have used those forecasts, and states so explicitly in every
recommendation's `evidence` ("load forecast unavailable; using current load
only", "battery SOC forecast unavailable; using current SOC only") — never
silently substituting or fabricating a forecast it doesn't have.

**Revisit:** once Load and/or Battery-SOC forecasting models clear the gate
(new model types, richer features, or fixed training data per item 2 above),
`RuleBasedOptimiser` can start reading `context.forecast_for(...)` for those
kinds too — no interface change needed, `DecisionContext` already carries
whatever's registered.
