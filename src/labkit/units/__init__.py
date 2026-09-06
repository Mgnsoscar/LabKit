"""Physical quantities for LabKit, built on `pint`.

Everything needed to create and validate quantities lives here:

- :data:`ureg` — the shared unit registry (import quantities from one registry).
- :data:`Quantity` / :func:`quantity` — the quantity type and its constructor.
- :data:`Unit` / :func:`unit` — a bare unit for ``5 * unit("MHz")`` style code.
- ``is_*`` / ``ensure_*`` — dimensionality guards (frequency, power, time, angle).

See :mod:`labkit.units.quantity` for the roadmap on logarithmic-unit arithmetic.
"""

from __future__ import annotations

from ._literals import UnitName
from ._logarithmic import LogArithmeticError
from .kinds import (
    DimensionalityError,
    ensure_angle,
    ensure_frequency,
    ensure_power,
    ensure_time,
    is_angle,
    is_dimensionless_decibel,
    is_frequency,
    is_power,
    is_time,
)
from .quantity import Quantity, Unit, is_quantity, quantity, unit
from .registry import make_registry, ureg

__all__ = [
    "ureg",
    "make_registry",
    "Quantity",
    "Unit",
    "quantity",
    "unit",
    "is_quantity",
    "UnitName",
    "LogArithmeticError",
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
