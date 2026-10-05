"""Markers (``:CALCulate:MARKer`` subsystem).

Verified against the *SHA850A User Manual* (EN01D) §3.9.1–§3.9.12: marker state,
mode, trace, X/Y read-out, marker functions, the peak searches and their
criteria. The SHA850A has eight markers.
"""

from __future__ import annotations

from typing import Literal

from ....units import Quantity
from ...base import BaseInstrument, Menu
from . import _common as c

__all__ = ["Marker", "MarkerMode", "MarkerFunction"]

#: Marker type (§3.9.3): normal (``POSition``), delta, fixed or off.
MarkerMode = Literal["POSition", "DELTa", "FIXed", "OFF"]
#: Marker function (§3.9.11): none, frequency counter, noise marker, N dB bandwidth.
MarkerFunction = Literal["OFF", "FCOunt", "NOISe", "NDB"]

_MARKERS = range(1, 9)


class Marker(Menu):
    """One of the analyzer's markers, addressed by number (1-8).

    Get a marker from the driver with ``analyzer.marker(1)``. A level read with
    :meth:`get_y` is only the plain trace level while the marker is a normal
    (``POSition``) marker with its function ``OFF``; a delta marker reads a
    difference and the noise marker a density.
    """

    def __init__(self, parent: BaseInstrument, number: int = 1) -> None:
        super().__init__(parent)
        if int(number) not in _MARKERS:
            raise ValueError(f"Marker must be 1–8, got {number}.")
        self.number = int(number)

    def enable(self, enabled: bool = True) -> None:
        """Switch the marker on/off (``:CALC:MARK<n>:STAT``)."""
        self.write(f":CALC:MARK{self.number}:STAT {c.onoff(enabled)}")

    def is_enabled(self) -> bool:
        return c.parse_bool(self.query(f":CALC:MARK{self.number}:STAT?"))

    def set_mode(self, mode: MarkerMode) -> None:
        """Set the marker type, normal/delta/fixed/off (``:CALC:MARK<n>:MODE``)."""
        self.write(f":CALC:MARK{self.number}:MODE {mode}")

    def set_trace(self, trace: int) -> None:
        """Put the marker on a trace, 1-6 (``:CALC:MARK<n>:TRAC``)."""
        if not 1 <= int(trace) <= 6:
            raise ValueError(f"Trace must be 1–6, got {trace}.")
        self.write(f":CALC:MARK{self.number}:TRAC {int(trace)}")

    def set_function(self, function: MarkerFunction) -> None:
        """Select the marker function (``:CALC:MARK<n>:FUNC``); ``OFF`` for a plain level read-out."""
        self.write(f":CALC:MARK{self.number}:FUNC {function}")

    def set_x(self, frequency: Quantity) -> None:
        """Position the marker at a frequency (``:CALC:MARK<n>:X``)."""
        self.write(f":CALC:MARK{self.number}:X {c.hz(frequency)}")

    def get_x(self) -> Quantity:
        """Read the marker's frequency (``:CALC:MARK<n>:X?``)."""
        return c.as_frequency(self.query(f":CALC:MARK{self.number}:X?"))

    def get_y(self) -> Quantity:
        """Read the marker's level in dBm (``:CALC:MARK<n>:Y?``)."""
        return c.as_power(self.query(f":CALC:MARK{self.number}:Y?"))

    def peak_search(self) -> None:
        """Move the marker to the trace maximum (``:CALC:MARK<n>:MAX``).

        The search honours the peak criteria (:meth:`set_peak_threshold_enabled`,
        :meth:`set_peak_excursion_enabled`): a peak that fails them is not found
        and the marker stays where it was (§3.9.12).
        """
        self.write(f":CALC:MARK{self.number}:MAX")

    def set_peak_threshold_enabled(self, enabled: bool) -> None:
        """Switch the peak-search threshold criterion on/off (``:CALC:MARK:PEAK:THR:STAT``).

        The criterion is shared by every marker's peak search (§3.9.12.2); off,
        the threshold is the analyzer's minimum (−200 dBm).
        """
        self.write(f":CALC:MARK:PEAK:THR:STAT {c.onoff(enabled)}")

    def set_peak_excursion_enabled(self, enabled: bool) -> None:
        """Switch the peak-search excursion criterion on/off (``:CALC:MARK:PEAK:EXC:STAT``).

        Shared by every marker's peak search (§3.9.12.2); off, any excursion counts.
        """
        self.write(f":CALC:MARK:PEAK:EXC:STAT {c.onoff(enabled)}")

    def next_peak(self) -> None:
        """Move the marker to the next peak (``:CALC:MARK<n>:MAX:NEXT``)."""
        self.write(f":CALC:MARK{self.number}:MAX:NEXT")

    def min_search(self) -> None:
        """Move the marker to the trace minimum (``:CALC:MARK<n>:MIN``)."""
        self.write(f":CALC:MARK{self.number}:MIN")

    def to_center(self) -> None:
        """Set the center frequency to the marker frequency.

        Implemented as read-then-set (``:CALC:MARK<n>:X?`` then ``:FREQ:CENT``)
        rather than the manual's ``:CALC:MARK<n>:CENT`` (§3.9.10.1), so it uses
        only commands the rest of the driver already depends on.
        """
        self.write(f":FREQ:CENT {c.hz(self.get_x())}")
