import pytest

from solarops.anomaly.application.evaluation.metrics import (
    detection_latency_seconds,
    f1_score,
    false_positive_rate,
    precision,
    recall,
)


def test_precision_known_answer():
    assert precision(8, 2) == pytest.approx(0.8)


def test_precision_with_no_positive_predictions_is_perfect():
    assert precision(0, 0) == 1.0


def test_recall_known_answer():
    assert recall(8, 2) == pytest.approx(0.8)


def test_recall_with_no_actual_positives_is_perfect():
    assert recall(0, 0) == 1.0


def test_f1_score_known_answer():
    assert f1_score(0.8, 0.8) == pytest.approx(0.8)


def test_f1_score_zero_when_both_zero():
    assert f1_score(0.0, 0.0) == 0.0


def test_false_positive_rate_known_answer():
    assert false_positive_rate(2, 18) == pytest.approx(0.1)


def test_false_positive_rate_zero_with_no_negatives():
    assert false_positive_rate(0, 0) == 0.0


def test_detection_latency_known_answer():
    assert detection_latency_seconds(10, 12, tick_seconds=5.0) == 10.0


def test_detection_latency_none_when_never_detected():
    assert detection_latency_seconds(10, None, tick_seconds=5.0) is None


def test_detection_latency_never_negative():
    assert detection_latency_seconds(10, 10, tick_seconds=5.0) == 0.0
