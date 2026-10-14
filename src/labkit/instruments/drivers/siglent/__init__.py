"""Siglent instrument drivers and their shared menus.

The SHA850A handheld spectrum analyzers (:class:`SHA851A`, 3.6 GHz, and
:class:`SHA852A`, 7.5 GHz) are built the same way as the Rohde & Schwarz
analyzers: a base, :class:`SHA850A`, composed from reusable per-topic menus
(Frequency, Bandwidth, Sweep, Amplitude, Trace, Marker, Measurement,
ReferenceOscillator, System), with thin concrete models on top. The base adds
the robust single-sweep and CW-reading sequences
(:meth:`SHA850A.single_sweep`, :meth:`SHA850A.measure_cw`).

:func:`integrate_band` computes a band's power from a trace, for an analyzer
without the channel-power option.
"""

from __future__ import annotations

from ._spectrum_analyzer import SHA850A
from .amplitude import Amplitude
from .band import GAUSSIAN_NOISE_BW_FACTOR, dbm_per_hz, integrate_band
from .bandwidth import Bandwidth
from .frequency import Frequency
from .marker import Marker
from .measurement import Measurement
from .sha851a import SHA851A
from .sha852a import SHA852A
from .sweep import Sweep
from .system import MINIMUM_FIRMWARE, Identity, ReferenceOscillator, System
from .trace import Trace

__all__ = [
    "SHA851A",
    "SHA852A",
    "SHA850A",
    "Frequency",
    "Bandwidth",
    "Sweep",
    "Amplitude",
    "Trace",
    "Marker",
    "Measurement",
    "ReferenceOscillator",
    "System",
    "Identity",
    "MINIMUM_FIRMWARE",
    "integrate_band",
    "dbm_per_hz",
    "GAUSSIAN_NOISE_BW_FACTOR",
]
