import pytest

from solarops.decision.application.evaluation.metrics import (
    confidence_calibration,
    decision_accuracy,
    ranking_quality,
)
from solarops.shared_kernel import ActionType


def test_decision_accuracy_matches():
    assert decision_accuracy(ActionType.CHARGE_BATTERY, ActionType.CHARGE_BATTERY) == 1.0


def test_decision_accuracy_mismatch():
    assert decision_accuracy(ActionType.CHARGE_BATTERY, ActionType.HOLD_BATTERY) == 0.0


def test_ranking_quality_perfect_match():
    ranking = [ActionType.CHARGE_BATTERY, ActionType.HOLD_BATTERY]
    assert ranking_quality(ranking, ranking) == 1.0


def test_ranking_quality_partial_match():
    predicted = [ActionType.CHARGE_BATTERY, ActionType.DISCHARGE_BATTERY]
    expected = [ActionType.CHARGE_BATTERY, ActionType.HOLD_BATTERY]
    assert ranking_quality(predicted, expected) == pytest.approx(0.5)


def test_ranking_quality_empty_expected_is_perfect():
    assert ranking_quality([], []) == 1.0


def test_confidence_calibration_perfect_is_zero():
    assert confidence_calibration([1.0, 0.0], [True, False]) == 0.0


def test_confidence_calibration_overconfident_is_penalised():
    assert confidence_calibration([1.0], [False]) == 1.0


def test_confidence_calibration_empty_is_zero():
    assert confidence_calibration([], []) == 0.0


def test_confidence_calibration_mismatched_lengths_raises():
    with pytest.raises(ValueError, match="same length"):
        confidence_calibration([1.0], [True, False])
