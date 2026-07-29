from solarops.execution.infrastructure.in_memory_command_repository import (
    InMemoryCommandRepository,
)
from solarops.shared_kernel import SiteId

from ..domain.test_command import make_command

SITE_A = SiteId("SITE-1")
SITE_B = SiteId("SITE-2")


def test_get_returns_none_before_save():
    repository = InMemoryCommandRepository()
    command = make_command()
    assert repository.get(command.command_id) is None


def test_save_then_get_round_trips():
    repository = InMemoryCommandRepository()
    command = make_command()
    repository.save(command)
    assert repository.get(command.command_id) is command


def test_get_by_idempotency_key():
    repository = InMemoryCommandRepository()
    command = make_command(idempotency_key="idem-xyz")
    repository.save(command)
    assert repository.get_by_idempotency_key("idem-xyz") is command
    assert repository.get_by_idempotency_key("other") is None


def test_list_by_site_scopes_to_the_requested_site():
    repository = InMemoryCommandRepository()
    command_a = make_command(site_id=SITE_A, idempotency_key="a")
    command_b = make_command(site_id=SITE_B, idempotency_key="b")
    repository.save(command_a)
    repository.save(command_b)

    assert repository.list_by_site(SITE_A) == [command_a]
    assert repository.list_by_site(SITE_B) == [command_b]


def test_list_by_site_is_empty_for_unknown_site():
    repository = InMemoryCommandRepository()
    assert repository.list_by_site(SITE_A) == []
