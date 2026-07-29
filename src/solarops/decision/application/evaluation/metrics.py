"""Decision-quality metrics (Document 6 §6) — pure functions."""

from __future__ import annotations

from solarops.shared_kernel import ActionType

__all__ = ["decision_accuracy", "ranking_quality", "confidence_calibration"]


def decision_accuracy(predicted: ActionType, expected: ActionType) -> float:
    """1.0 if the top recommendation matches the expected action, else 0.0."""
    return 1.0 if predicted is expected else 0.0


def ranking_quality(
    predicted_ranking: list[ActionType], expected_ranking: list[ActionType]
) -> float:
    """Fraction of the expected ranking's positions the predicted ranking gets
    right, position by position, over the expected ranking's length."""
    if not expected_ranking:
        return 1.0
    length = min(len(predicted_ranking), len(expected_ranking))
    if length == 0:
        return 0.0
    matches = sum(1 for i in range(length) if predicted_ranking[i] == expected_ranking[i])
    return matches / len(expected_ranking)


def confidence_calibration(confidences: list[float], correct: list[bool]) -> float:
    """Mean absolute distance between stated confidence and actual correctness.

    0.0 is perfectly calibrated, 1.0 is maximally miscalibrated.
    """
    if not confidences:
        return 0.0
    if len(confidences) != len(correct):
        raise ValueError("confidences and correct must be the same length")
    errors = [abs(c - (1.0 if ok else 0.0)) for c, ok in zip(confidences, correct, strict=True)]
    return sum(errors) / len(errors)
