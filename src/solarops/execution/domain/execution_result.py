"""ExecutionResult — outcome of handing a command to the HardwareInterface.

Doc 8 §6.5, CESF §10.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from solarops.shared_kernel import ExecutionOutcome

__all__ = ["ExecutionResult"]


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    outcome: ExecutionOutcome
    dispatched_at: datetime
    acknowledged_at: datetime | None = None
    retry_count: int = 0
    detail: str = ""
