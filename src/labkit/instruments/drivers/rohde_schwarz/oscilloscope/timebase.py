"""The horizontal axis: time per division, acquisition time, reference point.

Verified against the *R&S RTO6 User Manual*, chapter 24.8.2 "Time base":
``TIMebase:SCALe``, ``TIMebase:RANGe``, ``TIMebase:HORizontal:POSition``,
``TIMebase:REFerence`` and ``TIMebase:DIVisions?``.
"""

from __future__ import annotations

from .....units import Quantity, ensure_time
from ....base import Menu
from . import _common as c

__all__ = ["Timebase"]


class Timebase(Menu):
    """Horizontal scale, acquisition time and trigger/reference position."""

    def set_scale(self, seconds_per_division: Quantity) -> None:
        """Set the horizontal scale in seconds per division (``TIM:SCAL``), 25 ps/div – 10 ks/div."""
        ensure_time(seconds_per_division)
        self.write(f"TIM:SCAL {c.seconds(seconds_per_division)}")

    def get_scale(self) -> Quantity:
        return c.as_seconds(self.query("TIM:SCAL?"))

    def set_range(self, acquisition_time: Quantity) -> None:
        """Set the time of one acquisition across all divisions (``TIM:RANG``)."""
        ensure_time(acquisition_time)
        self.write(f"TIM:RANG {c.seconds(acquisition_time)}")

    def get_range(self) -> Quantity:
        return c.as_seconds(self.query("TIM:RANG?"))

    def set_position(self, offset: Quantity) -> None:
        """Set the time between the reference point and the trigger point (``TIM:HOR:POS``).

        Positive values show what happened before the trigger at the reference
        point; the trigger itself moves to the right of it.
        """
        ensure_time(offset)
        self.write(f"TIM:HOR:POS {c.seconds(offset)}")

    def get_position(self) -> Quantity:
        return c.as_seconds(self.query("TIM:HOR:POS?"))

    def set_reference(self, percent: float) -> None:
        """Set the reference point as a percentage of the screen width, 0–100 (``TIM:REF``)."""
        if not 0 <= percent <= 100:
            raise ValueError("Reference position must be between 0 and 100 %.")
        self.write(f"TIM:REF {c.percent(percent)}")

    def get_reference(self) -> float:
        return c.parse_float(self.query("TIM:REF?"))

    def get_divisions(self) -> int:
        """The number of horizontal divisions on screen (``TIM:DIV?``)."""
        return c.parse_int(self.query("TIM:DIV?"))
