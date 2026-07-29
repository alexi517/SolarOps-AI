from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from solarops.decision.domain.confidence import ConfidenceBand
from solarops.decision.domain.recommendation import Recommendation
from solarops.shared_kernel import ActionType, RecommendationId, SiteId


def make_recommendation(**overrides):
    defaults = dict(
        recommendation_id=RecommendationId.generate(),
        site_id=SiteId("SITE-1"),
        action=ActionType.CHARGE_BATTERY,
        confidence=0.91,
        expected_benefit="Prepare for forecasted evening demand",
        reason="Battery below target reserve",
        generated_at=datetime(2026, 7, 27, 12, 0, tzinfo=UTC),
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


def test_recommendation_round_trips_fields():
    recommendation = make_recommendation()
    assert recommendation.action is ActionType.CHARGE_BATTERY
    assert recommendation.confidence == 0.91


def test_params_default_to_empty_dict_but_can_carry_actionable_values():
    assert make_recommendation().params == {}
    recommendation = make_recommendation(params={"power_kw": 30.0})
    assert recommendation.params == {"power_kw": 30.0}


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_must_be_within_zero_and_one(confidence):
    with pytest.raises(ValidationError):
        make_recommendation(confidence=confidence)


def test_generated_at_must_be_timezone_aware():
    with pytest.raises(ValueError, match="timezone-aware"):
        make_recommendation(generated_at=datetime(2026, 7, 27, 12, 0))


def test_recommendation_is_immutable():
    recommendation = make_recommendation()
    with pytest.raises(Exception):
        recommendation.confidence = 0.5  # type: ignore[misc]


def test_explainability_fields_default_empty():
    recommendation = make_recommendation()
    assert recommendation.why_now == ""
    assert recommendation.evidence == ()
    assert recommendation.alternatives == ()
    assert recommendation.risks == ()


def test_explainability_fields_carry_explicit_values():
    recommendation = make_recommendation(
        why_now="Evaluated at 12:00.",
        evidence=("solar_power=80kW",),
        alternatives=("DISCHARGE_BATTERY — not chosen",),
        risks=("vetoed alternative X",),
    )
    assert recommendation.why_now == "Evaluated at 12:00."
    assert recommendation.evidence == ("solar_power=80kW",)
    assert recommendation.alternatives == ("DISCHARGE_BATTERY — not chosen",)
    assert recommendation.risks == ("vetoed alternative X",)


def test_confidence_band_and_factors_default():
    recommendation = make_recommendation()
    assert recommendation.confidence_band is ConfidenceBand.MEDIUM
    assert recommendation.confidence_factors == ()


def test_confidence_band_and_factors_can_be_set_explicitly():
    recommendation = make_recommendation(
        confidence_band=ConfidenceBand.LOW,
        confidence_factors=("load forecast unavailable -> reduced forecast certainty",),
    )
    assert recommendation.confidence_band is ConfidenceBand.LOW
    assert recommendation.confidence_factors == (
        "load forecast unavailable -> reduced forecast certainty",
    )
