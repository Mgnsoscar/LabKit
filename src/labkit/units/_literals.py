"""Auto-generated unit-name literals for editor autocompletion.

The :data:`UnitName` literal lets editors suggest every known unit name
when you type ``Unit("...")``.

This file is GENERATED. Do not edit by hand. Regenerate it with::

    python scripts/generate_unit_literals.py
"""

from __future__ import annotations

from typing import Literal

__all__ = ["UnitName"]

UnitName = Literal[
    # Frequency
    "Hz", "nHz", "uHz", "mHz", "kHz", "MHz", "GHz", "THz", "hertz",
    # Power (linear)
    "W", "nW", "uW", "mW", "kW", "MW", "GW", "TW", "watt",
    # Time
    "s", "ns", "us", "ms", "ks", "Ms", "Gs", "Ts", "second", "min", "minute", "hour", "day",
    # Electrical
    "V", "nV", "uV", "mV", "kV", "MV", "GV", "TV", "A", "nA", "uA", "mA", "kA", "MA", "GA", "TA", "ohm", "nohm", "uohm", "mohm", "kohm", "Mohm", "Gohm", "Tohm", "volt", "ampere",
    # Power (logarithmic)
    "dBm", "dBW", "dB", "decibel",
    # Angle
    "deg", "degree", "rad", "radian",
    # Ratio
    "percent", "dimensionless",
]
"""Every unit name LabKit understands, as a ``Literal`` for autocompletion."""
