"""ApprovalRequest -> JSON, plus the request/response DTOs for the human
approval endpoints — the part of the API that completes the Phase 5 HITL
workflow (brief §2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from solarops.execution.domain.approval_request import ApprovalRequest

from .command import CommandDetailResponse

__all__ = [
    "PendingApprovalResponse",
    "ApprovalActionRequest",
    "ModifyApprovalRequest",
    "ApprovalActionResponse",
]


class PendingApprovalResponse(BaseModel):
    approval_request_id: str
    command_id: str
    site_id: str
    risk_level: str
    requested_at: datetime
    timeout_at: datetime

    @classmethod
    def from_domain(cls, request: ApprovalRequest) -> PendingApprovalResponse:
        return cls(
            approval_request_id=str(request.approval_request_id),
            command_id=str(request.command_id),
            site_id=str(request.site_id),
            risk_level=request.risk_level.name,
            requested_at=request.requested_at,
            timeout_at=request.timeout_at,
        )


class ApprovalActionRequest(BaseModel):
    operator_id: str
    reason: str = ""


class ModifyApprovalRequest(ApprovalActionRequest):
    modified_params: dict = Field(default_factory=dict)


class ApprovalActionResponse(BaseModel):
    approval_request_id: str
    outcome: str
    command: CommandDetailResponse
