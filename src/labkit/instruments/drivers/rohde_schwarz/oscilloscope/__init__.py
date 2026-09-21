"""Rohde & Schwarz RTO6-family oscilloscopes.

- :class:`Oscilloscope` — the shared base, composed from the menus below.
- :class:`RTO64` — the four-channel RTO6 model.

Menus: :class:`Channel` (``scope.channel(n)``), :class:`Timebase`,
:class:`Acquisition`, :class:`Trigger`, :class:`Waveform`, :class:`History`,
:class:`Measurement`, :class:`Math` and :class:`System`.
"""

from __future__ import annotations

from ._common import WaveformHeader
from ._oscilloscope import Oscilloscope
from .acquisition import Acquisition
from .channel import Channel
from .history import History, HistoryTimestamp
from .math import Math
from .measurement import Measurement
from .rto64 import RTO64
from .system import System
from .timebase import Timebase
from .trigger import Trigger
from .waveform import Waveform

__all__ = [
    "RTO64",
    "Oscilloscope",
    "Channel",
    "Timebase",
    "Acquisition",
    "Trigger",
    "Waveform",
    "WaveformHeader",
    "History",
    "HistoryTimestamp",
    "Measurement",
    "Math",
    "System",
]
