# Code Walkthrough — five real execution paths, file by file

This document does not summarize the architecture — `ONBOARDING.md` and
`PROJECT_DEEP_DIVE.md` already do that. This document **follows the actual
code**: exact files, exact methods, in the exact order they run, so you can
have this open next to the source and step through it line by line.

Every snippet below is quoted verbatim from the file at the line numbers
given, as of the current codebase — if a line number looks off after a
future edit, the method name is still the thing to search for.

## Contents

1. [Get current state — API → Redis → back](#1-get-current-state--api--redis--back)
2. [Run a decision cycle — API → Telemetry → Forecast → Anomaly → Decision](#2-run-a-decision-cycle)
3. [Execute a command — the full safety/approval/dispatch pipeline](#3-execute-a-command)
4. [The decision engine's actual rules](#4-the-decision-engines-actual-rules)
5. [The composition root — how it's all wired at startup](#5-the-composition-root)
6. [How to make common changes](#6-how-to-make-common-changes)

---

## 1. Get current state — API → Redis → back

This is the simplest trace in the system — worth starting here because
every other trace reuses pieces of it.

**`src/solarops/api/routers/state.py:13-20` → `get_state()`**
```python
@router.get("/sites/{site_id}/state", response_model=EnergyStateResponse)
def get_state(
    site_id: str, composition: SystemComposition = Depends(get_composition)
) -> EnergyStateResponse:
    state = composition.state_manager.get_current(SiteId(site_id))
    if state is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no current state for site {site_id!r}")
    return EnergyStateResponse.from_domain(state)
```
What it does: the whole route is four lines. `Depends(get_composition)`
(next file) hands it the one live `SystemComposition`; everything else is
"ask for the state, 404 if there isn't one yet, otherwise convert to JSON."
Calls next: `composition.state_manager.get_current(...)`.

**`src/solarops/api/dependencies.py:21-22` → `get_composition()`**
```python
def get_composition(request: Request) -> SystemComposition:
    return request.app.state.composition
```
What it does: not a lookup, not a rebuild — it just returns the *one*
`SystemComposition` object that was built once at process startup and
stashed on `app.state` (you'll see exactly where in Trace 5). Every route
in the whole API gets the same object back from this.

**`src/solarops/telemetry/application/state_manager.py:27-28` → `StateManager.get_current()`**
```python
def get_current(self, site_id: SiteId) -> EnergyState | None:
    return self._store.get(site_id)
```
What it does: one line, forwards straight to whatever `StateStore` it was
built with. Calls next: `self._store.get(site_id)` — and *which* class
`self._store` actually is depends on `SOLAROPS_ENV` (see Trace 5).

**`src/solarops/telemetry/infrastructure/redis_state_store.py:24-28` → `RedisStateStore.get()`**
```python
def get(self, site_id: SiteId) -> EnergyState | None:
    raw = self._client.get(self._key(site_id))
    if raw is None:
        return None
    return EnergyState.model_validate_json(raw)
```
What it does: this is the actual Redis call — `self._client.get(...)` asks
Redis for whatever's stored under key `"state:site-001"`. Redis stores raw
bytes (JSON text), so `EnergyState.model_validate_json(raw)` is Pydantic
parsing that JSON back into a real, typed `EnergyState` object. (If
`SOLAROPS_ENV` is unset/`local`, this is instead `InMemoryStateStore.get()`
— a plain dict lookup, no Redis, no JSON round-trip at all — same method
signature, radically simpler body.)

**Back up: `src/solarops/api/schemas/state.py:48-76` → `EnergyStateResponse.from_domain()`**
```python
@classmethod
def from_domain(cls, state: EnergyState) -> EnergyStateResponse:
    return cls(
        site_id=str(state.site_id),
        ...
        solar_power_kw=state.solar_power.value,
        ...
    )
```
What it does: the trip back up. Every shared-kernel typed field
(`state.solar_power`, a `Power` object) gets unwrapped to a plain float
(`state.solar_power.value`) here — this is the one place `Power`/
`Temperature`/etc. stop being rich objects and become plain JSON numbers.
FastAPI then serializes the returned `EnergyStateResponse` to JSON and
sends it back over HTTP.

**One thing worth knowing before you go looking for it:** this endpoint
**never refreshes anything**. It only returns whatever was last written to
the store — by a decision cycle (Trace 2), possibly minutes ago. If you
want to know how a value *got into* Redis in the first place, that's
`SystemComposition.refresh_telemetry()`, covered next.

**In plain English, the whole flow was:** the route asks the one shared
`SystemComposition` for its `StateManager`, which asks whichever
`StateStore` is configured (Redis or a plain dict) for the last thing
written under this site's key, and — if something's there — hands back a
fully-typed `EnergyState` that then gets flattened into plain JSON numbers
for the HTTP response. No new reading is taken; this is a pure read of
whatever's already cached.

---

## 2. Run a decision cycle

**Important correction before this trace starts:** if you were expecting
this to route through `workflow/`'s LangGraph graph — it doesn't. The live
API calls the decision engine directly. `workflow/graph.py`'s
`START -> decision -> END` graph is real and tested, but only
`scripts/run_decision_pipeline.py` and `tests/unit/workflow/test_graph.py`
actually exercise it. This trace follows the path that genuinely runs when
you hit the API — see `ONBOARDING.md`'s section on `workflow/` for why
that split exists.

**`src/solarops/api/routers/decisions.py:25-34` → `run_decision_cycle()`**
```python
@router.post("/sites/{site_id}/decision-cycle", response_model=DecisionCycleResponse)
def run_decision_cycle(
    site_id: str, composition: SystemComposition = Depends(get_composition)
) -> DecisionCycleResponse:
    ranked, command = composition.run_decision_cycle()
    return DecisionCycleResponse(...)
```
Calls next: `composition.run_decision_cycle()` — the entire route is one
call plus response formatting.

**`src/solarops/platform/api_composition.py:350-361` → `SystemComposition.run_decision_cycle()`**
```python
def run_decision_cycle(self) -> tuple[RankedRecommendations, Command]:
    self.refresh_telemetry()
    context = self.current_decision_context()
    assert context is not None, "refresh_telemetry() just ran; state must exist"
    ranked = self.recommend(context)
    command = self.execution_pipeline.run(ranked.top)
    return ranked, command
```
What it does: four calls, in order — refresh, build context, reason,
execute. This method *is* the whole cycle; everything below is what each
of those four calls actually does.

### Step A — refresh telemetry, and feed Forecast/Anomaly on the way

**`src/solarops/platform/api_composition.py:261-294` → `refresh_telemetry()`**
```python
state, telemetry_events = self.ingestion.ingest(self.site_id)          # line 273
self.state_manager.update(state)                                         # line 274
...
with contextlib.suppress(NoRegisteredModel):                               # line 282
    _forecast, forecast_event = self.solar_forecaster.forecast(state)       # line 283
...
_anomalies, anomaly_events = self.anomaly_scoring_service.score(state, history_before)  # line 287
```
What it does, in order:
1. `self.ingestion.ingest(...)` — pulls one reading (the read side of
   Trace 1's *write* path — the twin's `.tick()` under the hood, wrapped
   into `Telemetry` then `EnergyState`), and **writes it into the
   StateStore right here** (`self.state_manager.update(state)`) — this is
   the exact moment Trace 1's Redis key gets a new value.
2. `self.solar_forecaster.forecast(state)` — asks whatever forecaster is
   currently registered for a fresh prediction. Wrapped in
   `contextlib.suppress(NoRegisteredModel)` — if a forecaster isn't
   registered (true today for Load/Battery-SOC), this quietly does
   nothing rather than crashing the whole cycle.
3. `self.anomaly_scoring_service.score(...)` — runs every currently active
   anomaly detector against the new reading plus recent history.

**`src/solarops/anomaly/application/scoring_service.py:45-88` → `AnomalyScoringService.score()`**
```python
for detector in self._registry.get_active():                # line 49
    covered = self._registry.covered_types(detector.name)
    detections.extend(
        d for d in detector.detect(state, history) if d.anomaly_type in covered
    )
...
for (anomaly_type, asset), group in grouped.items():           # line 62
    confidence = max(d.confidence for d in group)
    anomaly = Anomaly(..., severity=self._severity_for(confidence), ...)
    self._repository.save(anomaly)
```
What it does: calls `.detect()` on every registered detector (today: Rule
and Statistical — Isolation Forest never passed its gate), keeps only
`Detection`s for fault types that detector actually cleared its gate on,
groups multiple detectors firing on the *same* fault into one merged
`Anomaly`, and saves each one.

### Step B — build the decision context

**`src/solarops/platform/api_composition.py:312-338` → `current_decision_context()`**
```python
state = self.state_manager.get_current(self.site_id)                     # line 321
...
solar_forecast = self.forecast_repository.get_latest(...)                  # line 325
...
recent_anomalies = self.anomaly_repository.list_recent(
    self.site_id, since=self.clock.now() - _ANOMALY_RELEVANCE_WINDOW)       # line 330
return DecisionContext(
    energy_state=state, operating_constraints=self.operating_constraints,
    available_forecasts=available_forecasts, active_anomaly_count=len(recent_anomalies))
```
What it does: **read-only, no new work** — it re-reads the state that
Step A just wrote, whatever forecast is registered, and a *count* of
recent anomalies (never the anomaly objects themselves — Decision is not
allowed to import Anomaly), and bundles all three into one `DecisionContext`.

### Step C — reason

**`src/solarops/platform/api_composition.py:340-348` → `recommend()`**
```python
def recommend(self, context: DecisionContext) -> RankedRecommendations:
    started_at = time.perf_counter()
    ranked = self.decision_engine.recommend(context)
    recommendation_latency_seconds.observe(time.perf_counter() - started_at)
    return ranked
```
Calls next: `self.decision_engine.recommend(context)` — `decision_engine`
is a `RuleBasedOptimiser` instance. **This is where "the AI" actually
runs** — see Trace 4 for exactly what happens inside it.

### Step D — execute

`self.execution_pipeline.run(ranked.top)` — `ranked.top` is the
highest-priority `Recommendation` (`RankedRecommendations.top`, just
`self.recommendations[0]`). This call is the entirety of Trace 3.

**In plain English, the whole flow was:** the route asked
`SystemComposition` to run one full cycle; it pulled a fresh reading and
immediately fed it to whichever forecaster and anomaly detectors are
currently registered, re-read everything it just wrote into a bundled
`DecisionContext`, handed that to the rule-based decision engine for one
recommendation, and finally pushed that recommendation's top choice into
the execution pipeline — which is a whole separate trace, because a
recommendation is just a suggestion until it survives that pipeline.

---

## 3. Execute a command

Starting point: `self.execution_pipeline.run(ranked.top)` from Trace 2 —
`ranked.top` is a `Recommendation`, not yet a `Command`.

**`src/solarops/execution/application/execution_pipeline.py:138-242` → `ExecutionPipeline.run()`**

This is the longest method in the codebase — walking it stage by stage:

**Stage 0 — idempotency check (line 144-146)**
```python
idempotency_key = f"idem-{recommendation.recommendation_id}"
if self._command_repository.get_by_idempotency_key(idempotency_key) is not None:
    raise DuplicateCommandError(idempotency_key)
```
If this exact recommendation already produced a command, refuse to make a
second one.

**Stage 1 — plan (line 148)**
```python
command, created_event = self._command_planner.plan(recommendation)
```
Calls `src/solarops/execution/application/command_planner.py:42-61` →
`CommandPlanner.plan()`, which calls `Command.create(...)` — assigns a
real `CommandId`, resolves which asset this targets (a lookup table by
action type, e.g. `CHARGE_BATTERY` → `"battery"` — see
`_ACTION_ASSET_KIND` at line 24), and moves the new `Command` straight to
`PLANNED` status.

**Stage 2 — policy gate (line 152-163)**
```python
intent = to_command_intent(command, asset_operating_mode=asset_operating_mode)
policy_result, policy_events = self._policy_validator.validate(intent)
...
command.apply_policy_result(policy_result)
if not policy_result.passed:
    self._reject(command, "policy violation")
    return command
```
`to_command_intent` (`execution/application/command_intent_mapper.py`)
converts the real `Command` into Safety's own minimal `CommandIntent`
type. `PolicyValidator.validate()` checks the configurable rules (target
SOC vs policy limits, maintenance-mode restrictions, shed-fraction
ceiling). **Fails here → `REJECTED_BY_POLICY`, stops. Pipeline returns
immediately — nothing below this line runs.**

**Stage 3 — safety gate, fail-safe wrapped (line 166-186)**
```python
try:
    safety_assessment = self._safety_validator.validate(intent)
except FailSafeTriggered as exc:
    safety_assessment = SafetyAssessment(passed=False, failed_checks=(f"fail-safe: {exc}",), ...)
    ...
    self._reject(command, f"fail-safe: {exc}")
    return command
...
if not safety_assessment.passed:
    self._audit(CommandBlockedBySafety(...))
    return command
```
`SafetyValidator.validate()` checks the hard physical limits (battery
temp/power caps, inverter status, grid voltage/frequency tolerance).
Notice the `try/except FailSafeTriggered` — if Safety itself can't even
run its checks (state unavailable, an internal error), that's caught and
converted into an automatic block, never treated as "must be fine." **Fails
here → `BLOCKED_BY_SAFETY`, stops.**

**Stage 4 — risk gate (line 188-235)**
```python
risk_assessment = self._risk_assessor.assess(intent, state, policy, limits, safety_assessment)
command.apply_risk_assessment(risk_assessment)
...
if risk_assessment.level.is_auto_rejected:
    command.reject_by_risk()
    self._reject(command, "risk level CRITICAL")
    return command

approval_request = self._approval_engine.route(command, confidence_band=recommendation.confidence_band)
if approval_request is not None:
    ...
    return command  # PAUSED — resume_after_approval() continues this
```
`RiskAssessor.assess()` classifies LOW/MEDIUM/HIGH/CRITICAL (see the
Safety folder walkthrough from earlier in this conversation for its exact
if/then ladder). **CRITICAL → `REJECTED_BY_RISK`, stops, never reaches
`ApprovalEngine` at all.**

Otherwise, `ApprovalEngine.route()`
(`execution/application/approval_engine.py:42-70`) makes the actual
approve-vs-pause call:
```python
requires_approval = level.requires_manual_approval or confidence_band is ConfidenceBand.LOW
```
**Worth knowing precisely** — this is an `or`, not just risk level: a HIGH
risk *or* a Low confidence band (from Trace 4's confidence estimate) is
enough to force a pause, even at LOW/MEDIUM risk. If it pauses:
`command.await_approval()`, an `ApprovalRequest` is saved, and
`run()` **returns right here** — `resume_after_approval()` (below) is a
*separate* method call, triggered later by a human hitting
`POST /approvals/{id}/approve`, not a continuation of this same call.

If no approval is needed: `command.auto_approve()` inside `route()`, then
`run()` falls through to `self._dispatch_and_verify(command)` (line 242).

**`resume_after_approval()` (line 244-268)** — the path after a human
decides:
```python
self._approval_engine.decide(request, command, decision)
...
if command.status is CommandStatus.REJECTED_BY_OPERATOR:
    self._reject(command, "operator rejected")
    return command
...
return self._dispatch_and_verify(command)
```
`ApprovalEngine.decide()` turns the human's decision into
`command.approve(decision)` or `command.reject_by_operator(decision)`.
Approved (or modified) → falls through to the same
`_dispatch_and_verify()` an auto-approved command reaches.

**Stage 5 — dispatch and verify (line 270-333)** → `_dispatch_and_verify()`
```python
result = self._execution_manager.dispatch(command)
...
if command.status in (CommandStatus.DISPATCH_FAILED, CommandStatus.EXECUTION_FAILED):
    ...
    return command
...
if self._telemetry_refresh is not None:
    self._telemetry_refresh()
verification = self._verification_service.verify(command)
command.verify(verification)
if not verification.passed:
    ...
    return command
...
command.complete()
```
`ExecutionManager.dispatch()`
(`execution/application/execution_manager.py:32-95`) calls
`HardwareInterface.send()` (real or simulated — Trace 5), retrying up to
`DEFAULT_MAX_RETRIES = 2` times only on a `TIMED_OUT` outcome
(`_send_with_retries`, line 97-111). Any exception, or a `BLOCKED`
outcome, is a dispatch failure — never silently retried into a false
positive.

If dispatch succeeded: `self._telemetry_refresh()` pulls one more fresh
reading first (so verification doesn't compare against stale,
pre-command data), then `VerificationService.verify()`
(`execution/application/verification_service.py:35-61`) checks the
outcome — for the three battery actions, an exact expected
`battery_mode` match; for everything else, the weaker "no active fault
codes" check. **Fails here → `VERIFICATION_FAILED`, stops** — even a
successfully dispatched, successfully executed command does not reach
`COMPLETED` without this passing (ADR-011).

Only after all of that: `command.complete()` → `COMPLETED`.

**One thing that runs after literally every single stage above, success
or failure:** `self._audit(event)` (line 346-349) — appends to the audit
log, and if metrics are configured, `_record_metric()` (line 351-373)
increments the matching Prometheus counter. This is the *one* chokepoint
every domain event in this whole pipeline passes through — which is
exactly why Phase 7c's metrics work never had to touch the actual
decision logic anywhere in this file.

**In plain English, the whole flow was:** a `Recommendation` became a
`Command`, then had to survive four independent gates in strict order —
policy, safety, risk, and (if risk or confidence demanded it) human
approval — any one of which can stop it dead with its own terminal
status. Only a command that cleared every gate reaches real dispatch, and
even then, "dispatched successfully" isn't enough — a fresh telemetry
reading has to actually confirm the expected physical change before the
command is allowed to call itself complete.

---

## 4. The decision engine's actual rules

Starting point: `self.decision_engine.recommend(context)` from Trace 2,
Step C. `decision_engine` is a `RuleBasedOptimiser`.

**`src/solarops/decision/application/rule_based_optimiser.py:68-107` → `recommend()`**

```python
candidates = [c for c in (
    self._reliability_candidate(context),      # priority 2
    self._battery_health_candidate(context),     # priority 3
    self._self_consumption_candidate(context),    # priority 4
    self._cost_candidate(context),                  # priority 5
) if candidate is not None]

safe, vetoed = self._apply_safety_filter(candidates, context)
safe.sort(key=lambda c: c.priority)

if not safe:
    safe = [self._safe_default(context, vetoed)]

confidence = self._confidence_estimator.estimate(context)
if confidence.band is ConfidenceBand.LOW and safe[0].priority != 2:
    safe[0] = self._make_conservative(safe[0])
```

Here's the real if/then logic, one priority at a time, in the order the
code actually checks them:

### Priority 2 — reliable power to loads (`_reliability_candidate`, line 133-171)
```python
if state.grid_status is GridStatus.CONNECTED or state.building_load.value <= 0:
    return None    # only fires during an actual outage with real load to serve
```
- **If** the grid is down **and** there's real load to serve: check
  `battery_soc - min_soc >= reliability_min_discharge_margin_pct` (5.0 by
  default). **If margin is enough** → propose `DISCHARGE_BATTERY` at
  `min(building_load, max_discharge_power)`.
- **Else** (not enough reserve to safely cover load) → propose
  `SHED_LOAD` at `load_shed_fraction_on_outage` (0.2 by default) instead.

### Priority 3 — battery health (`_battery_health_candidate`, line 174-216)
```python
if soc < self._config.battery_healthy_min_soc_pct:      # default 30%
    ...propose CHARGE_BATTERY...
if soc > self._config.battery_healthy_max_soc_pct and building_load > 0:  # default 85%
    ...propose DISCHARGE_BATTERY...
```
- **If** SOC is below 30%: charge from solar surplus if there is any,
  otherwise from the grid (`reserve_charge_power_kw`, 10.0 default) — but
  **only if** there's a surplus or the grid is up; if neither, returns
  `None` rather than inventing a source.
- **Else if** SOC is above 85% and the building has real load: discharge
  to serve it.
- **Else**: no candidate at this priority.

### Priority 4 — solar self-consumption (`_self_consumption_candidate`, line 219-259)
```python
net = state.solar_power.value - state.building_load.value
if net > self._config.self_consumption_min_surplus_kw:      # default 0.5kW
    ...propose CHARGE_BATTERY at min(net, max_charge_power)...
if net < -self._config.self_consumption_min_surplus_kw:
    ...propose DISCHARGE_BATTERY at min(deficit, max_discharge_power)...
```
Plain English: if solar is comfortably outproducing the building, store
the surplus instead of exporting it. If solar is comfortably
underproducing, use stored solar to cover the gap instead of importing.

### Priority 5 — minimise cost (`_cost_candidate`, line 262-291)
```python
if state.grid_power.value <= 0: return None     # not currently importing
margin = battery_soc - min_soc
if margin < self._config.cost_discharge_margin_pct: return None   # default 10%
...propose DISCHARGE_BATTERY at min(grid_power, cost_discharge_power_kw=5.0, max_discharge_power)...
```
Only fires while actively importing from the grid, and only if the
battery has real spare margin beyond what Priority 3 already wants to
protect.

### Priority 1 — safety, a filter not a generator (`_apply_safety_filter` / `_veto_reason`, line 294-348)
Every candidate above gets checked against `_veto_reason()` — e.g.
`CHARGE_BATTERY` is vetoed if SOC is already at/over policy max, or
battery temp is at/over its cap, or the site is in maintenance mode;
`DISCHARGE_BATTERY` is vetoed if SOC is already at/under policy min.
Vetoed candidates never reach the ranked list — they become `risks` in the
final explanation instead (line 411).

### Picking the winner
```python
safe.sort(key=lambda c: c.priority)      # never re-ordered by anything else
if not safe:
    safe = [self._safe_default(context, vetoed)]
```
Whatever survives priorities 2-5's proposals *and* the safety filter gets
sorted purely by priority number — 2 always beats 3, 3 always beats 4, no
exceptions, no magnitude comparison across different candidates. If
*everything* got vetoed, `_safe_default()` (line 350-391) falls back to
`SHED_LOAD` (if the grid is down and shedding is policy-permitted) or
`HOLD_BATTERY` — the one candidate that's always safe because it does
nothing.

### The one exception to "priority order is never disturbed"
```python
if confidence.band is ConfidenceBand.LOW and safe[0].priority != 2:
    safe[0] = self._make_conservative(safe[0])
```
Under Low confidence (see Trace 5's `ConfidenceEstimator` weights),
`_make_conservative()` (line 109-130) scales the **winning candidate's own
magnitude** down by `confidence_low_conservative_scale` (0.5 by default) —
same action, smaller number — never substitutes a different, lower-ranked
candidate. Priority 2 is explicitly exempt: it's driven by *current*
telemetry (is the grid down right now?), never a forecast, so
forecast-driven uncertainty is irrelevant to it.

**In plain English, the whole flow was:** four independent rules each look
at the current reading and propose at most one action apiece — outage
reliability, keeping the battery in a healthy band, using solar instead of
wasting it, and shaving grid costs — and safety silently vetoes any
proposal that would violate a hard limit before any of them are ranked.
Whatever's left gets sorted strictly by priority number, never by which
number looks "smaller" or "safer" — and only *after* that ranking is
final does low confidence get one narrow chance to shrink the winning
action's own size, never to swap in a different one.

---

## 5. The composition root

This is the "how does all of the above actually get built and connected"
trace — `src/solarops/platform/api_composition.py:130-259`,
`SystemComposition.__init__`, read top to bottom exactly as it executes.

```python
self.twin = DigitalTwin(site_config=site_config, ..., start_time=datetime.now(UTC))   # 139
self.telemetry_source = TwinTelemetrySource(self.twin)                                  # 144
self.ingestion = TelemetryIngestionService(self.telemetry_source, clock)                 # 145
self.state_store = (
    RedisStateStore(redis.Redis.from_url(self.settings.redis_url))                        # 147
    if self.settings.use_real_infra else InMemoryStateStore()
)
```
Lines 139-152: build the twin, wrap it in a `TelemetrySource`, and decide
**right here** — via `self.settings.use_real_infra`, which is
`SOLAROPS_ENV == "production"` — whether `state_store` (Trace 1's `self._store`)
is real Redis or a plain dict.

```python
self.policy = build_policy(site_config)                # 155
self.safety_limits = build_safety_limits(site_config)     # 156
self.policy_repository = InMemoryPolicyRepository()
self.policy_repository.save(self.policy)
self.safety_limits_provider = StaticSafetyLimitsProvider(self.safety_limits)
```
Lines 155-159: `build_policy`/`build_safety_limits`
(`platform/safety_wiring.py`) translate the twin's own `SiteConfig`
numbers into Safety's own `Policy`/`SafetyLimits` objects — this is where
Trace 3's `PolicyValidator`/`SafetyValidator` get their real numbers from.

```python
self.forecast_registry = (
    MLflowModelRegistry(self.settings.mlflow_tracking_uri)                                # 169
    if self.settings.use_real_infra else InMemoryModelRegistry()
)
...
forecast_training_service.evaluate_and_register(SolarBaseline(...))                        # 181
```
Lines 166-193: same real-vs-fake switch for the model registry, then
**the tryout happens right here, at boot** — `evaluate_and_register` runs
`SolarBaseline` through the accuracy gate and only registers it if it
passes (which is why Trace 2's `self.solar_forecaster.forecast(state)`
ever finds anything).

```python
self.anomaly_registry = (
    MLflowDetectorRegistry(self.settings.mlflow_tracking_uri)                              # 201
    if self.settings.use_real_infra else InMemoryDetectorRegistry()
)
...
detector_training_service.evaluate_and_register(RuleDetector(self.anomaly_config))          # 211
detector_training_service.evaluate_and_register(StatisticalDetector(self.anomaly_config))    # 212
```
Lines 198-215: identical tryout pattern for the two anomaly detectors that
actually pass their gate.

```python
self.operating_constraints = build_operating_constraints(self.policy, self.safety_limits)   # 218
self.decision_engine = RuleBasedOptimiser(RuleEngineConfig(), clock)                          # 219
```
Line 218-219: Decision gets its own copy of the operating limits (never
reads `Policy`/`SafetyLimits` directly — it isn't allowed to import
Safety), and the engine from Trace 4 is built with its config.

```python
self.hardware = SimulatedHardwareInterface(self.twin)                                       # 222
...
self.audit_log = (
    PostgresAuditLog(create_engine(self.settings.postgres_dsn))                             # 236
    if self.settings.use_real_infra else InMemoryAuditLog()
)
self.execution_pipeline = ExecutionPipeline(
    command_planner=CommandPlanner(clock),
    policy_validator=PolicyValidator(self.policy_repository, clock),
    safety_validator=SafetyValidator(self.safety_limits_provider, self.state_store, clock),
    risk_assessor=RiskAssessor(clock),
    approval_engine=ApprovalEngine(self.approval_repository, clock),
    execution_manager=ExecutionManager(self.hardware, clock),
    verification_service=VerificationService(self.state_manager, clock),
    ...
    telemetry_refresh=self.refresh_telemetry,
    metrics=PIPELINE_METRICS,
)                                                                                              # 240-257
```
Lines 222-257: the real-vs-fake switch for the hardware interface and the
audit log, then **every single object Trace 3 walked through** gets
constructed and handed to one `ExecutionPipeline` — this block *is* Trace
3's entire cast of characters, assembled in one place. Note
`telemetry_refresh=self.refresh_telemetry` — this is how
`_dispatch_and_verify()` (Trace 3, Stage 5) is able to call a fresh
telemetry pull before verifying, without `execution_pipeline.py` ever
importing `platform`.

```python
self.refresh_telemetry()  # a real reading before any request arrives      # 259
```
Line 259: the very last thing the constructor does — one real cycle of
Trace 2's Step A, so the very first HTTP request never sees an empty state.

**Where this actually gets called from:** `src/solarops/api/app.py`'s
`lifespan()` function —
```python
app.state.composition = build_system_composition()
```
— run once, when Uvicorn starts the process. `build_system_composition()`
(`api_composition.py:364-367`) reads `PlatformSettings()` from the
environment if none is passed, which is how a bare `SOLAROPS_ENV=production`
in the shell (or `docker-compose.yml`) ends up deciding every real-vs-fake
choice throughout this whole constructor, with zero code changes.

**In plain English, the whole flow was:** one constructor, run exactly
once at process startup, builds the fake site, translates its settings
into every other context's own vocabulary, runs the forecast/anomaly
tryouts, and assembles the entire four-gate execution pipeline — deciding,
at every single infrastructure choice point, real vs. in-memory purely
based on one environment variable — then takes one real reading before
handing itself off to the FastAPI app to live for the rest of the process.

---

## 6. How to make common changes

| I want to... | Go here |
|---|---|
| Change a hard safety limit (max battery temp, max charge power, ...) | `src/solarops/platform/safety_wiring.py::build_safety_limits()` — reads from `SiteConfig`, so also check `src/solarops/simulation/infrastructure/config.py::SiteConfig` for the underlying number |
| Change a *policy* (operator-adjustable) limit, like min/max battery SOC | `src/solarops/platform/safety_wiring.py::build_policy()` |
| Change a decision rule's threshold (e.g. what counts as "healthy" SOC) | `src/solarops/decision/infrastructure/config.py::RuleEngineConfig` — every tunable in one place, never hardcoded in the optimiser itself |
| Change the decision rules' actual logic | `src/solarops/decision/application/rule_based_optimiser.py` — one `_..._candidate()` method per priority (Trace 4) |
| Change confidence scoring weights | `RuleEngineConfig.confidence_weight_*` fields, same file as above |
| Add a new API endpoint | New route in the matching `src/solarops/api/routers/*.py` file (or a new router file, registered in `src/solarops/api/app.py`); add a Pydantic schema in `src/solarops/api/schemas/` if it returns something new |
| Add a new Prometheus metric | Define it in `src/solarops/observability/metrics.py`; increment it wherever the event actually happens — either directly (Telemetry/Forecast/Anomaly, in `api_composition.py::refresh_telemetry()`) or via `PipelineMetrics` (Execution, in `execution_pipeline.py::_record_metric()`) |
| Add a new dashboard page | New file in `dashboard/pages/`, add it to the nav list in `dashboard/app.py`; it should only ever call `dashboard/api_client.py`, never import `solarops` |
| Change what a command's dispatch actually does (simulated hardware) | `src/solarops/platform/twin_hardware_interface.py::SimulatedHardwareInterface.send()` |
| Change how many times a dispatch retries | `src/solarops/execution/application/execution_manager.py::DEFAULT_MAX_RETRIES` |
| Change the approval timeout | `src/solarops/execution/application/approval_engine.py::DEFAULT_APPROVAL_TIMEOUT` |
| Switch real vs. in-memory infrastructure | `SOLAROPS_ENV` environment variable (`local`/`production`) — never a code change; see `src/solarops/platform/settings.py::PlatformSettings` |
| Add a real database table/adapter | Follow `src/solarops/execution/infrastructure/postgres_audit_log.py` as the template — SQLAlchemy Core, wired in via a ternary in `api_composition.py`, same pattern as the existing real/fake switches |

**Before committing any change:** run `pytest`, `ruff check .`, and
`lint-imports` (see `README.md`'s "Running the tests" section) — the last
one specifically catches the most common mistake when adding something
new: accidentally importing a context you're not allowed to.
