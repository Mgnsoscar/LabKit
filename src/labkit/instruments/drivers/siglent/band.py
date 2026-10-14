"""Band power from a spectrum trace — the fallback for an analyzer without channel power.

Pure numpy: nothing here talks to an instrument. :func:`integrate_band` turns a
trace (as returned by
:meth:`~labkit.instruments.drivers.siglent.trace.Trace.get_data`) into the power
in a frequency band, the same quantity the SHA850-AMK channel-power measurement
reports.

Why a noise-bandwidth factor
----------------------------
Each trace point is the power the resolution filter lets through when centred
on that frequency. For a spread (noise-like) signal of density *S* that is
*S* × ENBW, where ENBW is the filter's equivalent *noise* bandwidth — not the
3 dB bandwidth the RBW setting names. Summing the points as densities therefore
divides by RBW × ENBW/RBW. For the Gaussian-like RBW filter of the SHA850A
(datasheet: "Gaussian-like", shape factor < 4.8:1) ENBW/RBW is
√(π / (4 ln 2)) ≈ 1.0645 (:data:`GAUSSIAN_NOISE_BW_FACTOR`); a trace taken with
power (RMS) averaging and the average or sample detector reads true power per
filter, which this factor turns into true band power. The same factor makes a
lone CW tone integrate to its own power. The default factor of 1.0 treats the
RBW as the noise bandwidth (≈ 0.27 dB high for a Gaussian filter).
"""

from __future__ import annotations

import math

import numpy as np

from ....units import Quantity, ensure_frequency, ensure_power, quantity

__all__ = ["integrate_band", "dbm_per_hz", "GAUSSIAN_NOISE_BW_FACTOR"]

#: Equivalent noise bandwidth over 3 dB bandwidth of a Gaussian filter, √(π / (4 ln 2)).
GAUSSIAN_NOISE_BW_FACTOR = math.sqrt(math.pi / (4.0 * math.log(2.0)))


def integrate_band(
    freqs: Quantity,
    levels_dbm: Quantity,
    lo: Quantity,
    hi: Quantity,
    rbw: Quantity,
    noise_bw_factor: float = 1.0,
) -> Quantity:
    """Integrate a trace's power over the band ``[lo, hi]``.

    Each point stands for a bin of the trace's point spacing Δf centred on its
    frequency; its linear power is weighted by the part of that bin inside the
    band (Δf for interior bins, a fraction at the edges, so the band need not
    fall on bin edges) and divided by ``rbw × noise_bw_factor``:

        P = Σ p_k · overlap_k / (RBW · factor)

    `freqs` must be evenly spaced and ascending (a trace axis); `levels_dbm` the
    matching levels in dBm. Pass :data:`GAUSSIAN_NOISE_BW_FACTOR` for the
    analyzer's Gaussian RBW filter (see the module note). Returns the band power
    in dBm. Raises :class:`ValueError` for a band that is empty, inverted, or
    reaches beyond the trace (it is never extrapolated).
    """
    f = np.asarray(ensure_frequency(freqs).to("Hz").magnitude, dtype=float)
    p_dbm = np.asarray(ensure_power(levels_dbm).to("dBm").magnitude, dtype=float)
    if f.ndim != 1 or f.shape != p_dbm.shape:
        raise ValueError(f"freqs and levels must be 1-D arrays of one length, got {f.shape} and {p_dbm.shape}.")
    if f.size < 2:
        raise ValueError("A trace needs at least two points to integrate.")
    step = (f[-1] - f[0]) / (f.size - 1)
    if step <= 0:
        raise ValueError("Trace frequencies must be ascending.")
    lo_hz = float(ensure_frequency(lo).to("Hz").magnitude)
    hi_hz = float(ensure_frequency(hi).to("Hz").magnitude)
    rbw_hz = float(ensure_frequency(rbw).to("Hz").magnitude)
    if not hi_hz > lo_hz:
        raise ValueError(f"Band [{lo}, {hi}] is empty or inverted.")
    if rbw_hz <= 0 or noise_bw_factor <= 0:
        raise ValueError("rbw and noise_bw_factor must be positive.")
    # The trace covers its outermost bins out to half a point beyond each end.
    covered_lo, covered_hi = f[0] - step / 2, f[-1] + step / 2
    tolerance = 1e-9 * step
    if lo_hz < covered_lo - tolerance or hi_hz > covered_hi + tolerance:
        raise ValueError(
            f"Band [{lo_hz:g}, {hi_hz:g}] Hz reaches beyond the trace "
            f"[{covered_lo:g}, {covered_hi:g}] Hz."
        )
    overlap = np.clip(np.minimum(f + step / 2, hi_hz) - np.maximum(f - step / 2, lo_hz), 0.0, step)
    linear_mw = 10.0 ** (p_dbm / 10.0)
    total_mw = float(np.sum(linear_mw * overlap)) / (rbw_hz * noise_bw_factor)
    if total_mw <= 0:
        raise ValueError("The band holds no power (all levels at -inf dBm).")
    return quantity(10.0 * math.log10(total_mw), "dBm")


def dbm_per_hz(density: Quantity) -> float:
    """A power spectral density quantity (W/Hz, mW/Hz, …) as a number in dBm/Hz.

    The density half of
    :meth:`~labkit.instruments.drivers.siglent.measurement.Measurement.channel_power`
    is linear, since LabKit quantities cannot carry dBm/Hz.
    """
    return 10.0 * math.log10(float(density.to("mW/Hz").magnitude))
