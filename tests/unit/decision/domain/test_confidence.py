import pytest

from solarops.decision.domain.confidence import ConfidenceBand, ConfidenceEstimate


def test_estimate_round_trips_fields():
    estimate = ConfidenceEstimate(score=0.82, band=ConfidenceBand.MEDIUM, factors=("x",))
    assert estimate.score == 0.82
    assert estimate.band is ConfidenceBand.MEDIUM
    assert estimate.factors == ("x",)


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_score_must_be_within_zero_and_one(score):
    with pytest.raises(ValueError, match=r"\[0,1\]"):
        ConfidenceEstimate(score=score, band=ConfidenceBand.LOW, factors=("x",))


def test_factors_must_not_be_empty():
    with pytest.raises(ValueError, match="factors must not be empty"):
        ConfidenceEstimate(score=0.5, band=ConfidenceBand.MEDIUM, factors=())


def test_band_values_match_document_9():
    assert ConfidenceBand.HIGH.value == "HIGH"
    assert ConfidenceBand.MEDIUM.value == "MEDIUM"
    assert ConfidenceBand.LOW.value == "LOW"
