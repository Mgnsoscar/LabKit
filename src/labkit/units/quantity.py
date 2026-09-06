"""The :data:`Quantity` type and the :func:`quantity` constructor.

A *quantity* is a number (or array) with a physical unit attached. Working with
quantities instead of bare floats removes a whole class of silent errors: you
can add ``500 * Unit("MHz")`` to ``2e8 * Unit("Hz")`` without thinking about the
conversion, and a value measured in one unit compares equal to the same value
expressed in another.

LabKit quantities are `pint` quantities drawn from the shared registry (see
:mod:`labkit.units.registry`). This module is the single place other code
should import :data:`Quantity` and :func:`quantity` from.

Logarithmic units such as ``dBm``/``dB`` add, subtract and combine in the
physically-correct way; that behaviour lives in
:mod:`labkit.units._logarithmic` and is installed on the registry
automatically. Note that logarithmic quantities must be *constructed* with
``quantity(value, "dBm")`` — the ``value * unit("dBm")`` idiom is not supported
for them (see :func:`unit`).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from ._literals import UnitName
from .registry import ureg

# Matches a leading numeric magnitude followed by a unit, e.g. "-20 dBm".
_VALUE_UNIT = re.compile(
    r"^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(\S.*)$"
)

if TYPE_CHECKING:
    # pint's Quantity/Unit are generic at type-check time; at runtime we use the
    # registry's concrete classes.
    from pint import Quantity as Quantity
    from pint import Unit as Unit
else:
    Quantity = ureg.Quantity
    Unit = ureg.Unit

__all__ = ["Quantity", "Unit", "quantity", "unit", "is_quantity"]


def unit(name: UnitName) -> "Unit":
    """Return a bare :data:`Unit` you can multiply a number by.

    This preserves the ergonomic ``5 * unit("MHz")`` construction style, and
    because `name` is typed as :data:`~labkit.units._literals.UnitName`, editors
    suggest every known unit as you type.

    >>> 5 * unit("MHz") == quantity(5, "MHz")
    True

    .. warning::
        This idiom does **not** work for logarithmic units (``dBm``, ``dBW``,
        ``dB``): ``value * unit("dBm")`` relies on multiplication, which is
        undefined for them and raises
        :class:`~labkit.units.LogArithmeticError`. Build those with
        ``quantity(value, "dBm")`` instead.
    """
    return ureg.Unit(name)


def quantity(value: Any, unit: str | None = None) -> "Quantity":
    """Create a :data:`Quantity` on LabKit's shared registry.

    Parameters
    ----------
    value:
        A number, a numpy array, or a string such as ``"500 MHz"``. When a
        string is given, `unit` must be omitted and the unit is parsed from the
        string.
    unit:
        The unit to attach to a numeric `value`, e.g. ``"MHz"`` or ``"dBm"``.

    Examples
    --------
    >>> quantity(500, "MHz")
    <Quantity(500, 'megahertz')>
    >>> quantity("500 MHz") == quantity(0.5, "GHz")
    True
    """
    if isinstance(value, str):
        if unit is not None:
            raise ValueError(
                "Pass either a string like 'quantity(\"500 MHz\")' or a value "
                "and unit like 'quantity(500, \"MHz\")', not both."
            )
        # A leading "<number> <unit>" is built with the numeric constructor.
        # pint's string parser would read "-20 dBm" as -20 * dBm, which is
        # undefined for logarithmic units; splitting avoids that entirely and is
        # also faster. Fall back to the full parser for anything else (a bare
        # unit, or a value with no unit).
        match = _VALUE_UNIT.match(value)
        if match is not None:
            magnitude, unit_str = match.groups()
            return ureg.Quantity(float(magnitude), unit_str.strip())
        return ureg.Quantity(value)
    return ureg.Quantity(value, unit)


def is_quantity(obj: object) -> bool:
    """Return ``True`` if `obj` is a quantity from LabKit's registry."""
    return isinstance(obj, ureg.Quantity)
