"""Sweep configuration (``[SENSe:]SWEep`` and ``INITiate`` subsystems)."""

from __future__ import annotations

from typing import Literal

from ....units import Quantity
from ...base import Menu
from . import _common as c

__all__ = ["Sweep", "SweepType"]

#: How the analyzer acquires the spectrum.
SweepType = Literal["AUTO", "SWEEP", "FFT"]

_SWEEP_TYPE_SCPI = {"AUTO": "AUTO", "SWEEP": "SWE", "FFT": "FFT"}


class Sweep(Menu):
    """Number of points, sweep time, averaging count, and run mode."""

    def set_points(self, points: int) -> None:
        """Set the number of sweep (measurement) points (``SWE:POIN``)."""
        self.write(f"SWE:POIN {points}")

    def get_points(self) -> int:
        return c.parse_int(self.query("SWE:POIN?"))

    def set_time(self, time: Quantity) -> None:
        """Set the sweep time (``SWE:TIME``). Disables sweep-time auto-coupling."""
        self.write(f"SWE:TIME {c.seconds(time)}")

    def get_time(self) -> Quantity:
        return c.as_seconds(self.query("SWE:TIME?"))

    def set_time_auto(self, enabled: bool) -> None:
        """Couple the sweep time to span/RBW/VBW (``SWE:TIME:AUTO``)."""
        self.write(f"SWE:TIME:AUTO {c.onoff(enabled)}")

    def set_count(self, count: int) -> None:
        """Set the number of sweeps to average/max-hold over (``SWE:COUN``).

        ``0`` means continuous averaging over all sweeps.
        """
        self.write(f"SWE:COUN {count}")

    def get_count(self) -> int:
        return c.parse_int(self.query("SWE:COUN?"))

    def set_continuous(self, enabled: bool) -> None:
        """Continuous (``True``) vs single (``False``) sweeping (``INIT:CONT``)."""
        self.write(f"INIT:CONT {c.onoff(enabled)}")

    def is_continuous(self) -> bool:
        return c.parse_bool(self.query("INIT:CONT?"))

    def set_type(self, sweep_type: SweepType) -> None:
        """Select sweep vs FFT acquisition (``SWE:TYPE``)."""
        self.write(f"SWE:TYPE {_SWEEP_TYPE_SCPI[sweep_type]}")
