"""In-memory ApprovalRequestRepository — for tests and v1 (single-process, no persistence)."""

from __future__ import annotations

from solarops.execution.domain.approval_request import ApprovalRequest
from solarops.shared_kernel import ApprovalRequestId, CommandId, SiteId


class InMemoryApprovalRequestRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, ApprovalRequest] = {}

    def get(self, approval_request_id: ApprovalRequestId) -> ApprovalRequest | None:
        return self._by_id.get(str(approval_request_id))

    def get_pending_for_command(self, command_id: CommandId) -> ApprovalRequest | None:
        for request in self._by_id.values():
            if request.command_id == command_id and request.is_pending:
                return request
        return None

    def list_pending_by_site(self, site_id: SiteId) -> list[ApprovalRequest]:
        return [
            request
            for request in self._by_id.values()
            if request.site_id == site_id and request.is_pending
        ]

    def save(self, request: ApprovalRequest) -> None:
        self._by_id[str(request.approval_request_id)] = request
