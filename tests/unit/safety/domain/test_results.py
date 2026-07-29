"""PolicyResult, SafetyAssessment, RiskAssessment — structurally similar VOs, tested together."""

from datetime import UTC, datetime

import pytest

from solarops.safety.domain.policy_result import PolicyResult
from solarops.safety.domain.risk_assessment import RiskAssessment
from solarops.safety.domain.safety_assessment import SafetyAssessment
from solarops.shared_kernel import RiskLevel

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def test_policy_result_defaults_and_naive_timestamp_rejected():
    result = PolicyResult(passed=True, evaluated_at=NOW)
    assert result.violations == ()
    with pytest.raises(ValueError, match="timezone-aware"):
        PolicyResult(passed=True, evaluated_at=datetime(2026, 7, 27, 12, 0))


def test_safety_assessment_defaults_and_naive_timestamp_rejected():
    assessment = SafetyAssessment(passed=False, failed_checks=("x",), evaluated_at=NOW)
    assert assessment.failed_checks == ("x",)
    with pytest.raises(ValueError, match="timezone-aware"):
        SafetyAssessment(passed=True, evaluated_at=datetime(2026, 7, 27, 12, 0))


def test_risk_assessment_defaults_and_naive_timestamp_rejected():
    assessment = RiskAssessment(level=RiskLevel.LOW, assessed_at=NOW)
    assert assessment.factors == ()
    assert assessment.level is RiskLevel.LOW
    with pytest.raises(ValueError, match="timezone-aware"):
        RiskAssessment(level=RiskLevel.LOW, assessed_at=datetime(2026, 7, 27, 12, 0))
