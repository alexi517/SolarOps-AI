"""Safety bounded context (Document 8 §6.4) — Core.

Two independent gates: PolicyValidator (operational rules, configurable) and
SafetyValidator (hard physical limits, never relaxed) — see A.1 of
docs/phase5-command-safety-pipeline-brief.md. RiskAssessor classifies into the
shared kernel's RiskLevel. Execution context (Phase 5 Part B) is the customer.
"""
