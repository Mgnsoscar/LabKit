"""Keysight (Agilent) instrument drivers and the shared MXG signal-generator menus.

The menu classes here (Frequency, Power, Modulation, Sweep, Reference, System)
are the reusable building blocks; drivers such as :class:`N5183A` compose them
into an :class:`AnalogSignalGenerator`. Another MXG analog model reuses the
same menus instead of duplicating them — the same pattern as the R&S analyzer
and Aim-TTi generator packages.
"""

from __future__ import annotations

from ._signal_generator import AnalogSignalGenerator
from .frequency import Frequency
from .modulation import (
    AmplitudeModulation,
    FrequencyModulation,
    Modulation,
    PhaseModulation,
    PulseModulation,
)
from .n5183a import N5183A
from .power import Power
from .reference import Reference
from .sweep import Sweep
from .system import System

__all__ = [
    "N5183A",
    "AnalogSignalGenerator",
    "Frequency",
    "Power",
    "Modulation",
    "AmplitudeModulation",
    "FrequencyModulation",
    "PhaseModulation",
    "PulseModulation",
    "Sweep",
    "Reference",
    "System",
]
