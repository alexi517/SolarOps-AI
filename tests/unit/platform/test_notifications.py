from datetime import UTC, datetime

from solarops.anomaly.domain.anomaly_type import AnomalyType
from solarops.anomaly.domain.events import AnomalyDetected
from solarops.anomaly.domain.severity import Severity
from solarops.decision.domain.recommendation import Recommendation
from solarops.execution.domain.command import Command
from solarops.platform.notifications import NullNotifier, WhatsAppNotifier
from solarops.safety.domain.policy_result import PolicyResult
from solarops.safety.domain.risk_assessment import RiskAssessment
from solarops.safety.domain.safety_assessment import SafetyAssessment
from solarops.shared_kernel import (
    ActionType,
    AssetId,
    GridStatus,
    RecommendationId,
    RiskLevel,
    SiteId,
)

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


def make_command(**overrides) -> Command:
    defaults = dict(
        site_id=SiteId("SITE-1"),
        asset_id=AssetId("SITE-1-battery"),
        recommendation_id=RecommendationId.generate(),
        action=ActionType.CHARGE_BATTERY,
        params={"power_kw": 20.0},
        idempotency_key="idem-1",
        trace_id="trace-1",
        created_at=NOW,
    )
    defaults.update(overrides)
    return Command.create(**defaults)


def make_recommendation(**overrides) -> Recommendation:
    defaults = dict(
        recommendation_id=RecommendationId.generate(),
        site_id=SiteId("SITE-1"),
        action=ActionType.CHARGE_BATTERY,
        params={"power_kw": 20.0},
        confidence=0.9,
        expected_benefit="test",
        reason="test",
        generated_at=NOW,
        why_now="test",
        evidence=(),
        alternatives=(),
        risks=(),
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


class FakeResponse:
    def raise_for_status(self) -> None:
        pass


def test_null_notifier_does_nothing_for_every_method():
    # No assertions beyond "doesn't raise" — this is the whole point of the
    # default: every call is a silent no-op.
    notifier = NullNotifier()
    command = make_command()
    notifier.notify_approval_needed(command)
    notifier.notify_anomaly_detected(
        AnomalyDetected(
            aggregate_id="x",
            aggregate_type="Anomaly",
            anomaly_type=AnomalyType.BATTERY_OVERHEATING,
            severity=Severity.CRITICAL,
            confidence=0.8,
        )
    )
    notifier.notify_decision_cycle_result(make_recommendation(), command)
    notifier.notify_grid_status_changed(GridStatus.CONNECTED, GridStatus.OUTAGE)


def test_whatsapp_notifier_sends_approval_message_with_risk_level(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "solarops.platform.notifications.httpx.get",
        lambda url, params, timeout: (calls.append((url, params)), FakeResponse())[1],
    )

    command = make_command()
    command.apply_policy_result(PolicyResult(passed=True, evaluated_at=NOW))
    command.apply_safety_assessment(SafetyAssessment(passed=True, evaluated_at=NOW))
    command.apply_risk_assessment(RiskAssessment(level=RiskLevel.HIGH, assessed_at=NOW))

    notifier = WhatsAppNotifier(phone="1234567890", api_key="key123")
    notifier.notify_approval_needed(command)

    assert len(calls) == 1
    url, params = calls[0]
    assert url == "https://api.callmebot.com/whatsapp.php"
    assert params["phone"] == "1234567890"
    assert params["apikey"] == "key123"
    assert "CHARGE_BATTERY" in params["text"]
    assert "HIGH" in params["text"]


def test_whatsapp_notifier_grid_status_message():
    sent = []

    class RecordingNotifier(WhatsAppNotifier):
        def _send(self, text: str) -> None:
            sent.append(text)

    notifier = RecordingNotifier(phone="123", api_key="key")
    notifier.notify_grid_status_changed(GridStatus.CONNECTED, GridStatus.OUTAGE)

    assert len(sent) == 1
    assert "CONNECTED" in sent[0]
    assert "OUTAGE" in sent[0]


def test_whatsapp_notifier_swallows_send_failures_instead_of_raising(monkeypatch):
    def raise_error(*args, **kwargs):
        raise ConnectionError("network is down")

    monkeypatch.setattr("solarops.platform.notifications.httpx.get", raise_error)

    notifier = WhatsAppNotifier(phone="123", api_key="key")
    # Must not raise — a failed notification can never be allowed to break
    # the caller (the actual decision/execution pipeline).
    notifier.notify_grid_status_changed(GridStatus.CONNECTED, GridStatus.OUTAGE)
