from datetime import UTC, datetime

from solarops.execution.infrastructure.in_memory_approval_request_repository import (
    InMemoryApprovalRequestRepository,
)
from solarops.shared_kernel import ApprovalOutcome, SiteId

from ..domain.test_approval_request import ApprovalDecision, make_request

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
SITE_A = SiteId("SITE-1")
SITE_B = SiteId("SITE-2")


def test_get_returns_none_before_save():
    repository = InMemoryApprovalRequestRepository()
    request = make_request()
    assert repository.get(request.approval_request_id) is None


def test_save_then_get_round_trips():
    repository = InMemoryApprovalRequestRepository()
    request = make_request()
    repository.save(request)
    assert repository.get(request.approval_request_id) is request


def test_get_pending_for_command_ignores_decided_requests():
    repository = InMemoryApprovalRequestRepository()
    request = make_request()
    repository.save(request)
    assert repository.get_pending_for_command(request.command_id) is request

    request.decide(ApprovalDecision(outcome=ApprovalOutcome.APPROVED, decided_at=NOW))
    repository.save(request)
    assert repository.get_pending_for_command(request.command_id) is None


def test_list_pending_by_site_scopes_to_site_and_pending_only():
    repository = InMemoryApprovalRequestRepository()
    pending_a = make_request()  # site_id defaults to SITE-1
    repository.save(pending_a)

    decided = make_request()
    decided.decide(ApprovalDecision(outcome=ApprovalOutcome.REJECTED, decided_at=NOW))
    repository.save(decided)

    assert repository.list_pending_by_site(SITE_A) == [pending_a]
    assert repository.list_pending_by_site(SITE_B) == []
