"""Execution bounded context (Document 8 §6.5) — Core, the "crown jewel".

Owns the `Command` aggregate and its full CESF §7 lifecycle state machine, the
separate `ApprovalRequest` aggregate (ADR-017), and the pipeline that drives a
`Recommendation` through policy -> safety -> risk -> approval -> dispatch ->
verify. `HardwareInterface` (ADR-015) is the only path to the Digital Twin.
"""
