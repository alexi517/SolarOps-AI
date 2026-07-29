"""VerificationResult — confirms (or fails to confirm) the expected physical change.

Doc 8 §6.5, CESF §12. Acknowledgement from the hardware interface is never sufficient on its own
(ADR-011) — ``Command.complete()`` only accepts a passing ``VerificationResult``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = ["VerificationResult"]


@dataclass(frozen=True, slots=True)
class VerificationResult:
    passed: bool
    expected: str
    observed: str
    verified_at: datetime
