"""Band power from a trace (:func:`labkit.instruments.drivers.siglent.integrate_band`).

Checked against spectra whose band power is known analytically: a flat noise
floor seen through the RBW filter, and a lone CW tone seen as the filter's
Gaussian response.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from labkit.instruments.drivers.siglent import GAUSSIAN_NOISE_BW_FACTOR, dbm_per_hz, integrate_band
from labkit.units import DimensionalityError, quantity as Q

_RBW_HZ = 10e3


def _gaussian_response(f: np.ndarray, f0: float, rbw: float) -> np.ndarray:
    """Power response of a Gaussian filter with 3 dB bandwidth `rbw`, centred on `f0`."""
    return np.exp(-4.0 * math.log(2.0) * ((f - f0) / rbw) ** 2)


def _axis(start: float, stop: float, points: int) -> np.ndarray:
    return np.linspace(start, stop, points)


def test_gaussian_noise_bandwidth_factor() -> None:
    # ENBW / B3dB of a Gaussian filter, ≈ 0.27 dB.
    assert GAUSSIAN_NOISE_BW_FACTOR == pytest.approx(1.0645, abs=1e-4)
    f = np.linspace(-20 * _RBW_HZ, 20 * _RBW_HZ, 400001)
    enbw = float(np.sum(_gaussian_response(f, 0.0, _RBW_HZ))) * (f[1] - f[0])
    assert enbw / _RBW_HZ == pytest.approx(GAUSSIAN_NOISE_BW_FACTOR, rel=1e-6)


def test_flat_spectrum_integrates_to_density_times_width() -> None:
    # A flat density S reads S × ENBW in every bin.
    density_mw_per_hz = 1e-12  # -120 dBm/Hz
    f = _axis(1.0e9, 1.01e9, 1001)  # 10 kHz spacing
    reading_dbm = 10 * math.log10(density_mw_per_hz * _RBW_HZ * GAUSSIAN_NOISE_BW_FACTOR)
    levels = Q(np.full(f.size, reading_dbm), "dBm")
    for lo, hi in [(1.002e9, 1.006e9), (1.0021234e9, 1.0057e9), (1.0e9, 1.01e9)]:
        power = integrate_band(Q(f, "Hz"), levels, Q(lo, "Hz"), Q(hi, "Hz"), Q(_RBW_HZ, "Hz"), GAUSSIAN_NOISE_BW_FACTOR)
        expected = 10 * math.log10(density_mw_per_hz * (hi - lo))
        assert power.to("dBm").magnitude == pytest.approx(expected, abs=1e-9)


def test_default_factor_reads_high_by_the_noise_bandwidth() -> None:
    f = _axis(1.0e9, 1.01e9, 1001)
    levels = Q(np.full(f.size, -60.0), "dBm")
    args = (Q(f, "Hz"), levels, Q(1.002, "GHz"), Q(1.008, "GHz"), Q(_RBW_HZ, "Hz"))
    with_factor = integrate_band(*args, noise_bw_factor=GAUSSIAN_NOISE_BW_FACTOR).to("dBm").magnitude
    without = integrate_band(*args).to("dBm").magnitude
    assert without - with_factor == pytest.approx(10 * math.log10(GAUSSIAN_NOISE_BW_FACTOR))


def test_a_single_tone_integrates_to_its_own_power() -> None:
    tone_dbm, f0 = -23.5, 1575.42e6
    f = _axis(f0 - 100e3, f0 + 100e3, 2001)  # 100 Hz spacing, RBW spans 100 points
    levels = Q(tone_dbm + 10 * np.log10(_gaussian_response(f, f0, _RBW_HZ) + 1e-30), "dBm")
    power = integrate_band(
        Q(f, "Hz"), levels, Q(f0 - 50e3, "Hz"), Q(f0 + 50e3, "Hz"), Q(_RBW_HZ, "Hz"), GAUSSIAN_NOISE_BW_FACTOR
    )
    assert power.to("dBm").magnitude == pytest.approx(tone_dbm, abs=1e-6)


def test_tone_outside_the_band_is_not_counted() -> None:
    f0 = 1.0e9
    f = _axis(f0 - 200e3, f0 + 200e3, 4001)
    levels = Q(-20 + 10 * np.log10(_gaussian_response(f, f0, _RBW_HZ) + 1e-30), "dBm")
    power = integrate_band(Q(f, "Hz"), levels, Q(f0 + 100e3, "Hz"), Q(f0 + 200e3, "Hz"), Q(_RBW_HZ, "Hz"))
    assert power.to("dBm").magnitude < -200


@pytest.mark.parametrize(
    "lo, hi",
    [
        (1.0e9 - 10e3, 1.005e9),  # starts more than half a bin before the trace
        (1.002e9, 1.011e9),  # runs past the end
        (1.005e9, 1.005e9),  # empty
        (1.006e9, 1.004e9),  # inverted
    ],
)
def test_bands_off_the_trace_or_empty_are_refused(lo: float, hi: float) -> None:
    f = _axis(1.0e9, 1.01e9, 1001)
    levels = Q(np.full(f.size, -60.0), "dBm")
    with pytest.raises(ValueError):
        integrate_band(Q(f, "Hz"), levels, Q(lo, "Hz"), Q(hi, "Hz"), Q(_RBW_HZ, "Hz"))


def test_the_outer_half_bins_belong_to_the_trace() -> None:
    # 1001 bins of 10 kHz cover 1.0 GHz − 5 kHz … 1.01 GHz + 5 kHz.
    f = _axis(1.0e9, 1.01e9, 1001)
    levels = Q(np.full(f.size, -60.0), "dBm")
    power = integrate_band(Q(f, "Hz"), levels, Q(1.0e9 - 5e3, "Hz"), Q(1.01e9 + 5e3, "Hz"), Q(_RBW_HZ, "Hz"))
    assert power.to("dBm").magnitude == pytest.approx(-60.0 + 10 * math.log10(1001))


def test_inputs_are_dimension_checked() -> None:
    f = Q(_axis(1.0e9, 1.01e9, 11), "Hz")
    levels = Q(np.full(11, -60.0), "dBm")
    with pytest.raises(DimensionalityError):
        integrate_band(levels, levels, Q(1, "GHz"), Q(1.005, "GHz"), Q(_RBW_HZ, "Hz"))
    with pytest.raises(DimensionalityError):
        integrate_band(f, levels, Q(1, "GHz"), Q(1.005, "GHz"), Q(-10, "dBm"))
    with pytest.raises(ValueError):
        integrate_band(f, Q(np.full(10, -60.0), "dBm"), Q(1, "GHz"), Q(1.005, "GHz"), Q(_RBW_HZ, "Hz"))


def test_dbm_per_hz() -> None:
    assert dbm_per_hz(Q(1e-12, "mW/Hz")) == pytest.approx(-120.0)
    assert dbm_per_hz(Q(1e-15, "W/Hz")) == pytest.approx(-120.0)
