"""Domain exception -> HTTP status mapping (Phase 7a brief §4).

Every domain exception descends from ``DomainError`` (see
``shared_kernel.exceptions``'s docstring) — Starlette's exception middleware
walks an exception's MRO to find the most specific *registered* handler, so
registering one handler for ``DomainError`` catches every subclass; this
module picks the status code by checking which specific subclass it actually
is. Not-found (missing site/command/approval id) is handled directly in each
router via ``HTTPException(404, ...)`` — a lookup miss, not a domain rule
violation.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from solarops.forecast.domain.exceptions import NoRegisteredModel
from solarops.shared_kernel import (
    ApprovalRequired,
    AssetUnavailableError,
    DomainError,
    DuplicateCommandError,
    FailSafeTriggered,
    InvalidStateTransition,
    PolicyViolation,
    RiskRejected,
    SafetyViolation,
    UnsafeStateError,
    VerificationFailed,
)

__all__ = ["register_exception_handlers"]

_STATUS_BY_EXCEPTION: tuple[tuple[type[DomainError], int], ...] = (
    (NoRegisteredModel, status.HTTP_404_NOT_FOUND),
    (AssetUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE),
    (FailSafeTriggered, status.HTTP_503_SERVICE_UNAVAILABLE),
    (PolicyViolation, status.HTTP_409_CONFLICT),
    (RiskRejected, status.HTTP_409_CONFLICT),
    (DuplicateCommandError, status.HTTP_409_CONFLICT),
    (InvalidStateTransition, status.HTTP_409_CONFLICT),
    (ApprovalRequired, status.HTTP_409_CONFLICT),
    (SafetyViolation, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (UnsafeStateError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (VerificationFailed, status.HTTP_422_UNPROCESSABLE_CONTENT),
)


async def _domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    for exc_type, code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            status_code = code
            break
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error_handler)
