"""Physical-quantity value objects.

These wrap raw numbers in self-validating, immutable types so the domain never
passes a bare ``float`` around (avoiding *primitive obsession*). A ``Power`` can
be added to a ``Power`` but never to an ``Energy``; a ``StateOfCharge`` can only
exist between 0 and 100. Safety and physics code can therefore trust that a
value object, once constructed, is dimensionally and physically sane.

Construction-time constraint failures raise ``ValueError``/``TypeError`` (the
value simply cannot exist). Business-rule violations that occur *during
operations* raise domain exceptions instead — see ``exceptions.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar, Self

__all__ = [
    "Quantity",
    "Power",
    "Energy",
    "StateOfCharge",
    "Temperature",
    "Voltage",
    "Current",
    "Frequency",
]


def _require_real_number(value: object, name: str) -> None:
    # bool is a subclass of int; reject it so True/False can't masquerade as data.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


@dataclass(frozen=True, slots=True, order=True)
class Quantity:
    """Base for single-value physical quantities.

    Subclasses set ``unit`` and optional inclusive ``minimum`` / ``maximum``
    bounds. Arithmetic returns the *same subclass*, and ordering / equality are
    type-safe: comparing two different quantity types raises ``TypeError``.
    """

    value: float
    unit: ClassVar[str] = ""
    minimum: ClassVar[float | None] = None
    maximum: ClassVar[float | None] = None

    def __post_init__(self) -> None:
        name = type(self).__name__
        _require_real_number(self.value, name)
        lo, hi = type(self).minimum, type(self).maximum
        if lo is not None and self.value < lo:
            raise ValueError(f"{name} must be >= {lo} {self.unit}, got {self.value}")
        if hi is not None and self.value > hi:
            raise ValueError(f"{name} must be <= {hi} {self.unit}, got {self.value}")

    def __add__(self, other: object) -> Self:
        if type(other) is not type(self):
            return NotImplemented
        return type(self)(self.value + other.value)  # type: ignore[attr-defined]

    def __sub__(self, other: object) -> Self:
        if type(other) is not type(self):
            return NotImplemented
        return type(self)(self.value - other.value)  # type: ignore[attr-defined]

    def __mul__(self, scalar: object) -> Self:
        if isinstance(scalar, bool) or not isinstance(scalar, (int, float)):
            return NotImplemented
        return type(self)(self.value * scalar)

    __rmul__ = __mul__

    def __truediv__(self, other: object) -> Self | float:
        # Dividing by the same quantity yields a dimensionless ratio;
        # dividing by a scalar yields the same quantity.
        if type(other) is type(self):
            return self.value / other.value  # type: ignore[attr-defined]
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            return NotImplemented
        return type(self)(self.value / other)

    def __neg__(self) -> Self:
        return type(self)(-self.value)

    def __abs__(self) -> Self:
        return type(self)(abs(self.value))

    def __str__(self) -> str:
        return f"{self.value:g} {self.unit}".strip()


class Power(Quantity):
    """Real power in kilowatts. Sign encodes direction (import/charge vs.
    export/discharge), so negatives are allowed."""

    __slots__ = ()
    unit = "kW"


class Energy(Quantity):
    """Energy in kilowatt-hours. Non-negative."""

    __slots__ = ()
    unit = "kWh"
    minimum = 0.0


class StateOfCharge(Quantity):
    """Battery state of charge as a percentage in [0, 100]."""

    __slots__ = ()
    unit = "%"
    minimum = 0.0
    maximum = 100.0

    @property
    def fraction(self) -> float:
        """State of charge as a fraction in [0.0, 1.0]."""
        return self.value / 100.0


class Temperature(Quantity):
    """Temperature in degrees Celsius, bounded to a physically plausible range."""

    __slots__ = ()
    unit = "\N{DEGREE SIGN}C"
    minimum = -50.0
    maximum = 150.0


class Voltage(Quantity):
    """Voltage in volts. Non-negative."""

    __slots__ = ()
    unit = "V"
    minimum = 0.0


class Current(Quantity):
    """Current in amperes. Sign encodes direction, so negatives are allowed."""

    __slots__ = ()
    unit = "A"


class Frequency(Quantity):
    """Frequency in hertz. Non-negative."""

    __slots__ = ()
    unit = "Hz"
    minimum = 0.0
