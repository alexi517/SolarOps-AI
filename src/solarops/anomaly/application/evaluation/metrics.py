"""Anomaly detection metrics (Document 6 §5) — pure functions."""

from __future__ import annotations

__all__ = ["precision", "recall", "f1_score", "false_positive_rate", "detection_latency_seconds"]


def precision(true_positives: int, false_positives: int) -> float:
    denominator = true_positives + false_positives
    return true_positives / denominator if denominator > 0 else 1.0


def recall(true_positives: int, false_negatives: int) -> float:
    denominator = true_positives + false_negatives
    return true_positives / denominator if denominator > 0 else 1.0


def f1_score(precision_value: float, recall_value: float) -> float:
    denominator = precision_value + recall_value
    return 2 * precision_value * recall_value / denominator if denominator > 0 else 0.0


def false_positive_rate(false_positives: int, true_negatives: int) -> float:
    denominator = false_positives + true_negatives
    return false_positives / denominator if denominator > 0 else 0.0


def detection_latency_seconds(
    fault_injected_at_index: int,
    first_true_positive_index: int | None,
    tick_seconds: float,
) -> float | None:
    if first_true_positive_index is None:
        return None
    return max(0.0, (first_true_positive_index - fault_injected_at_index) * tick_seconds)
