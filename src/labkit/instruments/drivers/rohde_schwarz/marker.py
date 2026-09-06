"""Markers (``CALCulate:MARKer`` subsystem)."""

from __future__ import annotations

from ....units import Quantity
from ...base import BaseInstrument, Menu
from . import _common as c

__all__ = ["Marker"]


class Marker(Menu):
    """One of the analyzer's markers, addressed by number (1-16).

    Get a marker from the driver with ``analyzer.marker(1)``.
    """

    def __init__(self, parent: BaseInstrument, number: int = 1) -> None:
        super().__init__(parent)
        self.number = number

    def enable(self, enabled: bool = True) -> None:
        """Switch the marker on/off (``CALC:MARK<n>:STAT``)."""
        self.write(f"CALC:MARK{self.number}:STAT {c.onoff(enabled)}")

    def set_x(self, frequency: Quantity) -> None:
        """Position the marker at a frequency (``CALC:MARK<n>:X``)."""
        self.write(f"CALC:MARK{self.number}:X {c.hz(frequency)}")

    def get_x(self) -> Quantity:
        """Read the marker's frequency (``CALC:MARK<n>:X?``)."""
        return c.as_frequency(self.query(f"CALC:MARK{self.number}:X?"))

    def get_y(self) -> Quantity:
        """Read the marker's level in dBm (``CALC:MARK<n>:Y?``)."""
        return c.as_power(self.query(f"CALC:MARK{self.number}:Y?"))

    def peak_search(self) -> None:
        """Move the marker to the trace maximum (``CALC:MARK<n>:MAX``)."""
        self.write(f"CALC:MARK{self.number}:MAX")

    def next_peak(self) -> None:
        """Move the marker to the next-lower peak (``CALC:MARK<n>:MAX:NEXT``)."""
        self.write(f"CALC:MARK{self.number}:MAX:NEXT")

    def min_search(self) -> None:
        """Move the marker to the trace minimum (``CALC:MARK<n>:MIN``)."""
        self.write(f"CALC:MARK{self.number}:MIN")

    def to_center(self) -> None:
        """Set the center frequency to the marker frequency.

        Implemented as read-then-set (robust across firmware) rather than the
        optional marker-function command.
        """
        self.write(f"FREQ:CENT {c.hz(self.get_x())}")

    def to_ref_level(self) -> None:
        """Set the reference level to the marker level (read-then-set)."""
        self.write(f"DISP:TRAC:Y:SCAL:RLEV {c.dbm(self.get_y())}")
