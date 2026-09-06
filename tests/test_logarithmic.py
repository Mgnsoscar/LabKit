"""Physically-correct arithmetic for logarithmic units (dBm, dBW, dB).

Assertions are made on the linear equivalent (``.to("mW")``) where a level is
expected, and on the ``dB`` magnitude where a ratio is expected, so the checks
are exact rather than dependent on rounded dB values.
"""

from __future__ import annotations

import numpy as np
import pytest

from labkit.units import LogArithmeticError, quantity as Q

MW_3DB = 10 ** 0.3  # milliwatts in a 3 dBm signal (~1.995)


# --- addition ---------------------------------------------------------------

def test_power_plus_power_combines_in_linear_domain() -> None:
    # 1 mW + 1 mW = 2 mW
    assert (Q(0, "dBm") + Q(0, "dBm")).to("mW").magnitude == pytest.approx(2.0)
    # 1 mW + ~1.995 mW
    assert (Q(0, "dBm") + Q(3, "dBm")).to("mW").magnitude == pytest.approx(1 + MW_3DB)


def test_linear_power_plus_log_power() -> None:
    assert (Q(1, "mW") + Q(0, "dBm")).to("mW").magnitude == pytest.approx(2.0)


def test_power_plus_gain_applies_gain() -> None:
    # 0 dBm (1 mW) with +3 dB gain -> 1 mW * 10**0.3
    assert (Q(0, "dBm") + Q(3, "dB")).to("mW").magnitude == pytest.approx(MW_3DB)
    # commutative
    assert (Q(3, "dB") + Q(0, "dBm")).to("mW").magnitude == pytest.approx(MW_3DB)


def test_gain_plus_gain_cascades() -> None:
    result = Q(3, "dB") + Q(3, "dB")
    assert str(result.units) == "dB"
    assert result.magnitude == pytest.approx(6.0)


def test_dbw_reference_is_preserved() -> None:
    result = Q(0, "dBW") + Q(0, "dBW")  # 1 W + 1 W = 2 W
    assert str(result.units) == "dBW"
    assert result.to("W").magnitude == pytest.approx(2.0)


def test_left_reference_wins_for_mixed_log_power() -> None:
    assert str((Q(0, "dBm") + Q(0, "dBW")).units) == "dBm"
    assert str((Q(0, "dBW") + Q(0, "dBm")).units) == "dBW"


# --- subtraction ------------------------------------------------------------

def test_power_minus_power_is_db_ratio() -> None:
    result = Q(3, "dBm") - Q(0, "dBm")
    assert str(result.units) == "dB"
    assert result.magnitude == pytest.approx(3.0)
    assert (Q(0, "dBm") - Q(3, "dBm")).magnitude == pytest.approx(-3.0)


def test_power_minus_gain_applies_loss() -> None:
    assert (Q(10, "dBm") - Q(3, "dB")).magnitude == pytest.approx(7.0)


def test_gain_minus_gain() -> None:
    assert (Q(6, "dB") - Q(3, "dB")).magnitude == pytest.approx(3.0)


# --- multiplication / division: rejected, plus the linear escape hatch ------

def test_scaling_via_linear_conversion() -> None:
    # Multiplication/division on log units is rejected; convert to linear first.
    doubled = (Q(0, "dBm").to("mW") * 2).to("dBm")
    assert doubled.to("mW").magnitude == pytest.approx(2.0)
    ratio = Q(6, "dBm").to("mW") / Q(0, "dBm").to("mW")
    assert ratio.magnitude == pytest.approx(10 ** 0.6)


# --- rejected operations ----------------------------------------------------

@pytest.mark.parametrize(
    "op",
    [
        lambda: Q(0, "dBm") + 5,
        lambda: Q(3, "dB") + 1,
        lambda: Q(3, "dB") - Q(0, "dBm"),
        lambda: Q(3, "dB") * 2,
        lambda: 2 * Q(0, "dBm"),
        lambda: Q(0, "dBm") / 2,
        lambda: Q(0, "dBm") * Q(0, "dBm"),
        lambda: Q(6, "dBm") / Q(0, "dBm"),
    ],
)
def test_nonsensical_operations_raise(op) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(LogArithmeticError):
        op()


# --- arrays -----------------------------------------------------------------

def test_arrays_elementwise() -> None:
    a = Q(np.array([0.0, 3.0]), "dBm") + Q(np.array([0.0, 3.0]), "dBm")
    np.testing.assert_allclose(a.to("mW").magnitude, [2.0, 2 * MW_3DB])

    b = Q(np.array([3.0, 6.0]), "dBm") - Q(0, "dBm")
    assert str(b.units) == "dB"
    np.testing.assert_allclose(b.magnitude, [3.0, 6.0])


# --- non-logarithmic operations are unchanged -------------------------------

def test_non_log_arithmetic_is_unchanged() -> None:
    assert (Q(500, "MHz") + Q(0.5, "GHz")).to("MHz").magnitude == pytest.approx(1000.0)
    assert (Q(1, "mW") + Q(1, "mW")).to("mW").magnitude == pytest.approx(2.0)
    assert (2 * Q(3, "mW")).to("mW").magnitude == pytest.approx(6.0)


# --- equality and conversions still work ------------------------------------

def test_equality_and_conversion() -> None:
    assert Q(0, "dBm") == Q(1, "mW")
    assert Q(0, "dBm") != Q(1, "Hz")
    assert (Q(0, "dBm") + Q(3, "dBm")).to("mW").magnitude == pytest.approx(1 + MW_3DB)
