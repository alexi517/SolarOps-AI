"""Human approval endpoints — this is what completes the Phase 5 HITL workflow
(brief §2). Each just builds an ``ApprovalDecision`` and hands it to the real
``ExecutionPipeline.resume_after_approval`` — no approval logic lives here.

Note on MODIFY (disclosed, not silently patched): ``ApprovalDecision`` already
carries ``modified_params`` (Phase 5, ``execution/domain/approval_request.py``),
but ``Command`` has no method to retarget its own dispatched ``params`` from
that field before dispatch — recording it is exactly what the existing domain
supports today. Actually re-targeting the command would be a Phase 5 domain
change, out of scope for a thin API-only pass; this is a pre-existing gap this
endpoint surfaces rather than papers over.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from solarops.api.dependencies import get_composition, require_api_key
from solarops.api.schemas.approval import (
    ApprovalActionRequest,
    ApprovalActionResponse,
    ModifyApprovalRequest,
    PendingApprovalResponse,
)
from solarops.api.schemas.command import CommandDetailResponse
from solarops.execution.domain.approval_request import ApprovalDecision, ApprovalRequest
from solarops.execution.domain.command import Command
from solarops.platform.api_composition import SystemComposition
from solarops.shared_kernel import ApprovalOutcome, ApprovalRequestId, OperatorId, SiteId

router = APIRouter(tags=["approvals"])


@router.get("/sites/{site_id}/approvals/pending", response_model=list[PendingApprovalResponse])
def list_pending_approvals(
    site_id: str, composition: SystemComposition = Depends(get_composition)
) -> list[PendingApprovalResponse]:
    requests = composition.approval_repository.list_pending_by_site(SiteId(site_id))
    return [PendingApprovalResponse.from_domain(r) for r in requests]


def _load_pending(
    composition: SystemComposition, approval_id: str
) -> tuple[ApprovalRequest, Command]:
    request = composition.approval_repository.get(ApprovalRequestId(approval_id))
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no approval request {approval_id!r}")
    if not request.is_pending:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"approval request {approval_id!r} was already decided"
        )
    command = composition.command_repository.get(request.command_id)
    if command is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no command for approval request {approval_id!r}"
        )
    return request, command


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalActionResponse,
    dependencies=[Depends(require_api_key)],
)
def approve(
    approval_id: str,
    body: ApprovalActionRequest,
    composition: SystemComposition = Depends(get_composition),
) -> ApprovalActionResponse:
    _request, command = _load_pending(composition, approval_id)
    decision = ApprovalDecision(
        outcome=ApprovalOutcome.APPROVED,
        decided_at=composition.clock.now(),
        operator_id=OperatorId(body.operator_id),
        reason=body.reason,
    )
    resolved = composition.execution_pipeline.resume_after_approval(command, decision)
    return ApprovalActionResponse(
        approval_request_id=approval_id,
        outcome=ApprovalOutcome.APPROVED.value,
        command=CommandDetailResponse.from_domain(resolved),
    )


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=ApprovalActionResponse,
    dependencies=[Depends(require_api_key)],
)
def reject(
    approval_id: str,
    body: ApprovalActionRequest,
    composition: SystemComposition = Depends(get_composition),
) -> ApprovalActionResponse:
    _request, command = _load_pending(composition, approval_id)
    decision = ApprovalDecision(
        outcome=ApprovalOutcome.REJECTED,
        decided_at=composition.clock.now(),
        operator_id=OperatorId(body.operator_id),
        reason=body.reason,
    )
    resolved = composition.execution_pipeline.resume_after_approval(command, decision)
    return ApprovalActionResponse(
        approval_request_id=approval_id,
        outcome=ApprovalOutcome.REJECTED.value,
        command=CommandDetailResponse.from_domain(resolved),
    )


@router.post(
    "/approvals/{approval_id}/modify",
    response_model=ApprovalActionResponse,
    dependencies=[Depends(require_api_key)],
)
def modify(
    approval_id: str,
    body: ModifyApprovalRequest,
    composition: SystemComposition = Depends(get_composition),
) -> ApprovalActionResponse:
    _request, command = _load_pending(composition, approval_id)
    decision = ApprovalDecision(
        outcome=ApprovalOutcome.MODIFIED,
        decided_at=composition.clock.now(),
        operator_id=OperatorId(body.operator_id),
        modified_params=body.modified_params,
        reason=body.reason,
    )
    resolved = composition.execution_pipeline.resume_after_approval(command, decision)
    return ApprovalActionResponse(
        approval_request_id=approval_id,
        outcome=ApprovalOutcome.MODIFIED.value,
        command=CommandDetailResponse.from_domain(resolved),
    )
