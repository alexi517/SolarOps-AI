"""Typed identifiers.

Every aggregate is referenced across contexts by a *typed* identifier rather
than a bare ``str``. This makes it a compile-time (mypy) and run-time error to
pass a ``SiteId`` where an ``AssetId`` is expected, and keeps the ubiquitous
language (Document 8, section 5) honest at the type level.

These are pure value objects: immutable, compared by value, hashable, and
dependent on nothing but the standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Self
from uuid import uuid4

__all__ = [
    "Identifier",
    "SiteId",
    "AssetId",
    "CommandId",
    "RecommendationId",
    "PolicyId",
    "ApprovalRequestId",
    "OperatorId",
    "IncidentId",
    "ForecastId",
    "ScenarioId",
    "AnomalyId",
    "AlertId",
    "AuditEntryId",
    "EventId",
]


@dataclass(frozen=True, slots=True)
class Identifier:
    """Base class for all typed identifiers.

    Subclasses set a ``prefix`` used by :meth:`generate`. Two identifiers are
    equal only when they are the *same subclass* and hold the same value, so a
    ``SiteId`` never compares equal to an ``AssetId`` even if the strings match.
    """

    value: str
    prefix: ClassVar[str] = "ID"

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise TypeError(
                f"{type(self).__name__} value must be a string, "
                f"got {type(self.value).__name__}"
            )
        if not self.value.strip():
            raise ValueError(f"{type(self).__name__} value must not be empty")

    @classmethod
    def generate(cls) -> Self:
        """Create a new unique identifier, e.g. ``CMD-<uuid4>``."""
        return cls(f"{cls.prefix}-{uuid4()}")

    def __str__(self) -> str:
        return self.value


class SiteId(Identifier):
    __slots__ = ()
    prefix = "SITE"


class AssetId(Identifier):
    __slots__ = ()
    prefix = "ASSET"


class CommandId(Identifier):
    __slots__ = ()
    prefix = "CMD"


class RecommendationId(Identifier):
    __slots__ = ()
    prefix = "REC"


class PolicyId(Identifier):
    __slots__ = ()
    prefix = "POL"


class ApprovalRequestId(Identifier):
    __slots__ = ()
    prefix = "APR"


class OperatorId(Identifier):
    __slots__ = ()
    prefix = "OP"


class IncidentId(Identifier):
    __slots__ = ()
    prefix = "INC"


class ForecastId(Identifier):
    __slots__ = ()
    prefix = "FC"


class ScenarioId(Identifier):
    __slots__ = ()
    prefix = "SCN"


class AnomalyId(Identifier):
    __slots__ = ()
    prefix = "ANM"


class AlertId(Identifier):
    __slots__ = ()
    prefix = "ALT"


class AuditEntryId(Identifier):
    __slots__ = ()
    prefix = "AUD"


class EventId(Identifier):
    __slots__ = ()
    prefix = "EVT"
