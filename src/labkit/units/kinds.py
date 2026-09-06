"""Dimensionality guards for quantities.

Many instrument methods only make sense for a particular *kind* of quantity: a
span must be a frequency, an output level must be a power, a timeout must be a
duration. These helpers check the dimensionality of a quantity and raise a
clear error otherwise.

Each ``is_*`` predicate returns a bool; each ``ensure_*`` returns the quantity
unchanged when valid (so it composes inside expressions) and raises
``DimensionalityError`` otherwise.

This replaces the pydantic ``AfterValidator`` aliases of the earlier prototype
with plain, explicit functions that work on any quantity without needing a
pydantic boundary to trigger validation.
"""

from __future__ import annotations

from typing import Callable, cast

from .quantity import Quantity, is_quantity
from .registry import ureg

__all__ = [
    "DimensionalityError",
    "is_frequency",
    "is_power",
    "is_time",
    "is_angle",
    "is_dimensionless_decibel",
    "ensure_frequency",
    "ensure_power",
    "ensure_time",
    "ensure_angle",
]


class DimensionalityError(TypeError):
    """Raised when a quantity has the wrong physical dimension for its use."""


def _has_dimensionality(q: object, reference_unit: str) -> bool:
    if not is_quantity(q):
        return False
    reference_dim = ureg.Quantity(1, reference_unit).dimensionality
    return bool(cast(Quantity, q).dimensionality == reference_dim)


def is_frequency(q: object) -> bool:
    """Return ``True`` if `q` is a frequency (Hz, kHz, MHz, ...)."""
    return _has_dimensionality(q, "Hz")


def is_power(q: object) -> bool:
    """Return ``True`` if `q` is a power (W, mW, dBm, ...)."""
    return _has_dimensionality(q, "W")


def is_time(q: object) -> bool:
    """Return ``True`` if `q` is a duration (s, ms, us, ...)."""
    return _has_dimensionality(q, "s")


def is_angle(q: object) -> bool:
    """Return ``True`` if `q` is an angle (deg, rad, ...)."""
    return _has_dimensionality(q, "rad")


def is_dimensionless_decibel(q: object) -> bool:
    """Return ``True`` if `q` is a plain, dimensionless decibel value (``dB``).

    Distinguishes ``dB`` (a ratio) from ``dBm`` (a power); only the former is
    dimensionless.
    """
    if not is_quantity(q):
        return False
    return str(getattr(q, "units", "")) == "decibel"


def _ensure(
    q: object,
    predicate: Callable[[object], bool],
    name: str,
    examples: str,
) -> Quantity:
    # `predicate` is one of the is_* callables above.
    if not predicate(q):
        got = getattr(q, "units", type(q).__name__)
        raise DimensionalityError(
            f"Expected a {name} quantity (e.g. {examples}). Got '{got}'."
        )
    return cast(Quantity, q)


def ensure_frequency(q: object) -> Quantity:
    """Return `q` if it is a frequency, else raise :class:`DimensionalityError`."""
    return _ensure(q, is_frequency, "frequency", "Hz, kHz, MHz")


def ensure_power(q: object) -> Quantity:
    """Return `q` if it is a power, else raise :class:`DimensionalityError`."""
    return _ensure(q, is_power, "power", "W, mW, dBm")


def ensure_time(q: object) -> Quantity:
    """Return `q` if it is a duration, else raise :class:`DimensionalityError`."""
    return _ensure(q, is_time, "time", "s, ms, us")


def ensure_angle(q: object) -> Quantity:
    """Return `q` if it is an angle, else raise :class:`DimensionalityError`."""
    return _ensure(q, is_angle, "angle", "deg, rad")
