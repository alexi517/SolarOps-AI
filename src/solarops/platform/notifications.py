"""WhatsApp notifications via CallMeBot — a free, no-business-account way to
send yourself a WhatsApp message from a script (activate once by messaging
their bot number, then a plain HTTP request sends a message).

``NullNotifier`` is the default (no phone/API key configured) — every method
is a no-op. Notification failures (a network blip, a bad key, CallMeBot's
own rate limiting) must never break the actual decision/execution pipeline,
so every send is wrapped and logged, never raised.
"""

from __future__ import annotations

import logging

import httpx

from solarops.anomaly.domain.events import AnomalyDetected
from solarops.decision.domain.recommendation import Recommendation
from solarops.execution.domain.command import Command
from solarops.shared_kernel import GridStatus

__all__ = ["NullNotifier", "WhatsAppNotifier"]

logger = logging.getLogger(__name__)

_CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


class NullNotifier:
    """No phone/API key configured — every notification is silently dropped."""

    def notify_approval_needed(self, command: Command) -> None:
        pass

    def notify_anomaly_detected(self, event: AnomalyDetected) -> None:
        pass

    def notify_decision_cycle_result(
        self, recommendation: Recommendation, command: Command
    ) -> None:
        pass

    def notify_grid_status_changed(self, old_status: GridStatus, new_status: GridStatus) -> None:
        pass


class WhatsAppNotifier:
    def __init__(self, phone: str, api_key: str, *, timeout_seconds: float = 5.0) -> None:
        self._phone = phone
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def notify_approval_needed(self, command: Command) -> None:
        risk = command.risk_assessment.level.name if command.risk_assessment else "UNKNOWN"
        self._send(f"⚠️ SolarOps: {command.action.value} needs your approval ({risk} risk).")

    def notify_anomaly_detected(self, event: AnomalyDetected) -> None:
        self._send(
            f"🚨 SolarOps: anomaly detected — {event.anomaly_type.value} "
            f"({event.severity.value}, {event.confidence:.0%} confidence)."
        )

    def notify_decision_cycle_result(
        self, recommendation: Recommendation, command: Command
    ) -> None:
        self._send(
            f"SolarOps: decision cycle recommended {recommendation.action.value} "
            f"— command status: {command.status.value}."
        )

    def notify_grid_status_changed(self, old_status: GridStatus, new_status: GridStatus) -> None:
        self._send(f"⚡ SolarOps: grid status changed — {old_status.value} → {new_status.value}.")

    def _send(self, text: str) -> None:
        try:
            response = httpx.get(
                _CALLMEBOT_URL,
                params={"phone": self._phone, "text": text, "apikey": self._api_key},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except Exception:
            # Never let a notification failure break the actual pipeline —
            # log it and move on, same fail-visible-not-fail-fatal spirit as
            # the rest of this codebase's error handling.
            logger.exception("WhatsApp notification failed to send")
