# Phase 6c Brief — Optimisation Engine (the Decision Brain)

**For:** Claude Code (or manual execution)
**Scope:** The optimisation engine — Version 1 (deterministic rule engine) — plus
the interfaces for v2–v4. This replaces the Phase 4 stub `OptimisationAgent`.
**Source of truth:** the architecture documents.

**IMPORTANT — save this file to `docs/phase6c-optimisation-engine-brief.md` before
building.** Read it alongside `docs/08-domain-driven-design-spec.md` and
`docs/06-AI-Evaluation-Framework.md` (§6 Decision Quality, §8 Explainability).

## 0. The one hard rule (non-negotiable)
**The optimisation engine outputs recommendations ONLY. It must never construct
executable commands, and it must never touch the Digital Twin.** Command
generation and execution remain entirely inside the Command Execution Framework
(Phase 5). The brain reasons; the pipeline decides whether and how to act. This is
ADR-010 and it is the spine of the whole project — do not violate it.

## 1. Principles to preserve
- **Reason only** (see rule 0).
- **Every recommendation is explainable** — per Document 6 §8 it must answer:
  why, why now, what evidence, what alternatives, what risks.
- **Observable** (emits an event) and **auditable**.
- **Roadmap-ready:** v1 is a rule engine; the interface must let constraint
  optimisation (v2), MPC (v3), and RL (v4) slot in later **without changing
  anything downstream**. Define those interfaces now; implement only v1.

## 2. Where it lives
The existing Decision context (`src/solarops/decision/`). It already holds
`Recommendation` and the stub `OptimisationAgent` from Phase 4 — this phase
replaces the stub with the real engine. Decision may depend on `shared_kernel`,
`telemetry` (reads `EnergyState`), and `forecast` (reads forecasts) — the
contracts already permit this. It must **not** import `execution` or `simulation`.

## 3. The pluggable engine interface (enables the v1→v4 roadmap)
- `OptimisationEngine` (Protocol): `recommend(context) -> RankedRecommendations`.
- `DecisionContext` (VO): the inputs the engine reasons over — current
  `EnergyState`, available `Forecast`s, active `Policy` limits (read-only), and
  operating constraints.
- Implementations:
  - `RuleBasedOptimiser` (v1) — **implement this**.
  - `ConstraintOptimiser` (v2, OR-Tools), `MpcOptimiser` (v3), `RlOptimiser`
    (v4) — **interface/class shells only, not implemented.** v4 is an explicit
    placeholder.

## 4. Output shape (Document 6 §6 & §8)
- `RankedRecommendations` — an ordered list, best first.
- Each `Recommendation` (extend the Phase 4 type as needed) carries:
  `action` (`ActionType`), `confidence`, `expected_benefit`, `risks`, and a
  `rationale`/explanation that answers the five §8 questions, plus the
  `alternatives` considered. Ranking reflects the priority order in section 5.

## 5. The v1 rule engine — decision priorities (DECIDED)
Reason strictly in this priority order (from your instruction; put all thresholds
in config so they're tunable):
1. **System safety** — never recommend anything that current state makes unsafe
   (e.g. don't recommend charging a battery already at/over max SOC or overheating).
2. **Reliable power to loads** — keep critical/building load served.
3. **Battery health** — respect SOC reserve and healthy operating band.
4. **Maximise solar self-consumption** — prefer using on-site solar over export.
5. **Minimise imported energy and operating cost.**

The engine evaluates the situation against these in order and emits the
recommendation(s) that best satisfy them, each with its rationale. Where two
actions are viable, rank by the priority they serve.

Note: the engine reasons about safety to make *sensible* recommendations, but it
is **not** the safety authority — the Safety context (Phase 5) independently
re-checks everything. Two layers, on purpose.

## 6. Honest input constraint (from 6a — must be handled explicitly)
Only the **solar** forecast is production-registered today; the **load** and
**battery-SOC** forecasts do not yet meet their accuracy targets and are not
available. The engine must:
- Degrade gracefully: reason from current `EnergyState` + whatever forecasts are
  actually registered, not assume all three exist.
- State this in the rationale when a decision would have used a missing forecast
  (e.g. "load forecast unavailable; using current load only").
- Never fabricate a forecast it doesn't have.
Log this dependency in `docs/deferred-items.md` if not already captured.

## 7. Evaluation (Document 6 §6 Decision Quality)
- Build the evaluation hooks: Decision Accuracy, Recommendation Ranking Quality,
  Confidence Calibration, measured against the twin benchmark scenarios' expected
  responses (§9) where those expected responses are defined.
- Where §9's "expected AI response" per scenario isn't spelled out numerically,
  leave a `TODO(expected-decisions)` seam rather than inventing the expected
  answer — same discipline as prior phases. Do not fabricate the ground truth.

## 8. Wiring (LangGraph)
Replace the stub decision node in the existing `workflow/` graph so the graph now
calls `RuleBasedOptimiser` and passes its top recommendation onward exactly as the
stub did — the plumbing from Phase 4 stays; only the brain behind the node
changes. Confirm the end-to-end path still runs:
real `EnergyState` (+ solar forecast) → engine → ranked recommendations → (into
the Phase 5 pipeline, which independently safety-checks them).

## 9. Definition of done (6c)
- `RuleBasedOptimiser` produces ranked, explainable recommendations following the
  section 5 priority order, each answering the §8 questions.
- v2/v3/v4 exist as interface shells behind the same `OptimisationEngine`
  interface — roadmap visible in code, unimplemented.
- The engine degrades gracefully with only the solar forecast available.
- It outputs recommendations only — no command construction, no twin access
  (confirm via `lint-imports`: Decision reaches neither `execution` nor
  `simulation`).
- The LangGraph node now uses the real engine; the end-to-end script shows a real
  `EnergyState` producing a reasoned recommendation that then enters the Phase 5
  safety pipeline.
- Decision-quality evaluation hooks exist; expected-decision ground truth is a
  marked seam where §9 doesn't specify it.
- `pytest`, `ruff`, `lint-imports` green.
- **Report:** files created, a plain-English walkthrough of how the engine makes
  and explains one real decision, confirmation it never builds a command or
  touches the twin, and test results. This completes Phase 6.