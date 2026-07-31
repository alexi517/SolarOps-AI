# Welcome to SolarOps AI — a walkthrough for your first day

You're a new developer. Nobody's handed you a whiteboard talk — just this
file. Read it top to bottom and you should be able to open any folder in
this repo and already have a rough idea what's in it, why it's shaped that
way, and where you'd go to make your first change.

One sentence to hold onto the whole time, because every design decision in
this codebase traces back to it:

> **The AI owns reasoning. The Control Plane owns execution. The AI never
> touches hardware directly.**

## The mental model: a restaurant

We're going to use one story for the whole tour, because it makes an
otherwise abstract architecture concrete. Here it is, in full, once, so you
can refer back to it:

> SolarOps AI is a restaurant that hasn't opened for real customers yet, so
> it's rehearsing in a hyper-realistic **fake kitchen**. A **General
> Manager** opens the restaurant each morning, hiring one department at a
> time: a **stock-taker** who reports what's in the kitchen right now, a
> **sous chef** who predicts tomorrow's demand (but only gets hired if
> their predictions actually pass a tryout), a **health inspector** who
> watches for spoiled ingredients or a broken stove, a **head chef** who
> suggests what to cook next — but is never, ever allowed to touch the
> stove themselves — and an entire **approval chain** of staff (a
> rules-checker, a danger-checker, a risk-rater, sometimes the GM in
> person) who are the *only* ones allowed to actually cook something, and
> only after every one of them signs off.

Every folder below maps onto a role in that story. By the end, you'll be
able to point at any file and say which staff member it is.

## The 30,000-foot map

```
SolarOps/
├── src/solarops/     the actual system — twelve packages, one per department
├── dashboard/         the front-of-house display — a separate program, HTTP-only
├── monitoring/         Prometheus + Grafana — the "how busy are we" dashboards
├── docker/, Dockerfile, docker-compose.yml    how to run the whole restaurant for real
├── scripts/             one-off tools to test a single department by hand
├── tests/                one test folder per department, mirroring src/solarops/
└── docs/                  the original spec + one written brief per building phase
```

`src/solarops/` is where almost everything lives, split into three kinds of
folder:

| Kind | Folders | What they are, in the story |
|---|---|---|
| **Reasoning departments** — read state, never act | `telemetry/`, `forecast/`, `anomaly/`, `decision/` | The stock-taker, the sous chef, the health inspector, the head chef |
| **The one department allowed to act** | `safety/`, `execution/` | The approval chain, and the only staff allowed near the stove |
| **Foundations & wiring** | `shared_kernel/`, `simulation/`, `observability/`, `platform/`, `api/`, `workflow/` | The shared vocabulary, the fake kitchen, the silent clipboard crew, the GM, the front door, an unused side-experiment |

The single rule that makes all of this trustworthy, not just organized:
**every one of those folder boundaries is enforced by a tool
(`import-linter`), not just agreed upon.** If reasoning code ever tries to
import execution code, the build fails. That's what makes "the AI can't
execute" a fact you can verify, not a promise you have to trust.

---

## Walking the departments, in the order the restaurant actually opens

### 1. `shared_kernel/` — the common language everyone's allowed to use

Before any department can talk about anything, they need to agree on basic
nouns: what's a `SiteId`? What's a safe way to represent 5 kilowatts so
nobody accidentally adds it to 5 kilowatt-*hours*? What counts as
`RiskLevel.HIGH`?

- **`ids.py`** — typed identifiers (`SiteId`, `CommandId`, ...) so mixing up
  two different kinds of ID is a type error, not a silent bug.
- **`units.py`** — physical quantities (`Power`, `Energy`, `StateOfCharge`,
  ...) that validate themselves — a battery at 150% charge simply cannot be
  constructed.
- **`enums.py`** — the fixed vocabularies (`RiskLevel`, `GridStatus`,
  `ActionType`, `CommandStatus`, ...).
- **`events.py`** — the common shape every "something happened"
  announcement takes.
- **`exceptions.py`** — one shared family of "something's wrong" errors.
- **`clock.py`** — how code asks "what time is it?" (so tests can freeze
  time instead of depending on the real clock).

**The rule:** `shared_kernel` can depend on *nothing* else in the project.
Everything else can depend on it. It's the foundation everyone stands on.

### 2. `simulation/` — the fake kitchen

There's no real solar site yet, so this is a physics engine standing in for
one: solar panels, a battery, an inverter, the grid connection, and the
building's electrical load, each simulated with real (if simplified)
physics — sunlight follows a sine curve through the day, panels lose
efficiency as they heat up, batteries lose a little energy every time they
charge or discharge, etc.

- **`domain/digital_twin.py`** — the twin itself. Call `.tick()` and it
  advances one time-step and hands back a `SimulationState` — a snapshot
  of the whole fake site at that instant.
- **`domain/models/`** — six small files, one physics model each (solar,
  battery, inverter, grid, weather, building load). None of them know
  about each other — `DigitalTwin` is the only thing that wires them
  together (e.g. "solar output plus battery discharge both feed the
  inverter" is a single line inside `digital_twin.py`, not something any
  individual model knows).
- **`application/scenario_runner.py`** — a small, currently-**unused**
  wrapper meant for running named test scenarios. Worth knowing: nothing
  else in the codebase actually calls it — every real caller builds a
  `DigitalTwin` directly instead. Not broken, just disconnected. You'll see
  this "real but disconnected" pattern again.
- **`infrastructure/config.py`** — plain settings (`SiteConfig`,
  `SimulatorConfig`), no behavior.

**The rule:** Simulation can depend on `shared_kernel` only. It has never
heard of Telemetry, Decision, or anything else — which is exactly what
would let a real inverter replace this fake kitchen later without touching
anything downstream.

### 3. `telemetry/` — the stock-taker

Reads whatever the current source (the fake kitchen, or a real sensor
someday) reports, and keeps track of "what does the site look like right
now."

- **`domain/telemetry.py`** — one *raw* reading, unmodified.
- **`domain/energy_state.py`** — the *interpreted* current state (the raw
  reading plus two computed extras: `net_power` and `any_asset_offline`).
  This is the one object almost every other department is allowed to read.
- **`domain/ports.py`** — the Protocols (`TelemetrySource`, `StateStore`,
  `AssetRepository` — the last one has no real implementation yet, an
  honestly disclosed gap).
- **`application/ingestion_service.py`** — pulls one reading, checks if
  it's stale or faulted, builds the `EnergyState`.
- **`application/state_manager.py`** — the one read/write point for
  "current state."
- **`infrastructure/`** — `InMemoryStateStore` (a dict, used everywhere by
  default) or `RedisStateStore` (real Redis, used only when
  `SOLAROPS_ENV=production`).

### 4. `forecast/` — the sous chef, hired only after a tryout

Predicts future solar output. The tryout matters: a candidate model only
gets registered (hired) if it clears a real accuracy gate.

- **`domain/forecast.py`**, **`forecast_point.py`**, **`forecast_kind.py`**
  — the published prediction and its pieces.
- **`domain/ports.py`** — `ForecastModel` (the swappable interface every
  predictor implements), `ModelRegistry`, `HistoricalDataSource`.
- **`application/training/training_service.py`** — runs the tryout:
  evaluate first, register *only if it passes*.
- **`application/solar_generation_forecaster.py`** — asks the currently
  registered model for a live prediction.
- **`infrastructure/models/`** — the actual candidates: `solar_baseline.py`
  (simple physics-based, currently the only one hired),
  `load_baseline.py`/`battery_soc_baseline.py` (auditioned, never passed),
  `xgboost_forecaster.py` (a real ML model).

**Honest fact worth knowing on day one:** only the solar predictor is
actually registered. Load and battery-SOC forecasting were tried and never
cleared the accuracy bar — Decision was built to reason around their
absence rather than pretend they exist.

### 5. `anomaly/` — the health inspector

Watches telemetry for equipment faults.

- **`domain/detection.py`** — one detector's *raw* finding (a single
  detector run can fire several of these for the same underlying problem).
- **`domain/anomaly.py`** — the *merged*, published finding, after
  `scoring_service.py` combines every detector's raw `Detection`s into one.
- **`application/rule_detector.py`**, **`statistical_detector.py`**,
  **`isolation_forest_detector.py`** — three candidate inspectors, same
  tryout pattern as Forecast. Today, Rule and Statistical are hired;
  Isolation Forest never passed its gate.

### 6. `decision/` — the head chef

Reads current state, whatever forecast exists, and how many anomalies are
active, and suggests exactly one action. **Never touches the twin, never
builds a command** — this is ADR-010, the single most important rule in the
whole system.

- **`domain/recommendation.py`**, **`ranked_recommendations.py`** — the
  suggestion itself, and a ranked list of alternatives.
- **`domain/confidence.py`** — how sure the engine is about its own inputs.
- **`application/rule_based_optimiser.py`** — the actual v1 "brain": a
  transparent, rule-based engine (not an LLM, not a black box) that
  generates a few candidate actions, ranks them by priority, and — under
  low confidence — scales back the top candidate's own magnitude as a
  precaution.
- **`application/confidence_estimator.py`** — scores how reliable the
  current reasoning inputs actually are (fresh data? any active fault? how
  many forecasts are actually available?).

**Roadmap you should know about:** this v1 rule engine is explicitly
designed to be swapped for smarter engines later (constraint optimization,
then MPC, then RL) without Safety or Execution changing at all — the
interface was built for that future, even though only v1 exists today.

### 7. `safety/` — the approval chain's rule book (three independent judges)

Every suggested action gets checked by three separate judges, in order —
any of the first two can stop it outright.

- **`domain/command_intent.py`** — Safety's own minimal "an action being
  considered" type, invented specifically because Safety isn't allowed to
  import Execution's real `Command`.
- **`domain/policy.py`** — configurable rules an operator can change.
- **`domain/safety_limits.py`** — hard physical ceilings, **never**
  relaxed by anyone.
- **`application/policy_validator.py`** — judge 1: operational rules.
- **`application/safety_validator.py`** — judge 2: hard physical limits.
- **`application/risk_assessor.py`** — judge 3: classifies LOW / MEDIUM /
  HIGH / CRITICAL. This single classification decides everything that
  happens next: LOW/MEDIUM auto-execute, HIGH pauses for a human, CRITICAL
  is rejected outright, no exceptions.

### 8. `execution/` — the only staff allowed near the stove

The crown jewel. Owns the `Command` aggregate's entire lifecycle as a
strict state machine — there is no code path that skips a gate or moves
backward.

- **`domain/command.py`** — the `Command` aggregate. ~20 lifecycle states
  (`CREATED` → ... → `COMPLETED`, or one of several terminal failure
  states), each transition validated against the *current* state before
  it's allowed. This is what makes "100% of unsafe commands blocked" a
  structural property, not a hope.
- **`domain/approval_request.py`** — a **separate** aggregate for human
  approval (ADR-017) — kept separate so a slow human decision never holds
  the `Command`'s own consistency boundary open.
- **`application/command_intent_mapper.py`** — the one function that
  converts a real `Command` into Safety's `CommandIntent`, so those two
  types can never silently drift apart.
- **`application/execution_pipeline.py`** — the actual approval chain:
  plan → policy → safety → risk → (maybe pause for approval) → dispatch →
  verify. Every single transition gets audited through one chokepoint.
- **`infrastructure/postgres_audit_log.py`** vs. **`in_memory_audit_log.py`**
  — the receipt log, real (Postgres) or scratch-paper (in-memory),
  depending on `SOLAROPS_ENV`.
- **Known, disclosed gap:** `CommandRepository`/`ApprovalRequestRepository`
  stay in-memory even in "production" mode — restarting the API loses
  in-flight commands. Written down as a deliberate, understood limitation,
  not hidden.

### 9. `observability/` — the silent clipboard crew

Two files, no layers (`domain`/`application`/`infrastructure`) — it doesn't
reason about anything, it just counts. `metrics.py` defines every
Prometheus `Counter`/`Histogram`/`Gauge` in the system, created once as
module-level singletons. Execution calls into it through a `Protocol`
(`ExecutionMetricsRecorder`) so it never has to import this package
directly — same "shape, not the real thing" trick you'll see everywhere.

### 10. `platform/` — the General Manager

The one file allowed to import *every* department, because its entire job
is building each one and physically handing objects between them.

- **`api_composition.py`** — the GM's opening checklist. Read top to
  bottom and it *is* the whole system's wiring, in order: build the fake
  kitchen → hire the stock-taker → post the house rules → audition the
  sous chef → audition the inspector → hire the head chef → set up the
  entire approval chain. Also exposes `run_decision_cycle()` — the one
  method that runs a complete order from start to finish.
- **`settings.py`** — the one switch (`SOLAROPS_ENV`) deciding real vs.
  fake infrastructure everywhere.
- **`*_wiring.py`** files (`safety_wiring.py`, `forecast_wiring.py`,
  `anomaly_wiring.py`, `decision_wiring.py`) — small translators that take
  the twin's raw settings and repackage them into each department's own
  vocabulary, since no department is allowed to read `SiteConfig` itself.
- **`twin_*.py`** files — the real implementations of each department's
  Protocol, backed by the fake kitchen (`SimulatedHardwareInterface`,
  `TwinTelemetrySource`, `TwinHistoricalDataSource`, ...).

### 11. `api/` — the front door

A thin FastAPI layer — 14 HTTP endpoints, no business logic of its own.
`app.py` builds one `SystemComposition` at startup and keeps it alive for
the whole process; every router just calls a method on it and turns the
result into JSON. `dependencies.py` handles the one bit of real logic here:
a shared-secret `X-API-Key` check on the three approval-mutating endpoints.

### 12. `workflow/` — a real but disconnected side room

A one-node LangGraph graph (`START → decision → END`), built early as
scaffolding for a future multi-step AI orchestration graph. The live API
never routes through it — it calls the decision engine directly instead.
Still tested, still runnable via `scripts/run_decision_pipeline.py`, just
not on the path anything else actually takes. Worth knowing so you don't
assume it's load-bearing.

### `dashboard/` — the front-of-house display (outside the kitchen entirely)

A **separate program**, not part of `solarops` at all — it imports nothing
from the package (checked with a literal `grep`, not just claimed). It's a
Streamlit app that talks to the API over plain HTTP, exactly like any
external client would. Six pages (`overview`, `forecasts`, `anomalies`,
`recommendations`, `commands`, `approvals`), one `api_client.py` doing every
network call, one `style.py` for the shared look.

### Everything else, briefly

- **`scripts/`** — one runnable file per department, mostly predating the
  API — useful for exercising one thing in isolation without booting the
  whole stack. `run_api.py` is the one that *is* the live entry point.
- **`tests/unit/`** — mirrors `src/solarops/` folder-for-folder. `tests/integration/`
  is the small, deliberate exception that needs real services (mostly
  auto-skips cleanly if they're not running). `tests/dashboard/` drives the
  UI headlessly against a real in-process API.
- **`docs/`** — the two founding specs plus one written brief per build
  phase. If you want to know *why* a file looks the way it does, the brief
  for its phase is the real source of truth.
- **`monitoring/`**, **`docker/`**, `Dockerfile`, `docker-compose.yml` — how
  to actually run this thing with real infrastructure. See `DEPLOYMENT.md`.

---

## The libraries, and where each one actually lives

| Library | Where | Why |
|---|---|---|
| Pydantic v2 | `EnergyState`, API schemas | Validation + JSON serialization from one model |
| pydantic-settings | `PlatformSettings`, `APISettings` | Typed config from environment variables |
| FastAPI + Uvicorn | `api/` | Async, free OpenAPI docs, clean dependency injection |
| Redis | `RedisStateStore` | Sub-millisecond reads for "current state right now" |
| SQLAlchemy (Core) + psycopg | `PostgresAuditLog` | Durable, immutable audit trail |
| MLflow | `MLflowModelRegistry`/`MLflowDetectorRegistry` | Versioned experiment tracking, free |
| scikit-learn | Isolation Forest detector, evaluation metrics | Standard classical ML toolkit |
| XGBoost | one forecasting candidate (didn't clear the gate) | Strong tabular regression baseline |
| LangGraph | `workflow/` | Orchestration graph — built, not yet on the live path |
| prometheus-client | `observability/metrics.py` | Standard Prometheus exposition |
| Streamlit + Plotly | `dashboard/` | Full operator UI in pure Python, interactive charts |
| httpx | `dashboard/api_client.py` | The dashboard's only connection to the API |
| pytest, ruff, mypy, import-linter | dev tooling | Tests, lint, types, and the architecture-boundary enforcer |

**No LLM anywhere.** The "AI" is a transparent rule engine plus small
classical ML models — worth knowing before anyone asks.

---

## How data actually flows — one real request, traced

Calling `POST /sites/site-001/decision-cycle` does this, in order:

```
1. telemetry/  reads the current state          → EnergyState
2. forecast/   predicts solar output (if any)     → Forecast
3. anomaly/    checks for faults                    → list[Anomaly]
4. platform/   bundles 1-3 into one DecisionContext
5. decision/   suggests one action                    → Recommendation
6. execution/  drives it through:
      safety/  → PolicyResult, SafetyAssessment, RiskAssessment
      → LOW/MEDIUM: dispatches to hardware, then verifies
      → HIGH: pauses, waits for a human via the API/dashboard
      → CRITICAL: rejected, full stop
7. observability/ silently counts every step along the way
```

Nobody in that list imports anybody they're not supposed to. Data moves
between them exactly three ways, and you'll recognize all three once you've
read a bit of code:

1. **Read this published object, but don't reach inside my other stuff**
   (e.g. everyone reading `EnergyState`).
2. **Here's the shape I need — someone else fill it in** (a `Protocol` in
   one department's `ports.py`, implemented by a real class somewhere else,
   wired together by `platform/`).
3. **The GM physically hands the object from one department to the next**
   (`platform/api_composition.py`, the only file allowed to see everyone).

---

## Getting started, practically

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Run the tests — this is your safety net for every change you make
pytest              # should be 599 passed, 1 skipped (a Redis test that needs a real Redis)
ruff check .         # lint
lint-imports          # the architecture-boundary checker — run this after ANY new import

# 3. Run it locally, no Docker needed
python scripts/run_api.py            # API at http://127.0.0.1:8000/docs
pip install -e ".[dashboard]"
streamlit run dashboard/app.py        # dashboard at http://localhost:8501

# 4. Run it "for real," with Redis/Postgres/MLflow
cp .env.example .env
docker compose up --build
```

**Where to make your first change:** pick one small, well-isolated thing —
e.g. a new field on the dashboard's Overview page, or a new metric in
`observability/metrics.py`. Whatever you touch, the two things to run
before you call it done are `pytest` (did you break anything?) and
`lint-imports` (did you accidentally cross a boundary you shouldn't have?).
If `lint-imports` fails, don't fight it by restructuring — it's telling you
the change belongs somewhere else, or needs a `Protocol` (Way 2 above)
instead of a direct import.

**Where to go deeper:**
- `README.md` — quick architecture reference and the full API surface.
- `PROJECT_DEEP_DIVE.md` — the long-form version of this document, written
  for defending the project: every design decision's reasoning, and every
  real bug that got found and fixed along the way, told honestly.
- `docs/08-domain-driven-design-spec.md` — the original spec this whole
  repo was built from.
- `docs/phase*.md` — one written brief per build phase; the real source of
  truth for *why* any specific file looks the way it does.
- `DEPLOYMENT.md` — how the Docker/real-infrastructure setup actually works.

You now know enough to open any file in this repo and already have a rough
idea what it's for before you've read a single line of its code. That's
the whole point of a project shaped like a restaurant with clear job
descriptions: you don't need the entire codebase in your head at once — you
just need to know which department you're in.
