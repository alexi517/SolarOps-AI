# SolarOps AI

Safe, auditable AI control plane for solar energy assets.

> The AI owns reasoning. The Control Plane owns execution. The AI never touches
> hardware directly.

This repository follows the blueprint in `docs/08-domain-driven-design-spec.md`.

## Running the whole platform

`docker compose up` brings up the API wired to real Redis/Postgres/MLflow
(add `--profile monitoring` for Prometheus + Grafana too). See
[`DEPLOYMENT.md`](DEPLOYMENT.md) for the full run command, URLs, and what's
still in-memory even in this mode.

For a local, no-Docker loop: `python scripts/run_api.py` (API on
`127.0.0.1:8000`) and `streamlit run dashboard/app.py` (operator UI on
`127.0.0.1:8501`) against the in-memory/fake adapters every test also uses.

## Architecture

A bounded context per reasoning/execution concern (Doc 8), wired together at
one composition root. Only Execution ever drives hardware, and only after a
command clears Safety's independent gates — Forecast, Anomaly, and Decision
reason but never issue commands (ADR-010). Every dependency below is enforced
by `import-linter`, not just convention — `lint-imports` checks 9 contracts
(e.g. "Forecast may only depend on the shared kernel and Telemetry") on every
run, not just at review time.

```
src/solarops/
├── shared_kernel/    # typed IDs, physical value objects, DomainEvent, Clock port —
│                      # the only thing every other context is allowed to import
├── simulation/       # the Digital Twin — a physics-based solar/battery/inverter/grid
│                      # simulator standing in for real hardware
├── telemetry/        # ingests readings, tracks the current EnergyState (Layer 1 state store)
├── forecast/         # Solar Generation / Building Load / Battery SOC forecasting —
│                      # reasons only, never issues commands
├── anomaly/          # rule / statistical / Isolation-Forest fault detection —
│                      # reasons only, never issues commands
├── decision/         # RuleBasedOptimiser — ranks recommendations; never touches the
│                      # twin or issues commands
├── safety/           # PolicyValidator + SafetyValidator + RiskAssessor — the
│                      # independent gates every command must clear
├── execution/        # the Command / ApprovalRequest aggregates and the full
│                      # policy -> safety -> risk -> approval -> dispatch -> verify pipeline
├── observability/    # Prometheus metrics (CESF §17, Doc 6 §11)
├── workflow/         # LangGraph graph wiring Telemetry -> Decision
├── platform/         # the composition root — wires every context into one
│                      # SystemComposition; real-vs-in-memory adapter selection lives here
└── api/               # the FastAPI edge — the only way into the running system from outside
```

Two more pieces sit outside `src/solarops/`, deliberately:
- **`dashboard/`** — a Streamlit operator UI. It never imports `solarops`
  (checked: `grep -rn "solarops" dashboard/` stays at zero real imports) — it
  only ever talks to the API over HTTP, same as any other client would. See
  `dashboard/README.md`.
- **`monitoring/`** — Prometheus scrape configs plus two provisioned Grafana
  dashboards (Operations, AI & Safety). See `monitoring/README.md`.

`scripts/` holds one runnable entry point per context (`run_simulator.py`,
`run_telemetry_pipeline.py`, `run_forecast_training_and_evaluation.py`,
`run_anomaly_detection_evaluation.py`, `run_decision_pipeline.py`,
`run_execution_pipeline_happy_path.py` / `_unsafe.py`, `run_api.py`) —
useful for exercising one context in isolation without the full API.

`docs/` has the spec this was built from (`08-domain-driven-design-spec.md`)
plus the brief for every phase (`phase5-...` through `phase8-...`) — each
brief is the actual source of truth for why a given phase's code looks the
way it does.

## API surface

Full interactive docs at `/docs` once the API is running. Every endpoint is
open except the three that mutate a pending approval, which require an
`X-API-Key` header (Phase 7a brief §3 — a minimal demo-grade check, not full
RBAC; see the `TODO(auth-rbac)` in `api/dependencies.py`).

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | — | liveness |
| GET | `/metrics` | — | Prometheus exposition format |
| GET | `/sites/{site_id}/state` | — | current `EnergyState` |
| GET | `/sites/{site_id}/forecasts` | — | whatever's currently registered per kind |
| GET | `/sites/{site_id}/anomalies` | — | recent detected anomalies |
| GET | `/sites/{site_id}/recommendations` | — | current ranked recommendations |
| POST | `/sites/{site_id}/decision-cycle` | — | refresh telemetry, reason, run the top recommendation through the execution pipeline |
| GET | `/sites/{site_id}/commands` | — | command history for a site |
| GET | `/commands/{command_id}` | — | full command detail, every gate outcome |
| GET | `/commands/{command_id}/audit` | — | that command's audit trail |
| GET | `/sites/{site_id}/approvals/pending` | — | commands currently awaiting approval |
| POST | `/approvals/{approval_id}/approve` | ✓ | approve a pending command |
| POST | `/approvals/{approval_id}/reject` | ✓ | reject a pending command |
| POST | `/approvals/{approval_id}/modify` | ✓ | approve with modified params |

## Status and known gaps

Every phase brief in `docs/` (`phase5-...` through `phase8-...`) has landed —
simulation through execution, the API, the dashboard, monitoring, and
Dockerization are all built, tested, and wired at the composition root
(`platform/api_composition.py`).

Gaps found along the way were tracked rather than quietly worked around:

- **`docs/deferred-items.md`** — known accuracy/detection-latency gaps (e.g.
  Battery Overheating recall short of target; Load/Battery-SOC forecasts
  never cleared their accuracy gate, so Decision reasons around their
  absence rather than pretending they exist) and one training/evaluation
  data-generation issue affecting the ML detector/forecaster numbers.
- **`DEPLOYMENT.md`** — which aggregates run on real Redis/Postgres/MLflow
  under Docker vs. which are marked seams still in-memory (`Command` and
  `ApprovalRequest` — reconstructing their state machines from a persisted
  snapshot needs transition-replay logic not yet built).
- **`monitoring/README.md`** — one metric
  (`solarops_commands_auto_rejected_by_confidence_total`) is declared but
  permanently reads 0, since no code path currently auto-rejects on
  confidence alone.

## Design notes

- **Typed IDs.** A `SiteId` is never equal to an `AssetId`, even with the same
  string — mixing identifiers is a type error, not a silent bug.
- **No primitive obsession.** Physical quantities are self-validating value
  objects. `StateOfCharge` can only exist in `[0, 100]`; `Power + Energy` is a
  `TypeError`.
- **One home for the risk policy.** `RiskLevel` carries the CESF §8 policy
  (auto-execute / notify / manual approval / auto-reject) as properties.
- **Deterministic time.** The domain depends on a `Clock` port; `FixedClock`
  lets tests and the Digital Twin control time exactly.
- **Fail-safe is a first-class error.** `FailSafeTriggered` encodes ADR-012.
- **Reasoning never touches hardware.** Forecast/Anomaly/Decision only ever
  read `EnergyState`; only Execution's pipeline (via `HardwareInterface`) can
  dispatch a command, and only after Safety has signed off.

## Running the tests

```bash
pip install -e ".[dev]"
pytest
```

Architecture rules are enforced with import-linter:

```bash
lint-imports
```

Lint:

```bash
ruff check .
```

The dashboard has its own extra and its own test suite (`tests/dashboard/`,
run against a real API instance headlessly via Streamlit's `AppTest`):

```bash
pip install -e ".[dashboard]"
pytest tests/dashboard
```
