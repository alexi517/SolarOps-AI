"""Request/response DTOs for the simulation-control endpoint — testing-only
surface for injecting/clearing a fault on the running Digital Twin, so a
scenario (e.g. a grid outage) can be exercised against a live deployment,
not just via a local script (``scripts/run_fault_injection_demo.py``)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .state import EnergyStateResponse

__all__ = ["FaultInjectionRequest", "FaultInjectionResponse"]

FaultTarget = Literal["solar", "battery", "inverter", "grid", "sensor"]


class FaultInjectionRequest(BaseModel):
    target: FaultTarget
    # None clears whatever fault is currently set on that target. Which
    # strings are meaningful depends on the target (e.g. grid accepts
    # "OUTAGE"/"UNSTABLE", battery accepts "OVERHEATING") — see
    # simulation/domain/models/*.py's own inject_fault() docstrings; an
    # unrecognised string is silently a no-op, matching the twin's own
    # existing tolerance.
    fault: str | None = None


class FaultInjectionResponse(BaseModel):
    target: FaultTarget
    fault: str | None
    state: EnergyStateResponse
