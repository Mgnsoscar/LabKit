"""Units: construction, conversion, and dimensionality guards.

The skipped tests at the bottom pin down the *target* behaviour for logarithmic
units. They are the specification for the next milestone (physically-correct
dBm/dB arithmetic) and should be un-skipped as that lands.
"""

from __future__ import annotations

import math

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


# --- Target behaviour for the next milestone (not implemented yet) ----------

@pytest.mark.skip(reason="Physically-correct dBm arithmetic is the next milestone.")
def test_dbm_addition_combines_in_linear_domain() -> None:
    # 1 mW + 2 mW = 3 mW  ->  ~4.771 dBm
    result = quantity(0, "dBm") + quantity(3, "dBm")
    assert result.to("dBm").magnitude == pytest.approx(10 * math.log10(3), abs=1e-3)


@pytest.mark.skip(reason="Physically-correct dBm arithmetic is the next milestone.")
def test_dbm_minus_dbm_is_dimensionless_db() -> None:
    result = quantity(3, "dBm") - quantity(0, "dBm")
    assert result.to("dB").magnitude == pytest.approx(3.0)
