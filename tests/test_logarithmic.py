"""Physically-correct arithmetic for logarithmic units (dBm, dBW, dB).

Assertions are made on the linear equivalent (``.to("mW")``) where a level is
expected, and on the ``dB`` magnitude where a ratio is expected, so the checks
are exact rather than dependent on rounded dB values.
"""

from __future__ import annotations

from typing import Any

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


# --- array reductions -------------------------------------------------------

LEVELS_MW = [1.0, MW_3DB, 10 ** 0.6]  # linear equivalents of [0, 3, 6] dBm


def _levels() -> Any:
    return Q(np.array([0.0, 3.0, 6.0]), "dBm")


def _q(result: object) -> Any:
    """Launder a numpy-typed result so the quantity attributes type-check."""
    return result


def test_sum_of_log_power_array_is_linear_and_in_the_log_unit() -> None:
    total = _levels().sum()
    assert str(total.units) == "dBm"
    assert total.to("mW").magnitude == pytest.approx(sum(LEVELS_MW))
    assert total.magnitude == pytest.approx(10 * np.log10(sum(LEVELS_MW)))  # ~8.44 dBm, not 9
    # the numpy function form agrees with the method form
    assert _q(np.sum(_levels())).magnitude == pytest.approx(total.magnitude)
    assert _q(np.nansum(_levels())).magnitude == pytest.approx(total.magnitude)


def test_mean_average_median_of_log_power_array() -> None:
    levels = _levels()
    linear_mean = sum(LEVELS_MW) / 3
    assert levels.mean().to("mW").magnitude == pytest.approx(linear_mean)
    assert _q(np.mean(levels)).to("mW").magnitude == pytest.approx(linear_mean)
    assert _q(np.nanmean(levels)).to("mW").magnitude == pytest.approx(linear_mean)
    assert _q(np.average(levels)).to("mW").magnitude == pytest.approx(linear_mean)
    assert str(_q(np.mean(levels)).units) == "dBm"
    # weighted average is also linear-domain
    weighted = _q(np.average(levels, weights=[1.0, 0.0, 0.0]))
    assert weighted.to("mW").magnitude == pytest.approx(1.0)
    # median: the middle element (3 dBm) either way
    assert _q(np.median(levels)).magnitude == pytest.approx(3.0)


def test_cumsum_of_log_power_array() -> None:
    running = _q(np.cumsum(_levels()))
    assert str(running.units) == "dBm"
    np.testing.assert_allclose(running.to("mW").magnitude, np.cumsum(LEVELS_MW))
    np.testing.assert_allclose(_levels().cumsum().to("mW").magnitude, np.cumsum(LEVELS_MW))


def test_reductions_keep_the_dbw_reference() -> None:
    levels: Any = Q(np.array([0.0, 0.0]), "dBW")  # 1 W + 1 W
    total = levels.sum()
    assert str(total.units) == "dBW"
    assert total.to("W").magnitude == pytest.approx(2.0)


def test_reductions_along_an_axis() -> None:
    grid: Any = Q(np.array([[0.0, 0.0], [3.0, 3.0]]), "dBm")
    by_column = _q(np.sum(grid, axis=0))
    assert by_column.shape == (2,)
    np.testing.assert_allclose(by_column.to("mW").magnitude, [1 + MW_3DB, 1 + MW_3DB])
    np.testing.assert_allclose(grid.mean(axis=1).to("mW").magnitude, [1.0, MW_3DB])


def test_max_and_min_are_unchanged_and_exact() -> None:
    levels = _levels()
    assert levels.max() == Q(6, "dBm")
    assert levels.min() == Q(0, "dBm")
    assert np.max(levels) == Q(6, "dBm")
    assert np.nanmin(levels) == Q(0, "dBm")
    assert np.argmax(levels) == 2


def test_differences_between_levels_are_db_ratios() -> None:
    levels = _levels()
    spread = _q(np.ptp(levels))
    assert str(spread.units) == "dB"
    assert spread.magnitude == pytest.approx(6.0)
    steps = _q(np.diff(levels))
    assert str(steps.units) == "dB"
    np.testing.assert_allclose(steps.magnitude, [3.0, 3.0])
    assert str(levels.std().units) == "dB"
    assert levels.std().magnitude == pytest.approx(np.std([0.0, 3.0, 6.0]))
    assert str(_q(np.nanstd(levels)).units) == "dB"


def test_ratio_array_reductions_stay_in_db() -> None:
    gains: Any = Q(np.array([3.0, 3.0]), "dB")
    assert gains.sum() == Q(6, "dB")  # cascade
    assert np.mean(gains) == Q(3, "dB")
    assert np.ptp(gains) == Q(0, "dB")


@pytest.mark.parametrize(
    "op",
    [
        lambda: np.prod(_levels()),
        lambda: _levels().prod(),
        lambda: np.cumprod(_levels()),
        lambda: _levels().cumprod(),
        lambda: np.var(_levels()),
        lambda: _levels().var(),
        lambda: np.prod(Q(np.array([1.0, 2.0]), "dB")),
    ],
)
def test_meaningless_reductions_raise(op) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(LogArithmeticError):
        op()


def test_linear_array_reductions_are_unchanged() -> None:
    powers: Any = Q(np.array([1.0, 2.0, 3.0]), "mW")
    assert powers.sum() == Q(6, "mW")
    assert np.mean(powers) == Q(2, "mW")
    assert np.cumsum(powers)[-1] == Q(6, "mW")
    assert str(_q(np.std(powers)).units) == "mW"
    freqs: Any = Q(np.array([1.0, 3.0]), "GHz")
    assert freqs.mean() == Q(2, "GHz")
    assert np.ptp(freqs) == Q(2, "GHz")


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
