"""Tests for typed identifiers."""

from __future__ import annotations

import pytest

from solarops.shared_kernel.ids import AssetId, CommandId, Identifier, PolicyId, SiteId


def test_generate_uses_type_prefix() -> None:
    assert SiteId.generate().value.startswith("SITE-")
    assert AssetId.generate().value.startswith("ASSET-")
    assert CommandId.generate().value.startswith("CMD-")


def test_policy_id_uses_pol_prefix() -> None:
    # Added for the Safety context's Policy aggregate (Phase 5, Part A).
    assert PolicyId.generate().value.startswith("POL-")


def test_generated_ids_are_unique() -> None:
    ids = {CommandId.generate() for _ in range(1000)}
    assert len(ids) == 1000


def test_equality_is_by_value_within_a_type() -> None:
    assert SiteId("SITE-1") == SiteId("SITE-1")
    assert SiteId("SITE-1") != SiteId("SITE-2")


def test_different_id_types_are_never_equal() -> None:
    # Same string, different type -> not equal. This is the whole point.
    assert SiteId("X-1") != AssetId("X-1")
    assert AssetId("X-1") != SiteId("X-1")


def test_ids_are_hashable_and_distinct_across_types() -> None:
    bag = {SiteId("X-1"), AssetId("X-1")}
    assert len(bag) == 2


def test_empty_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        SiteId("")
    with pytest.raises(ValueError):
        SiteId("   ")


def test_non_string_value_is_rejected() -> None:
    with pytest.raises(TypeError):
        SiteId(123)  # type: ignore[arg-type]


def test_str_returns_the_raw_value() -> None:
    assert str(CommandId("CMD-42")) == "CMD-42"


def test_identifier_is_immutable() -> None:
    site = SiteId("SITE-1")
    with pytest.raises(Exception):
        site.value = "SITE-2"  # type: ignore[misc]


def test_base_identifier_has_default_prefix() -> None:
    assert Identifier.generate().value.startswith("ID-")
