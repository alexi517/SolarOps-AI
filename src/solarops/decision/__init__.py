"""Decision bounded context (Document 8 §6.3) — Core.

Owns the ``Recommendation`` aggregate and the ``OptimisationEngine`` roadmap.
Reasons only — never issues commands, never touches the Digital Twin (ADR-010,
Phase 6c brief §0). ``RuleBasedOptimiser`` (v1, Phase 6c) is the first real
implementation, behind an interface that also defines v2 (constraint
optimisation) / v3 (MPC) / v4 (RL) as unimplemented shells
(``application/engine_shells.py``).
"""
