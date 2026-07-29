# DOCUMENT 8

# DOMAIN-DRIVEN DESIGN (DDD) SPECIFICATION

**Project:** SolarOps AI
**Version:** 1.0
**Owner:** AI Platform Team
**Status:** Draft
**Depends on:** Document 7 — Command Execution & Safety Framework (CESF)

---

# 1. Purpose

This document is the architectural blueprint that every other artifact in SolarOps AI — code, APIs, agents, services, migrations — must conform to. It defines the *ubiquitous language*, the *bounded contexts*, the *aggregates and value objects*, the *domain events*, the *repositories and services*, and — most importantly — the *dependency rules* that keep reasoning cleanly separated from execution.

It exists to enforce one architectural truth established in the CESF:

> **The AI owns reasoning. The Control Plane owns execution. The AI never touches hardware directly.**

Everything below is in service of making that truth structurally impossible to violate — not merely a convention, but a property the type system and layering enforce.

---

# 2. Strategic Design — Bounded Contexts

A bounded context is a boundary within which a model and its language are internally consistent. SolarOps AI is decomposed into seven contexts, each classified by its strategic importance.

| # | Context | Responsibility | Classification |
|---|---------|----------------|----------------|
| 1 | **Telemetry** | Sensor ingestion, validation, current-state reconstruction | Supporting |
| 2 | **Forecast** | Solar / load / battery prediction | Supporting |
| 3 | **Decision** | Optimisation, ranking, recommendation generation | **Core** |
| 4 | **Safety** | Policies, safety validation, risk classification | **Core** |
| 5 | **Execution** | Command planning, approval, dispatch, verification | **Core** |
| 6 | **Simulation** | Digital Twin, physics models, scenarios | Supporting |
| 7 | **Observability** | Audit, metrics, traces, alerts, incidents | Generic |

**Why this classification matters.** The *core domain* is where the project's differentiating value lives — and for SolarOps AI that is not the LLM. It is the **Safety + Execution pipeline that turns a recommendation into a demonstrably safe, verified action**, plus the **Decision** logic that produces good recommendations. Forecasting and simulation are standard supporting capabilities; observability is a generic concern any serious system needs. Engineering effort, test rigor, and design attention are budgeted accordingly.

---

# 3. The Control Plane Overlay

The seven contexts map onto the three Control Plane layers. This is the reconciliation of the two mental models: *bounded contexts* describe **what code owns which concepts**; *Control Plane layers* describe **the authority gradient from thinking to acting**.

```text
                        AI CONTROL PLANE
┌───────────────────────────────────────────────────────────────┐
│                                                                 │
│  REASONING LAYER  (LLM + ML — may recommend, may never act)     │
│  ┌───────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │  Telemetry    │──▶│   Forecast   │──▶│    Decision      │    │
│  │  (perceive)   │   │  (predict)   │   │  (recommend)     │    │
│  └───────────────┘   └──────────────┘   └────────┬─────────┘    │
│                                                   │             │
│                              Recommendation (Published Language)│
│                                                   ▼             │
│  DECISION LAYER  (adjudicates recommendation → authorised?)     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Safety:  Policy · Safety Validation · Risk · Approval  │    │
│  └───────────────────────────────────┬────────────────────┘    │
│                                       │ authorised Command      │
│                                       ▼                         │
│  EXECUTION LAYER  (dispatch · verify — the only actor)          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Execution:  Plan · Dispatch · Acknowledge · Verify     │    │
│  └───────────────────────────────────┬────────────────────┘    │
│                                       │ Hardware Interface (ACL)│
└───────────────────────────────────────┼────────────────────────┘
                                        ▼
                          Simulation (Digital Twin, v1)
                          → future: real hardware, unchanged above

        Observability  ◀── consumes events from every layer (cross-cutting)
```

The authority gradient is strict and one-directional: **Reasoning may recommend; only the Execution Layer acts; and it acts only on a Command the Decision Layer has authorised.** No context in the Reasoning Layer holds a reference that can reach the Hardware Interface.

---

# 4. Context Map — Relationships

DDD context-mapping patterns make the integration contracts explicit.

| Upstream (supplier) | Downstream (consumer) | Pattern | Contract |
|---------------------|-----------------------|---------|----------|
| Simulation (Twin) | Telemetry | Open Host Service | Twin exposes telemetry the same way real sensors would |
| Telemetry | Forecast, Decision, Safety | Open Host Service + Published Language | `EnergyState` snapshot |
| Forecast | Decision | Customer/Supplier | `Forecast` |
| Decision | Execution | **Published Language** | `Recommendation` (the contract crossing into the Control Plane) |
| Safety | Execution | Customer/Supplier | `SafetyAssessment`, `RiskAssessment` (Execution is the customer; **fail-safe** applies — §9) |
| Execution | Simulation (Twin) | **Anticorruption Layer** | `HardwareInterface` port; the twin conforms to it, real hardware later conforms to it |
| All contexts | Observability | Published Language | Domain events → audit / metrics / alerts |

Two relationships carry the architecture:

- **Decision → Execution is a Published Language, not a shared object.** A `Recommendation` crosses the boundary as an immutable contract. Execution does not import Decision's internals, and vice versa. This is what lets the optimisation engine evolve (Rule Engine → Constraint Optimiser → MPC → RL) without any change to the execution pipeline.

- **Execution → Simulation is an Anticorruption Layer.** The `HardwareInterface` port belongs to the Execution context and speaks *its* language (`asset_id`, `command`, `target_soc`). The Digital Twin implements that port today; a Modbus/MQTT/vendor adapter implements it tomorrow. Execution never learns a vendor's dialect. This is the DDD formalisation of CESF Success Criterion: *"the Digital Twin and future hardware interfaces can be swapped without modifying AI logic."*

---

# 5. Ubiquitous Language

Every term below has exactly one meaning across the codebase, docs, tests, and conversations. Divergence from this glossary is a bug.

| Term | Definition |
|------|------------|
| **Recommendation** | Structured intent produced by the Decision context. Carries *what* and *why*, never *how*. Non-executable. |
| **Command** | An executable instruction with a full lifecycle and audit trail. The central aggregate of Execution. |
| **Gate** | A pipeline stage that can pass a command through or terminate it (Policy, Safety, Risk, Approval, Verification). |
| **Control Plane** | The whole reasoning-to-execution system; comprises the Reasoning, Decision, and Execution layers. |
| **Policy** | Site-configurable operational rule (max SOC, maintenance mode, critical-load protection, operator override). |
| **Safety Validation** | The final technical gate: hard physical/operational limits. Failing it always blocks. |
| **Risk Level** | Classification — Low / Medium / High / Critical — that determines the approval path. |
| **Approval** | Human-in-the-loop authorisation for Medium/High risk commands. Async; pauses the pipeline. |
| **Dispatch** | Sending an authorised command to the Hardware Interface. |
| **Acknowledgement** | The interface confirming receipt (not yet proof of effect). |
| **Verification** | Confirming, via telemetry, that the asset actually changed state as expected. |
| **Hardware Interface** | The anticorruption-layer port through which — and only through which — commands reach an asset. |
| **Digital Twin** | The v1 deterministic simulator implementing the Hardware Interface. |
| **Telemetry** | A single immutable sensor reading. |
| **EnergyState** | A consistent, immutable snapshot of the whole site's current state. |
| **Forecast** | A time-series prediction with metadata (model, horizon, confidence). |
| **Scenario** | A named configuration that drives the Twin (e.g. "grid outage", "cloudy afternoon"). |
| **Incident** | A managed operational anomaly with a lifecycle (open → investigating → resolved). |
| **Alert** | An immutable emitted notification; may escalate into an Incident. |
| **Audit Entry** | An immutable, append-only record of something that happened. Never edited, never deleted. |
| **Fail-Safe** | When a critical pipeline component is unavailable, the default action is to *reject*, never to act. |
| **Site** | A physical location aggregating assets and policies. |
| **Asset** | A controllable/observable unit: Battery, Inverter, Solar, Grid, Building Load. |
| **Operator** | A human actor with an RBAC role; the subject of approvals and audit attribution. |

---

# 6. Tactical Design — Aggregates, Value Objects, Events, Repositories, Services

Notation: **AR** = Aggregate Root (entity, consistency boundary, has a repository). **E** = Entity (identity, but lives inside an aggregate). **VO** = Value Object (immutable, no identity, compared by value). Every one of the 22 domain models from the stack decision is placed exactly once.

### 6.1 Telemetry Context — *Supporting*

| Element | Kind | Notes |
|---------|------|-------|
| `Asset` | AR | Battery / Inverter / Solar / Grid / BuildingLoad as `AssetType`; holds config + operating mode |
| `Telemetry` | VO | One immutable reading (timestamp + measurements) |
| `EnergyState` | VO | Immutable consistent snapshot of the whole site |
| Repositories | — | `AssetRepository`, `TelemetryRepository` (time-series), `StateStore` (Redis, current state) |
| Domain services | — | `TelemetryIngestionService`, `StateManager` (reconstructs `EnergyState`) |
| Events out | — | `TelemetryIngested`, `EnergyStateUpdated`, `AssetOffline` |

### 6.2 Forecast Context — *Supporting*

| Element | Kind | Notes |
|---------|------|-------|
| `Forecast` | AR | Identity + horizon + series of predicted points |
| `ForecastMetadata` | VO | Model version, generated-at, confidence, horizon |
| `ForecastPoint` | VO | (timestamp, value, interval) |
| Repositories | — | `ForecastRepository` |
| Domain services | — | `SolarForecaster`, `LoadForecaster`, `BatteryForecaster` |
| Events out | — | `ForecastGenerated` |

### 6.3 Decision Context — *Core*

| Element | Kind | Notes |
|---------|------|-------|
| `Recommendation` | AR | The Published-Language output crossing into the Control Plane |
| Repositories | — | `RecommendationRepository` |
| Domain services | — | `OptimisationAgent` (**stub in v1** → Rule Engine → Constraint Optimiser → MPC → RL), `RecommendationRanker` |
| Events out | — | `RecommendationProduced` |

The v1 stub `OptimisationAgent` returns, e.g.:

```python
Recommendation(
    action=ActionType.START_BATTERY_CHARGE,
    confidence=0.91,
    expected_benefit="Prepare for forecasted evening demand",
    reason="Battery below target reserve",
)
```

### 6.4 Safety Context — *Core*

| Element | Kind | Notes |
|---------|------|-------|
| `Policy` | AR | Versioned site policy; mutable by operators |
| `SafetyAssessment` | VO | Immutable result: passed/blocked + failed checks + evaluated limits |
| `RiskAssessment` | VO | Immutable: `RiskLevel` + contributing factors + safety margin |
| Repositories | — | `PolicyRepository` |
| Domain services | — | `PolicyValidator`, `SafetyValidator`, `RiskAssessor` |
| Events out | — | `PolicyViolated`, `CommandBlockedBySafety`, `RiskAssessed` |

### 6.5 Execution Context — *Core (crown jewel)*

| Element | Kind | Notes |
|---------|------|-------|
| `Command` | AR | Owns the full lifecycle state machine (§7). Holds gate outcomes as VOs. |
| `ApprovalRequest` | AR | **Separate** aggregate — async human workflow, own lifecycle + timeout |
| `CommandPlan` | VO | Planned parameters produced by the planner |
| `PolicyResult` | VO | Outcome attached to the command |
| `ApprovalDecision` | VO | Approve / Reject / Modify + operator identity, inside `ApprovalRequest` |
| `ExecutionResult` | VO | Success / Failed / TimedOut / Cancelled / Blocked + retries + acks |
| `VerificationResult` | VO | Expected vs observed telemetry + pass/fail |
| Repositories | — | `CommandRepository`, `ApprovalRequestRepository` |
| Domain services | — | `CommandPlanner`, `ApprovalEngine`, `ExecutionManager`, `VerificationService` |
| Ports | — | `HardwareInterface` (ACL — the only path to an asset) |
| Events out | — | `CommandCreated`, `CommandValidated`, `CommandApproved/Rejected`, `CommandDispatched`, `CommandAcknowledged`, `CommandExecuted/Failed/TimedOut`, `ExecutionVerified/VerificationFailed`, `CommandCompleted`, `ApprovalRequested` |

### 6.6 Simulation Context — *Supporting*

| Element | Kind | Notes |
|---------|------|-------|
| `DigitalTwin` | AR | Deterministic physics engine; **implements `HardwareInterface`** |
| `SimulationState` | VO | Immutable snapshot of the twin's internal physical state |
| `Scenario` | AR | Named configuration driving the twin |
| Repositories | — | `ScenarioRepository` (twin state in memory / Redis) |
| Domain services | — | `BatteryModel`, `SolarModel`, `LoadModel`, `GridModel`, `InverterModel`, `ScenarioRunner` |
| Events out | — | `SimulationTick`, `ScenarioLoaded` |

The simulation is **pure deterministic physics — no ML** — which is exactly what makes the entire pipeline testable offline.

### 6.7 Observability Context — *Generic, cross-cutting*

| Element | Kind | Notes |
|---------|------|-------|
| `Incident` | AR | Managed anomaly with lifecycle |
| `AuditEntry` | VO | Immutable, append-only; never edited or deleted |
| `Alert` | VO | Immutable emitted notification |
| `Event` | VO | The persisted domain-event envelope |
| Repositories | — | `AuditLog` (append + read only), `EventStore` (append-only), `IncidentRepository` |
| Domain services | — | `AuditService`, `MetricsCollector`, `AlertingService`, `IncidentManager` |

### 6.8 Platform concerns (not full contexts)

| Element | Kind | Home |
|---------|------|------|
| `Site` | AR | Config aggregate; holds Asset IDs + Policy ID by reference |
| `Operator` | E | Small Access/RBAC concern (generic); referenced by Approval + Audit |

---

# 7. The Command Aggregate — Lifecycle & Invariants

The `Command` is the consistency boundary at the heart of the system. It owns a state machine that mirrors the CESF pipeline. **Every transition emits a domain event and appends an immutable `AuditEntry`.**

```text
                         CREATED
                            │ plan
                         PLANNED
                            │ policy
        ┌───────────────────┼──────────────▶ REJECTED_BY_POLICY  (terminal)
                     POLICY_VALIDATED
                            │ safety
        ┌───────────────────┼──────────────▶ BLOCKED_BY_SAFETY   (terminal)
                     SAFETY_VALIDATED
                            │ risk
                     RISK_ASSESSED
              ┌──────────┬──┴───────┬──────────────┐
          Low│      Med/High│   Critical│           │
             ▼           ▼             ▼            
      AUTO_APPROVED  AWAITING_APPROVAL  REJECTED_BY_RISK (terminal)
             │           │ decision
             │      ┌────┴─────┐
             │  approve   reject/timeout
             │      │         └──────────▶ REJECTED_BY_OPERATOR / TIMED_OUT (terminal)
             │   APPROVED
             └──────┬──────┘
                    │ dispatch
                DISPATCHED ───────────────▶ DISPATCH_FAILED     (terminal)
                    │ ack
               ACKNOWLEDGED
                    │ execute ────────────▶ EXECUTION_FAILED / TIMED_OUT (terminal)
                 EXECUTED
                    │ verify ─────────────▶ VERIFICATION_FAILED → raises Incident (terminal)
                 VERIFIED
                    │
                COMPLETED  (terminal, success)
```

**Invariants enforced by the aggregate (not by callers):**

1. A command may only be **DISPATCHED** if it is `APPROVED` (or `AUTO_APPROVED`) *and* has passing `PolicyResult` and `SafetyAssessment`. There is no code path to dispatch otherwise.
2. `RiskLevel.CRITICAL` transitions directly and only to `REJECTED_BY_RISK`. Critical is never dispatchable.
3. Transitions are forward-only; the sole exception is moving to a terminal failure state.
4. `COMPLETED` requires a `VerificationResult` with `passed = True`. Acknowledgement alone never completes a command (ADR-011).
5. Each command carries a unique **idempotency key**; a duplicate dispatch is rejected, preventing duplicate execution (CESF §14).
6. A command is never mutated in place through Redis/cache; state changes go through the aggregate, are persisted via `CommandRepository`, and are audited.

This state machine *is* the CESF pipeline, encoded as an aggregate invariant rather than as scattered `if` statements — which is what makes "100% of unsafe commands blocked" a structural guarantee rather than a hope.

---

# 8. Shared Kernel — Scoped Deliberately

You asked that every service import the same models so the language stays consistent. Correct in spirit — but a *large* shared kernel silently couples contexts and turns every change into a cross-context change. So the shared kernel is scoped to the **language, not the behaviour**:

**In the shared kernel** (`solarops.shared_kernel`):
- **Typed IDs:** `SiteId`, `AssetId`, `CommandId`, `RecommendationId`, `OperatorId`, `IncidentId` (no bare strings crossing boundaries).
- **Units as value objects:** `Power(kW)`, `Energy(kWh)`, `StateOfCharge(%)`, `Temperature(°C)`, `Voltage`, `Current`, `Frequency(Hz)` — self-validating, no primitive obsession.
- **Enums:** `AssetType`, `ActionType`, `CommandStatus`, `RiskLevel`, `ExecutionOutcome`, `ApprovalOutcome`, `AssetOperatingMode`.
- **`DomainEvent`** base + the event envelope.
- **Domain exceptions:** `SafetyViolation`, `PolicyViolation`, `UnsafeStateError`, `DuplicateCommandError`, `FailSafeTriggered`, `InvalidStateTransition`.
- The **clock abstraction** (so tests and simulation control time).

**Not in the shared kernel** — each stays inside its owning context and crosses boundaries only as a published-language contract/DTO: `Command`, `Recommendation`, `Forecast`, `SafetyAssessment`, `Policy`, `Site`, `DigitalTwin`, etc.

The rule of thumb: **if two contexts must agree on a value's *meaning*, it's shared kernel; if they must agree on an aggregate's *behaviour*, it's a published-language contract, not a shared object.**

---

# 9. Dependency Rules

These are the load-bearing rules. Everything else is negotiable; these are not.

**9.1 Layered dependency (hexagonal / clean architecture).** Each context is internally split into `domain / application / infrastructure`, and dependencies point *inward only*:

```text
   infrastructure  ──depends on──▶  application  ──depends on──▶  domain
   (SQLAlchemy, Redis, Qdrant,       (use cases,                 (models, VOs,
    OpenAI/Anthropic, FastAPI,        orchestration,              enums, domain
    HTTP hardware adapter,            LangGraph nodes)            services, ports)
    Celery)                                                       depends on NOTHING
```

- **The domain layer imports no framework.** No FastAPI, no SQLAlchemy, no LangGraph, no OpenAI SDK appears in a domain module. The `Command` aggregate does not know Postgres exists.
- Repositories and the `HardwareInterface` are **ports** (interfaces) defined in the domain; their SQLAlchemy/Redis/HTTP implementations live in infrastructure and are injected. This dependency inversion is precisely what lets the Twin be swapped for real hardware.

**9.2 Control-plane boundary.** No Reasoning-Layer context (Telemetry, Forecast, Decision) may import from the Execution context, and none holds a reference that can reach `HardwareInterface`. Communication downward happens exclusively through the `Recommendation` published language. This makes "the AI cannot execute" a compile-time/import-time fact, not a runtime check.

**9.3 Fail-safe as a dependency rule (ADR-012).** The Execution context depends on the Safety port. If the Safety port is unavailable or errors, `ExecutionManager`'s default is to **reject**, raising `FailSafeTriggered`. There is no "assume safe on error" branch anywhere in the codebase.

**9.4 Audit is unconditional.** Every state transition on a `Command`, and every operator action, appends to the immutable `AuditLog`. There is no code path that mutates command state without auditing it.

These are enforced mechanically, not by discipline: an import-linter contract in CI fails the build if a domain module imports infrastructure, or if a Reasoning context imports Execution.

---

# 10. Folder Structure

A **modular monolith** (ADR-013): one deployable, hard module boundaries. Microservices later become a deployment change, not a redesign, because the contexts are already isolated.

```text
solarops/
├── pyproject.toml
├── docker-compose.yml
├── alembic.ini
├── .github/workflows/           # GitHub Actions CI (lint, import-linter, tests)
├── docs/
│   ├── 07-cesf.md
│   └── 08-ddd-spec.md           # this document
├── migrations/                  # Alembic
├── src/solarops/
│   ├── shared_kernel/           # ids, units, enums, events, exceptions, clock
│   │
│   ├── telemetry/               # ┐
│   │   ├── domain/              # │ each context:
│   │   ├── application/         # │   domain  → pure model + ports
│   │   └── infrastructure/      # │   application → use cases / orchestration
│   ├── forecast/                # │   infrastructure → adapters (db, redis, api)
│   ├── decision/                # │
│   ├── safety/                  # │
│   ├── execution/               # │
│   ├── simulation/              # │
│   ├── observability/           # ┘
│   │
│   ├── platform/                # config, DB session, Redis, Qdrant, DI container, RBAC
│   ├── workflow/                # LangGraph graph, shared state, nodes wiring contexts
│   └── api/                     # FastAPI app + routers (edge/adapter layer)
│
└── tests/
    ├── unit/                    # per-aggregate, no I/O
    ├── integration/             # context + real adapters (db, redis)
    └── contract/                # published-language contracts between contexts
```

---

# 11. Mapping to the Build Order

This blueprint maps directly onto the seven phases. Each phase builds only what the dependency rules allow it to build.

| Phase | Delivers | Contexts / layers touched |
|-------|----------|---------------------------|
| **1** | Domain models, enums, value objects, exceptions | `shared_kernel` + `domain` of every context |
| **2** | Digital Twin, asset models, telemetry generator | Simulation, Telemetry (domain + infra) |
| **3** | State manager, Redis, event store | Telemetry, Observability (infra) |
| **4** | LangGraph workflow, stub agents, shared state | `workflow`, Decision (stub) |
| **5** | Full command pipeline: policy, safety, risk, approval, execution, verification | Safety + Execution (**core**) |
| **6** | Forecast models, anomaly detection, optimisation engine | Forecast, Decision (real logic replacing stub) |
| **7** | API, dashboard, MLflow, Langfuse, Prometheus, Grafana | `api`, Observability, platform |

Phase 1 is next. Because the shared kernel and domain models have zero framework dependencies, they are the safest, highest-leverage starting point — everything downstream imports them, and they can be fully unit-tested with no infrastructure.

---

# 12. Architecture Decision Records

*(Continuing the numbering from CESF, which ended at ADR-012.)*

### ADR-013 — Modular Monolith over Microservices (for v1)
**Decision:** One deployable with hard, import-enforced context boundaries.
**Reason:** Preserves DDD isolation and the "swap to microservices later" option, without the operational cost of distributed systems before it's warranted. The boundaries are real in code today; they become network boundaries later only if load demands it.

### ADR-014 — Minimal Shared Kernel
**Decision:** Share only IDs, units, enums, the event base, and exceptions. Aggregates cross boundaries as published-language contracts.
**Reason:** A large shared kernel couples every context to every change. Sharing the *language* but not the *behaviour* keeps contexts independently evolvable while preserving one ubiquitous language.

### ADR-015 — Hardware Interface as an Anticorruption Layer
**Decision:** `HardwareInterface` is a port owned by Execution; the Twin and all future hardware adapters conform to it.
**Reason:** Formalises CESF's swap-without-changing-AI-logic goal. Vendor dialects (Modbus, MQTT, proprietary APIs) never leak into the AI or the command model.

### ADR-016 — Command Aggregate Owns Its Lifecycle
**Decision:** The `Command` aggregate enforces its state-machine transitions and gate invariants internally.
**Reason:** Encodes "unsafe commands cannot execute" as an aggregate invariant rather than as scattered checks callers might forget — making CESF's "100% of unsafe commands blocked" a structural property.

### ADR-017 — Approval is a Separate Aggregate
**Decision:** `ApprovalRequest` is its own aggregate root, linked to a `Command` by ID, not nested inside it.
**Reason:** Human approval is asynchronous, long-lived, and has its own timeout lifecycle. Keeping it out of the Command's consistency boundary avoids holding the command's transaction open across a human decision.

---

# 13. Open Questions (deferred, not forgotten)

- **Event sourcing depth:** Is `EnergyState` fully event-sourced from the event store, or a Redis-cached projection with periodic snapshots? (Resolved in Phase 3.)
- **Idempotency key derivation:** Content hash of the plan vs. an explicit key from the planner. (Resolved in Phase 5.)
- **Approval transport:** In-process now; message queue (Celery/Redis) when approvals may outlive a request. (Revisit in Phase 5.)
- **RBAC granularity:** Whether `Operator` roles gate *which* commands may be approved by *whom* per asset class. (Revisit in Phase 5/7.)

---

# 14. Success Criteria for this Specification

This DDD spec has succeeded when:

- Every module in the codebase belongs to exactly one bounded context, and its dependencies obey §9.
- The import-linter contract in CI passes: no domain module imports infrastructure; no Reasoning context imports Execution.
- A new engineer can read §5 and §7 and correctly predict what the code does.
- The Digital Twin can be replaced by a real hardware adapter touching only the Simulation context and the `HardwareInterface` implementation.
- Adding a new optimisation strategy (Rule Engine → MPC → RL) requires zero changes to Safety or Execution.
