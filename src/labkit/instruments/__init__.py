"""SCPI/VISA instrument control for LabKit.

Building blocks:

- :class:`TestEnvironment` — subclass it to declare and configure your bench.
- :class:`BaseInstrument` — base class for instrument drivers.
- :class:`Menu` — group related SCPI commands into sub-objects.
- :class:`DummyBackend` — offline backend that prints SCPI instead of sending.
- :mod:`labkit.instruments.registry` — the failsafe at-exit shutdown machinery.

Concrete drivers (spectrum analyzers, VNAs, signal generators) will live under
``labkit.instruments.drivers``; that package is a placeholder for now.

Importing this package does not import `pyvisa`; only creating a non-dummy
:class:`TestEnvironment` does. Install the extra with
``pip install "labkit[instruments]"``.
"""

from __future__ import annotations

from .base import BaseInstrument, Backend, DummyBackend, Menu
from .drivers import FPL1003, FSV3007, TGR6000, ZNLE18
from .environment import TestEnvironment
from .mock import MockBackend, MockEnvironment, mock_instrument

__all__ = [
    "TestEnvironment",
    "BaseInstrument",
    "Backend",
    "DummyBackend",
    "Menu",
    "FSV3007",
    "FPL1003",
    "ZNLE18",
    "TGR6000",
    "MockBackend",
    "MockEnvironment",
    "mock_instrument",
]
