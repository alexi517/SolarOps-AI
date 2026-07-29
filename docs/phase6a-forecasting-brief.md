# Phase 6a Brief — Forecasting Engine

**For:** Claude Code (or manual execution)
**Context:** Forecast (`src/solarops/forecast/`) — a *supporting* context.
**Scope:** Forecasting only. Anomaly detection (6b) and optimisation (6c) follow.
**Status:** Fully specified. Behavioural defaults DECIDED (section 5); evaluation
gate now DECIDED from Document 6 (section 6). No open gaps — build it.

Keep every threshold, feature, horizon, and target in configuration so behaviour
is swappable without code changes.

## 0. Principles to preserve
- Forecasters **reason only** — predictions, never commands.
- Every forecast is **explainable** (carries model + version + confidence) and
  **observable** (emits an event; logs to MLflow + Langfuse).
- **Model-swappable:** Prophet / XGBoost / LightGBM / LSTM all implement one
  interface, interchangeable without touching anything downstream.
- **No model is released** unless it passes the Document 6 evaluation gate.

## 1. Deliverables (checklist)
- Solar Generation, Building Load, and Battery State-of-Charge forecast services
- One common forecasting interface
- Feature engineering pipeline
- Training pipeline
- Evaluation pipeline (with the Document 6 gate)
- Model registry integration (MLflow, in-memory fallback for tests)
- Versioned inference API (every forecast tagged with the model version)
- Unit and integration tests

## 2. Domain (`forecast/domain/`)
- `forecast.py` — `Forecast` aggregate root: `ForecastId`, `site_id`,
  `kind: ForecastKind`, `horizon`, ordered `ForecastPoint` series, `ForecastMetadata`. Immutable.
- `forecast_point.py` — VO: `timestamp`, `value` (`Power` for solar/load,
  `StateOfCharge` for battery), optional prediction interval.
- `forecast_metadata.py` — VO: `model_name`, `model_version`, `generated_at`,
  `horizon`, `resolution`, confidence.
- `forecast_kind.py` — enum: `SOLAR_GENERATION`, `BUILDING_LOAD`, `BATTERY_SOC`.
- `ports.py`:
  - `ForecastModel` (Protocol) — `predict(features, horizon) -> list[ForecastPoint]`; carries `name`, `version`, `kind`.
  - `TrainableModel` (Protocol) — `fit(training_set) -> FitResult`. Baselines implement `ForecastModel` only; ML models implement both.
  - `ForecastRepository`, `HistoricalDataSource`, `ModelRegistry`, `BenchmarkScenarioSource`.
- `events.py` — `ForecastGenerated`.

## 3. Application (`forecast/application/`)
- `feature_engineering.py` — turns raw history + current `EnergyState` into the
  per-kind feature sets in section 5.
- `forecasting_service.py` — shared orchestration: features → `model.predict` →
  build `Forecast` → persist → emit `ForecastGenerated`.
- `SolarGenerationForecaster`, `BuildingLoadForecaster`, `BatterySocForecaster`.
- `training/training_service.py` — fit → evaluate (section 6) → register the
  version **only if it passes the gate**; `retrain()` hook (drift = later seam).
- `evaluation/forecast_evaluator.py` — the Document 6 forecast metrics and gate.

## 4. Infrastructure (`forecast/infrastructure/`)
- `models/`:
  - A deterministic **baseline** per kind (no training) — the V1 default so the
    context works end-to-end before any ML.
  - **`XGBoostForecaster`** — first ML model, proves the interface.
    `ProphetForecaster`, `LightGBMForecaster`, `LSTMForecaster` — class shells
    against the same interface, not implemented yet.
- `model_registry.py` — MLflow-backed, in-memory fallback for tests.
- `in_memory_forecast_repository.py`.
- `historical_data_source.py` — see section 7 (training data).
- `config.py` — `ForecastConfig` (pydantic-settings): horizons, resolution,
  per-kind features, SOC energy-balance params, **and the evaluation targets from
  section 6**. All behaviour lives here, not hardcoded.

## 5. Behavioural defaults (DECIDED — externalise to `ForecastConfig`)
- **Horizons:** 15 min, 30 min, 1 h, 6 h. Default series resolution 15-min out to
  6 h; the named horizons are the evaluation checkpoints.
- **Solar inputs:** historical solar output, irradiance, cloud cover, temperature,
  time of day, seasonality.
- **Load inputs:** historical demand, hour of day, day of week, occupancy
  profile, calendar effects.
- **Battery SOC:** deterministic **energy-balance** model in v1 — project SOC from
  forecasted generation minus forecasted demand applied to current SOC with
  round-trip efficiency. Behind the same `ForecastModel` interface for later ML
  replacement.

## 6. Evaluation & release gate (DECIDED — from Document 6)
- **Metrics:** MAE, RMSE, MAPE, R² (§4).
- **Release targets (the gate):** Solar MAE < 8%; Load MAPE < 10%; Battery SOC
  error < 5% (§4). Put these in `ForecastConfig` so they're tunable.
- **Benchmark scenarios (§9):** evaluate against six standard Digital-Twin
  scenarios — Clear Day, Cloud Front, Evening Peak, Grid Outage, Battery
  Overheating, Sensor Failure. Reuse the simulation `Scenario` aggregate; add any
  of the six that don't already exist as twin scenarios. (Clear Day / Cloud Front
  / Evening Peak are the primary forecast-accuracy scenarios; the others run for
  robustness.)
- **The gate (ADR-009, §15):** a model is registered/released **only if** it
  meets the targets on the benchmark scenarios **and** introduces **no regression**
  vs the previously released version (§10 — compare current vs previous from the
  registry).
- **Observability (§13):** log model versions, metrics, hyperparameters to MLflow;
  traces to Langfuse.
- **Continuous evaluation (§14):** the gate must be invocable from CI (run on PR /
  before merge / before deploy / after retrain). Full CI wiring is Phase 7 — just
  make the gate a callable entry point now.

## 7. Training data note
- The only source today is the Digital Twin — generate synthetic history by
  running the twin over many simulated days and train on that. Mark it clearly as
  the interim source; do **not** import `simulation` into the forecast context
  (feed it via `HistoricalDataSource`, wired at platform).

## 8. Import rules
- New contract: `solarops.forecast` may depend on `shared_kernel` and `telemetry`.
- Update the Decision contract: Decision may now also depend on `forecast`.
- The evaluation harness that runs twin scenarios spans simulation + forecast — it
  is orchestration and lives at the platform composition root, not inside the
  forecast context.
- Confirm all with `lint-imports`.

## 9. Definition of done (6a)
- Three forecasters produce `Forecast` aggregates through one swappable
  `ForecastModel` interface, deterministic baselines working end-to-end.
- `XGBoostForecaster` trains, evaluates against the Document 6 gate, and registers
  only on pass — proving both the swap and the gate.
- Feature-engineering, training, and evaluation pipelines exist; MLflow registry
  wired (in-memory fallback for tests); forecasts carry their model version.
- Evaluation runs the six benchmark scenarios, checks the targets, and enforces
  no-regression against the previous release.
- End-to-end script produces all three forecasts (all horizons) from real twin
  data and prints an evaluation report.
- `pytest`, `ruff`, `lint-imports` green, with the contract updates.
- **Report:** files created, a plain-English summary of the forecast flow and the
  evaluation gate, proof the model interface is swappable, and test results.
  Stop before 6b.