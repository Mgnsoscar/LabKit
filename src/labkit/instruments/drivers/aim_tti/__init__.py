"""Aim-TTi instrument drivers and the shared TGR-family signal-generator menus.

The menu classes here (Frequency, Output, Modulation, Sweep, Reference, System)
are the reusable building blocks; drivers such as :class:`TGR6000` compose them
into a :class:`SignalGenerator`. A future TGR-family generator reuses the same
menus instead of duplicating them — the same pattern as the R&S analyzer package.
"""

from __future__ import annotations

from ._signal_generator import SignalGenerator
from .frequency import Frequency
from .modulation import Modulation, ModulationNotSupportedError
from .output import Output
from .reference import Reference
from .sweep import Sweep
from .system import System
from .tgr6000 import TGR6000

__all__ = [
    "TGR6000",
    "SignalGenerator",
    "Frequency",
    "Output",
    "Modulation",
    "ModulationNotSupportedError",
    "Sweep",
    "Reference",
    "System",
]
