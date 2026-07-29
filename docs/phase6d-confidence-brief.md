# Phase 6d Brief — Confidence Estimation & Auto-Escalation

**For:** Claude Code (or manual execution)
**Scope:** Add calculated confidence to recommendations, and make low confidence
force human approval. Decision-logic only — no new ML, no new context.
**Source of truth:** Document 9 (AIDES) §8 and §12; ADR-019.

**IMPORTANT — save this file to `docs/phase6d-confidence-brief.md` before building.**
Read it alongside `docs/09-AI-Intelligence-Decision-Engine.md` (§8, §12) and the
existing Decision and Execution code.

## 0. What this adds
Right now recommendations carry a confidence *value*, but it isn't *calculated*
from anything, and it doesn't affect approval. Document 9 §8 requires a real,
factor-based confidence score, and requires that **low confidence automatically
forces human approval**. This phase builds exactly that.

## 1. Confidence estimation (Decision context)
Add a `ConfidenceEstimator` in `src/solarops/decision/` that computes a score in
[0, 1] for each recommendation from the factors in §8, using only data already
available:
- **Forecast certainty** — how much the recommendation relied on forecasts, and
  their confidence. A decision leaning on an unavailable forecast (load/battery,
  which aren't registered) is *less* confident and must say so.
- **Data freshness** — how recent the `EnergyState` reading is (via the `Clock`).
  Stale state → lower confidence.
- **Model agreement / availability** — how many of the expected inputs were
  actually present vs missing.
- **Anomaly presence** — if the anomaly context is reporting an active anomaly on
  a relevant asset, confidence drops.

Keep the exact weighting in `RuleEngineConfig` (tunable, not hardcoded). The
estimator returns both the score and the **factors** that produced it, so the
explanation can show its working.

## 2. Confidence bands (§8)
- **High:** > 0.90
- **Medium:** 0.70–0.90
- **Low:** < 0.70

Put the thresholds in config. Attach the band and the contributing factors to the
`Recommendation` (extend the existing type additively; don't break its shape).

## 3. Auto-escalation — the important rule
Document 9 §8: low-confidence recommendations **automatically require human
approval.** This must combine with the existing Phase 5 risk-based approval, and
**confidence may only ever make the system more cautious, never less:**

> A recommendation requires human approval if **either** its risk level requires
> it (existing rule) **OR** its confidence is Low. Low confidence can escalate an
> otherwise-auto action to human approval; it can **never** downgrade a
> human-approval requirement to auto.

Wire this at the point where the approval path is decided (the `ApprovalEngine` /
the risk→approval decision). CRITICAL still auto-rejects regardless of confidence.
Concretely:
- Low confidence + otherwise-LOW/MEDIUM risk → **now requires human approval.**
- Any risk that already required approval → still does (unchanged).
- CRITICAL → still auto-rejected.

## 4. Conservative-under-uncertainty (§12)
Per Document 9 §12, when inputs are missing / models disagree / confidence is low,
the engine must **prefer conservative recommendations** and **never fabricate
missing information** (the latter already holds — keep it). "Conservative" here
means: prefer the lower-impact / safer candidate when confidence is Low (e.g.
prefer holding or a smaller action over a large one). Keep this rule simple,
explicit, and documented.

## 5. Explainability (§9)
The recommendation's explanation must now include:
- the confidence score and band,
- the factors that drove it (e.g. "load forecast unavailable → reduced
  confidence"),
- and, when auto-escalated, a clear statement: "escalated to human approval due to
  low confidence."

## 6. Honesty & scope
- Decision-logic only. No new ML model, no new bounded context, no import changes
  expected (Decision already reads telemetry/forecast; if it needs anomaly signal,
  reconsider — do **not** add a Decision→Anomaly import without flagging it first;
  prefer passing anomaly state in via the composition root).
- Extend existing types additively; keep all tests green.

## 7. Definition of done
- Every recommendation carries a **calculated** confidence score, band, and the
  factors behind it.
- Low confidence forces human approval, combined with risk so that confidence can
  only increase caution (proven with tests: a LOW-risk + low-confidence command
  now pauses for approval; a HIGH-risk command's approval requirement is unchanged;
  CRITICAL still auto-rejects).
- Under low confidence the engine prefers the more conservative candidate.
- Explanations state the confidence, its drivers, and any low-confidence
  escalation.
- `pytest`, `ruff`, `lint-imports` green.
- **Report:** files created/changed, a plain-English walkthrough of one
  recommendation getting a confidence score and being escalated for low confidence,
  confirmation confidence can never *reduce* required approval, and test results.