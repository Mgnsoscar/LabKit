"""Units: construction, conversion, and dimensionality guards.

Logarithmic-unit arithmetic (dBm/dB) has its own suite in
``tests/test_logarithmic.py``.
"""

from __future__ import annotations

import pytest

from labkit.units import (
    DimensionalityError,
    ensure_frequency,
    ensure_power,
    is_frequency,
    is_power,
    quantity,
    unit,
)


def test_parse_and_equality_across_units() -> None:
    assert quantity("500 MHz") == quantity(0.5, "GHz")
    assert quantity(500, "MHz") == quantity(500e6, "Hz")


def test_unit_multiplication_style() -> None:
    assert 5 * unit("MHz") == quantity(5, "MHz")


def test_dbm_converts_to_linear() -> None:
    assert quantity(0, "dBm").to("mW").magnitude == pytest.approx(1.0)
    assert quantity(30, "dBm").to("W").magnitude == pytest.approx(1.0)


def test_string_constructor_handles_offset_units() -> None:
    # "-20 dBm" would trip pint's default string parser (offset-unit ambiguity);
    # quantity() must still build it correctly.
    assert quantity("-20 dBm").to("uW").magnitude == pytest.approx(10.0)
    assert quantity("-20 dBm") == quantity(-20, "dBm")


def test_kind_predicates() -> None:
    assert is_frequency(quantity(1, "GHz"))
    assert not is_frequency(quantity(1, "W"))
    assert is_power(quantity(3, "dBm"))
    assert is_power(quantity(1, "mW"))


def test_ensure_returns_quantity_when_valid() -> None:
    q = quantity(1, "GHz")
    assert ensure_frequency(q) is q


def test_ensure_raises_on_wrong_dimension() -> None:
    with pytest.raises(DimensionalityError):
        ensure_power(quantity(1, "Hz"))
