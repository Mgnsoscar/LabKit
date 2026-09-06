"""Rohde & Schwarz instrument drivers and the shared FSV-family menus.

The menu classes here (Frequency, Bandwidth, Sweep, Amplitude, Trace, Marker,
Display, ReferenceOscillator) are the reusable building blocks; drivers such as
:class:`FSV3007` compose them. A future FPL1003 driver reuses the same menus
instead of duplicating them.
"""

from __future__ import annotations

from ._spectrum_analyzer import SpectrumAnalyzer
from .amplitude import Amplitude
from .bandwidth import Bandwidth
from .fpl1003 import FPL1003
from .frequency import Frequency
from .fsv3007 import FSV3007
from .marker import Marker
from .sweep import Sweep
from .system import Display, ReferenceOscillator
from .trace import Trace

__all__ = [
    "FSV3007",
    "FPL1003",
    "SpectrumAnalyzer",
    "Frequency",
    "Bandwidth",
    "Sweep",
    "Amplitude",
    "Trace",
    "Marker",
    "Display",
    "ReferenceOscillator",
]
