# Phase 5 Brief — Command Execution & Safety Pipeline

**For:** Claude Code (or manual execution)
**Contexts:** Safety + Execution — the two **core** contexts, the "crown jewel."
**Source of truth:** Document 7 (CESF) and Document 8 (DDD spec) §6.4, §6.5, §7.
**Build order:** Two verified halves. Complete and green-light **Part A (Safety)**
before starting **Part B (Execution)**. Report after each part; change nothing
outside the brief without flagging it.

This is the most safety-critical phase in the project. Do not guess. Where a
value or rule is not specified, read it from configuration or ask — never invent
a silent default in the validators.

---

## 0. Non-negotiables (from the CESF ADRs and success criteria)

These are structural guarantees, not aspirations. Every one must be enforced in
code and covered by a test.

1. **Fail-safe by default (ADR-012).** If any critical component (especially the
   safety validator) is unavailable or cannot evaluate, the command is
   **rejected**, never executed. Use the existing `FailSafeTriggered`. There is
   no "assume safe on error" branch anywhere.
2. **Mandatory verification (ADR-011).** A command is `COMPLETED` only after
   telemetry confirms the expected physical change. An acknowledgement from the
   hardware interface is **not** success.
3. **Reasoning/execution separation (ADR-010).** Execution consumes a
   `Recommendation`; the AI never dispatches. Already holds — keep it.
4. **100% of unsafe commands blocked.** Safety validation is a hard gate; any
   single failed check blocks execution.
5. **No duplicate execution.** Every command carries an idempotency key;
   duplicates are rejected.
6. **Risk policy (CESF §8):** CRITICAL → auto-reject (never dispatched);
   HIGH → manual approval; MEDIUM → notify operator, then proceed; LOW → auto.
   This already lives on `RiskLevel` in the shared kernel — use those properties.
7. **Complete, immutable audit trail (§15).** Every state transition emits a
   domain event and writes an append-only audit entry. **No command can be
   deleted.**
8. **Single hardware path (§16).** Only the Execution Manager calls the
   `HardwareInterface`.
9. **Limits are data, never magic numbers.** All policy and safety thresholds
   come from configuration / the `Policy` aggregate, injected at startup. The
   Safety context must not import `solarops.simulation`.

---

# PART A — Safety context (`src/solarops/safety/`)

Three inspectors, each a pure, independently testable service.

## A.1 Two different kinds of limit — keep them separate

The CESF defines **two distinct gates** and they must not be merged:

- **Policy validation (§6)** — *operational* rules an operator can configure or
  temporarily relax: target max SOC, maintenance mode (no charging), protected
  critical loads (cannot interrupt), operator overrides / temporary restrictions.
- **Safety validation (§7)** — *hard physical* limits that are **never** relaxed:
  the final technical gate.

Policy can say "no". Safety can also say "no", and nothing overrides it.

## A.2 Domain (`safety/domain/`)

- `policy.py` — `Policy` aggregate root: the site's configurable operational
  rules (max/min SOC targets, maintenance-mode flag, protected critical loads,
  active operator overrides). Versioned.
- `safety_limits.py` — the hard physical limits (a value object or part of
  `Policy`): battery max/min SOC, max temperature, max current, max charge rate;
  inverter max power, max voltage, max current, allowed operating modes; grid
  required availability and voltage/frequency tolerances; building critical-load
  requirements.
- `safety_assessment.py` — `SafetyAssessment` VO: `passed: bool`,
  `failed_checks: tuple[str, ...]`, and the values evaluated. Immutable.
- `risk_assessment.py` — `RiskAssessment` VO: `level: RiskLevel`,
  `factors: tuple[str, ...]` explaining the rating.
- `ports.py` — `PolicyRepository` protocol (and a `SafetyLimitsProvider` if
  limits are separate).
- `events.py` — `PolicyViolated`, `CommandBlockedBySafety`, `RiskAssessed`.

## A.3 Application (`safety/application/`)

- `policy_validator.py` — checks a planned command against the `Policy` (§6).
  Honours maintenance mode, max-SOC target, protected critical loads, operator
  overrides. Returns pass, or a failure carrying a `PolicyViolation` reason.
- `safety_validator.py` — the **final technical gate** (§7). Reads the current
  `EnergyState` (real conditions: battery temp, grid availability, etc.) **and**
  the command's intended effect, and evaluates every hard limit in A.2. Any
  failed check → `BLOCKED`. **Fail-safe:** if it cannot evaluate (missing data,
  internal error, limits unavailable) → treat as BLOCKED and raise
  `FailSafeTriggered`. Never pass on uncertainty.
- `risk_assessor.py` — classifies into a `RiskLevel` from the CESF §8 factors.
  **This is the one component with genuine design latitude** — the CESF lists
  factors but no formula. Implement a simple, transparent, table-driven v1
  heuristic and document each rule. Suggested v1 mapping (tunable):
  - **CRITICAL** — asset in EMERGENCY / fault / offline mode; or the action sits
    at the very edge of a hard safety limit (near-zero margin) even though it
    passed; or a grid-dependent action during a grid outage/instability.
  - **HIGH** — battery discharge that would drop reserve below a policy floor; a
    large power swing (e.g. > 50% of rated); high forecast uncertainty; asset in
    MAINTENANCE.
  - **MEDIUM** — routine action with a modest safety margin / moderate impact.
  - **LOW** — routine action, comfortable margin, normal operating state.

  Note: forecast uncertainty is not available until Phase 6. Accept it as an
  optional input that defaults to "unknown → treat conservatively."

## A.4 Infrastructure & wiring

- In-memory `PolicyRepository`.
- The `Policy` and safety limits are **constructed at the platform composition
  root** from the site's configuration (reuse the existing `SiteConfig` values
  from Phase 2 so the numbers are not duplicated or invented), then injected.
  The Safety context receives them as data — it never imports `simulation`.

## A.5 Verify Part A before continuing

- Unit tests: policy pass; each policy-block case; safety pass; **each individual
  safety-block case**; the fail-safe case (validator can't evaluate → BLOCKED);
  risk-assessor mapping for each level.
- `pytest`, `ruff`, `lint-imports` green. Add a contract: `solarops.safety` may
  depend only on `shared_kernel` and `telemetry` (it reads `EnergyState` — an
  Open Host Service relationship, like Decision).
- **Report which files you created and the test results. Stop and wait.**

---

# PART B — Execution context (`src/solarops/execution/`)

The command lifecycle and the pipeline that drives it.

## B.1 Ports — resolve this first (avoids an import-linter wall)

The `HardwareInterface` port must live where **Execution** can import it without
importing `simulation`. If it currently lives in `simulation/`, **move the
Protocol to `execution/domain/ports.py`** (the consumer owns the port). The
concrete twin adapter that implements it moves to / stays in the platform
composition root, which may import both `execution` (for the Protocol) and
`simulation` (for the twin). Same pattern already used for telemetry's
`TelemetrySource`. Confirm with `lint-imports`.

## B.2 Domain (`execution/domain/`)

- `command.py` — `Command` aggregate root. **Owns the lifecycle state machine**
  (Doc 8 §7). Carries: `command_id`, `site_id`, `asset_id`, originating
  `recommendation_id`, action + params (e.g. `target_soc`), `idempotency_key`,
  `trace_id`, timestamps, and the gate outcomes as attached VOs. **No external
  code sets `status` directly** — transitions happen through aggregate methods,
  and an illegal transition raises `InvalidStateTransition`. Enforce the §7
  invariants: cannot dispatch unless policy + safety passed and approved;
  CRITICAL → auto-reject; `COMPLETED` requires a passing `VerificationResult`;
  duplicate idempotency key → `DuplicateCommandError`.
- `command_plan.py` — `CommandPlan` VO (planner output).
- `approval_request.py` — `ApprovalRequest` aggregate (separate, per ADR-017):
  pending → approved / rejected / modified / expired; operator identity; timeout.
  `ApprovalDecision` VO.
- `execution_result.py`, `verification_result.py` — VOs.
- `ports.py` — `CommandRepository`, `ApprovalRequestRepository`,
  `HardwareInterface` (see B.1), `TelemetryReader` (reads `EnergyState` for
  verification).
- `events.py` — the full set: `CommandCreated`, `CommandValidated`,
  `CommandBlockedBySafety`, `RiskAssessed`, `ApprovalRequested`,
  `CommandApproved`, `CommandRejected`, `CommandDispatched`,
  `CommandAcknowledged`, `CommandExecuted`, `CommandFailed`, `CommandTimedOut`,
  `ExecutionVerified`, `VerificationFailed`, `CommandCompleted`,
  `CommandCancelled`.

## B.3 Application (`execution/application/`)

- `command_planner.py` — `Recommendation` → `CommandPlan` → `Command`
  (`CREATED` → `PLANNED`). Assigns unique ID, idempotency key, trace ID,
  timestamp (§5).
- `approval_engine.py` — LOW/MEDIUM → `AUTO_APPROVED` (MEDIUM also emits an
  operator notification); HIGH → create `ApprovalRequest`, set
  `AWAITING_APPROVAL`, pause; CRITICAL never reaches here (rejected at risk).
  Applies an operator decision (approve / reject / modify target).
- `execution_manager.py` — **the only caller of `HardwareInterface`.** Handles
  dispatch, acknowledgement tracking, retries with exponential backoff on
  timeout, duplicate prevention (idempotency), and outcomes (Success / Failed /
  Timed Out / Cancelled / Blocked) (§10, §14). Fail-safe on component
  unavailability.
- `verification_service.py` — after execution, read telemetry via
  `TelemetryReader` and confirm the expected change within a time window (e.g.
  charge current increases, SOC rises, inverter reports charging) (§12). Pass →
  `VERIFIED` → `COMPLETED`. Fail → `VerificationFailed`, raise an alert/incident,
  mark failed. **Acknowledgement alone never completes a command.**
- `execution_pipeline.py` — orchestrates the full CESF §3 flow:
  recommendation → plan → policy → safety → risk → approval → execute → verify →
  audit → update state. Terminates safely at any gate failure (§13). Emits an
  event and writes an immutable audit entry at **every** transition.

## B.4 Infrastructure & wiring

- In-memory `CommandRepository`, `ApprovalRequestRepository`.
- Append-only audit log: supports write + read only, **no delete** (§15).
- The pipeline that spans contexts is wired at the platform composition root.

## B.5 Import rules

`solarops.execution` may depend on `shared_kernel`, `decision` (for the
`Recommendation` published-language type), `safety`, and `telemetry`. It must
**not** import `simulation` (it reaches the twin only through the
`HardwareInterface` port, wired at platform). Add the contract and confirm.

## B.6 Verify Part B

- **Happy path:** a safe LOW-risk command flows CREATED → … → COMPLETED, with
  verification confirming the change.
- **Each gate failure terminates correctly:** policy reject, safety block,
  CRITICAL reject, operator reject, dispatch failure, timeout, verification fail.
- **Fail-safe:** safety validator unavailable → command rejected.
- **Idempotency:** duplicate command rejected.
- **Approval:** HIGH pauses; approve resumes to completion; reject terminates;
  modify adjusts the target.
- **Verification is mandatory:** a command whose hardware acknowledges but whose
  telemetry does **not** change ends `VERIFICATION_FAILED`, not `COMPLETED`.
- **Audit:** every command has a full trail; deletion is impossible.
- **Two end-to-end scripts:** (1) real `EnergyState` → stub recommendation →
  full pipeline → twin executes → verified → completed; (2) an unsafe command
  that is blocked at the safety gate and never reaches the twin.
- `pytest`, `ruff`, `lint-imports` all green.

---

## Definition of done (the CESF §19 success criteria)

- 100% of unsafe commands are blocked.
- Every command has a complete, immutable audit trail.
- Verification confirms the real state change before a command is `COMPLETED`.
- Human approval is enforced according to the risk policy.
- The Digital Twin is reached only through the `HardwareInterface` port, so it
  could be swapped for real hardware without touching pipeline logic.
- The system stays safe under component outages (fail-safe) and duplicate/timeout
  conditions.
