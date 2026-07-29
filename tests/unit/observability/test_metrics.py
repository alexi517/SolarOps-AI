"""observability/metrics.py — the metric definitions exist with the right
names/types, and PipelineMetrics genuinely satisfies Execution's own
ExecutionMetricsRecorder Protocol (structural, no inheritance)."""

from __future__ import annotations

from prometheus_client import generate_latest

from solarops.execution.domain.ports import ExecutionMetricsRecorder
from solarops.observability import metrics


def _exposition_text() -> str:
    return generate_latest().decode()


def test_pipeline_metrics_is_an_execution_metrics_recorder():
    recorder: ExecutionMetricsRecorder = metrics.PIPELINE_METRICS
    # Every Protocol method is callable without raising — this is the
    # structural-typing proof: nothing here imports Execution's Protocol
    # into metrics.py, it's just satisfied by having the right methods.
    recorder.command_issued()
    recorder.command_blocked_by_safety()
    recorder.command_rejected("policy")
    recorder.approval_required()
    recorder.approval_approved()
    recorder.approval_wait_time(1.23)
    recorder.execution_latency(0.5)
    recorder.retry_count(1)
    recorder.command_failed()
    recorder.command_timed_out("execution")
    recorder.verification_failed()
    recorder.command_completed()


def test_every_cesf_17_and_doc6_11_metric_name_is_exposed():
    text = _exposition_text()
    expected_names = [
        "solarops_commands_issued_total",
        "solarops_commands_blocked_by_safety_total",
        "solarops_commands_rejected_total",
        "solarops_commands_auto_rejected_by_confidence_total",
        "solarops_approvals_required_total",
        "solarops_approvals_approved_total",
        "solarops_approval_wait_time_seconds",
        "solarops_execution_latency_seconds",
        "solarops_command_retry_count",
        "solarops_commands_failed_total",
        "solarops_commands_timed_out_total",
        "solarops_verification_failures_total",
        "solarops_commands_completed_total",
        "solarops_recommendation_latency_seconds",
        "solarops_forecasts_produced_total",
        "solarops_anomalies_detected_total",
        "solarops_registered_model_versions",
        "solarops_api_requests_total",
        "solarops_api_request_latency_seconds",
        "solarops_telemetry_updates_total",
    ]
    for name in expected_names:
        assert f"# TYPE {name}" in text, f"{name} is not exposed"


def test_commands_rejected_total_is_labelled_by_reason():
    metrics.commands_rejected_total.labels(reason="policy").inc()
    text = _exposition_text()
    assert 'solarops_commands_rejected_total{reason="policy"}' in text


def test_registered_model_versions_gauge_accepts_context_labels():
    metrics.registered_model_versions.labels(
        context="forecast", model_name="solar-baseline", version="v1"
    ).set(1)
    text = _exposition_text()
    assert 'context="forecast"' in text
    assert 'model_name="solar-baseline"' in text
