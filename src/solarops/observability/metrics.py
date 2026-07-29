"""Prometheus metric definitions (CESF §17, Document 6 §11 — Phase 7c brief).

Every ``Counter``/``Histogram``/``Gauge`` below is a module-level singleton,
created once when this module is first imported — the standard
``prometheus_client`` pattern, and why building a fresh ``SystemComposition``
never risks a "duplicated timeseries" error: every instance shares the same
global objects, which is also what makes them meaningful to scrape.

This is a leaf module — it imports nothing from any ``solarops`` context.
Application services never import it directly; ``platform/api_composition.py``
(the composition root) wires ``PipelineMetrics`` into ``ExecutionPipeline``
the same way it already wires in ``audit_log``/``clock``/``hardware_interface``,
and calls the recording functions below directly for Telemetry/Forecast/
Anomaly/Decision, whose own application services stay untouched. Every
context's import-linter contract already forbids depending on
``solarops.observability`` (checked — pre-existing, alongside `api`/
`platform`/`workflow`), which this design never needs anyway.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

__all__ = [
    "PipelineMetrics",
    "PIPELINE_METRICS",
    "commands_auto_rejected_by_confidence_total",
    "recommendation_latency_seconds",
    "forecasts_produced_total",
    "anomalies_detected_total",
    "registered_model_versions",
    "telemetry_updates_total",
    "api_requests_total",
    "api_request_latency_seconds",
]

# --- Execution (CESF §17) ---

commands_issued_total = Counter(
    "solarops_commands_issued_total",
    "Commands created by the execution pipeline.",
)
commands_blocked_by_safety_total = Counter(
    "solarops_commands_blocked_by_safety_total",
    "Commands blocked by a hard safety check.",
)
commands_rejected_total = Counter(
    "solarops_commands_rejected_total",
    "Commands rejected, by reason.",
    ["reason"],
)
commands_auto_rejected_by_confidence_total = Counter(
    "solarops_commands_auto_rejected_by_confidence_total",
    "Commands auto-rejected by low confidence alone (no such path exists yet).",
)
# TODO(6d-confidence-auto-reject): Phase 6d's confidence rule (Document 9 §8)
# only ever *escalates* an otherwise-auto command to human approval — there
# is no code path where low confidence alone auto-rejects one. Declared per
# the brief's own instruction ("add the metric, leave it at zero, never
# fake it") — nothing increments this counter today.

approvals_required_total = Counter(
    "solarops_approvals_required_total",
    "Commands that paused awaiting human approval.",
)
approvals_approved_total = Counter(
    "solarops_approvals_approved_total",
    "Commands approved by a real human operator (excludes AUTO_APPROVED).",
)
approval_wait_time_seconds = Histogram(
    "solarops_approval_wait_time_seconds",
    "Time between an approval being requested and a human deciding it.",
)
execution_latency_seconds = Histogram(
    "solarops_execution_latency_seconds",
    "Time between dispatch and hardware acknowledgement.",
)
command_retry_count = Histogram(
    "solarops_command_retry_count",
    "Number of retries a command's dispatch required.",
    buckets=(0, 1, 2, 3, 4, 5),
)
commands_failed_total = Counter(
    "solarops_commands_failed_total",
    "Commands that failed during dispatch or execution.",
)
commands_timed_out_total = Counter(
    "solarops_commands_timed_out_total",
    "Commands that timed out, by stage.",
    ["stage"],
)
verification_failures_total = Counter(
    "solarops_verification_failures_total",
    "Commands whose post-execution telemetry did not confirm the expected state.",
)
commands_completed_total = Counter(
    "solarops_commands_completed_total",
    "Commands that completed successfully.",
)


class PipelineMetrics:
    """The real ``prometheus_client``-backed implementation of Execution's own
    ``ExecutionMetricsRecorder`` Protocol (``execution/domain/ports.py``) —
    satisfied structurally, no inheritance, no import of Execution needed
    here. Constructed once and injected by ``platform/api_composition.py``,
    the composition root already allowed to import both.
    """

    def command_issued(self) -> None:
        commands_issued_total.inc()

    def command_blocked_by_safety(self) -> None:
        commands_blocked_by_safety_total.inc()

    def command_rejected(self, reason: str) -> None:
        commands_rejected_total.labels(reason=reason).inc()

    def approval_required(self) -> None:
        approvals_required_total.inc()

    def approval_approved(self) -> None:
        approvals_approved_total.inc()

    def approval_wait_time(self, seconds: float) -> None:
        approval_wait_time_seconds.observe(seconds)

    def execution_latency(self, seconds: float) -> None:
        execution_latency_seconds.observe(seconds)

    def retry_count(self, count: int) -> None:
        command_retry_count.observe(count)

    def command_failed(self) -> None:
        commands_failed_total.inc()

    def command_timed_out(self, stage: str) -> None:
        commands_timed_out_total.labels(stage=stage).inc()

    def verification_failed(self) -> None:
        verification_failures_total.inc()

    def command_completed(self) -> None:
        commands_completed_total.inc()


PIPELINE_METRICS = PipelineMetrics()


# --- AI / model (Document 6 §11) ---

recommendation_latency_seconds = Histogram(
    "solarops_recommendation_latency_seconds",
    "Time to produce a ranked recommendation list.",
)
forecasts_produced_total = Counter(
    "solarops_forecasts_produced_total",
    "Forecasts produced, by kind.",
    ["kind"],
)
anomalies_detected_total = Counter(
    "solarops_anomalies_detected_total",
    "Anomalies detected, by type and severity.",
    ["anomaly_type", "severity"],
)
registered_model_versions = Gauge(
    "solarops_registered_model_versions",
    "1 if this model/version is currently registered and active.",
    ["context", "model_name", "version"],
)

# --- API / ops (Document 6 §11) ---

api_requests_total = Counter(
    "solarops_api_requests_total",
    "API requests, by method/route/status.",
    ["method", "route", "status"],
)
api_request_latency_seconds = Histogram(
    "solarops_api_request_latency_seconds",
    "API request latency, by method/route.",
    ["method", "route"],
)
telemetry_updates_total = Counter(
    "solarops_telemetry_updates_total",
    "Telemetry readings ingested.",
)
