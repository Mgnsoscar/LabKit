"""Markers on the active trace (``CALCulate<Chn>:MARKer`` subsystem).

A marker reads a stimulus/response point on a channel's active trace and can be
moved to peaks and minima by a search. Get one from the driver with
``vna.marker(1)``. The marker's response value (:meth:`Marker.get_y`) is in the
active trace format's unit, so it is returned as a plain float.

Verified against the *R&S ZNL/ZNLE User Manual*, ``CALCulate<Chn>:MARKer<Mk>...``.
"""

from __future__ import annotations

from typing import Literal

from .....units import Quantity
from ....base import BaseInstrument, Menu
from . import _common as c

__all__ = ["Marker", "SearchMode", "MarkerMode"]

#: Peak/target search executed by :meth:`Marker.search`.
SearchMode = Literal["MAX", "MIN", "NEXT_PEAK", "PEAK_LEFT", "PEAK_RIGHT"]
#: Marker tracking mode.
MarkerMode = Literal["NORMAL", "FIXED", "ARBITRARY"]

_SEARCH_SCPI = {
    "MAX": "MAX", "MIN": "MIN", "NEXT_PEAK": "NPE",
    "PEAK_LEFT": "LPE", "PEAK_RIGHT": "RPE",
}
_MODE_SCPI = {"NORMAL": "NORM", "FIXED": "FIX", "ARBITRARY": "ARB"}


class Marker(Menu):
    """One marker on a channel's active trace, addressed by number.

    Get a marker with ``vna.marker(1)`` (optionally ``channel=`` for a channel
    other than 1). Create it on the instrument with :meth:`enable` before use.
    """

    def __init__(self, parent: BaseInstrument, number: int = 1, channel: int = 1) -> None:
        super().__init__(parent)
        self.number = number
        self.channel = channel

    def _base(self) -> str:
        return f"CALC{self.channel}:MARK{self.number}"

    def enable(self, enabled: bool = True) -> None:
        """Create/remove the marker (``CALC<Chn>:MARK<Mk>:STAT``)."""
        self.write(f"{self._base()}:STAT {c.onoff(enabled)}")

    def set_x(self, frequency: Quantity) -> None:
        """Position the marker at a stimulus frequency (``CALC<Chn>:MARK<Mk>:X``)."""
        self.write(f"{self._base()}:X {c.hz(frequency)}")

    def get_x(self) -> Quantity:
        """Read the marker's stimulus frequency (``CALC<Chn>:MARK<Mk>:X?``)."""
        return c.as_frequency(self.query(f"{self._base()}:X?"))

    def get_y(self) -> float:
        """Read the marker's response value (``CALC<Chn>:MARK<Mk>:Y?``).

        The unit follows the active trace's format (dB, degrees, …), so a plain
        float is returned.
        """
        return c.parse_float(self.query(f"{self._base()}:Y?"))

    def set_mode(self, mode: MarkerMode) -> None:
        """Set the marker mode: normal, fixed or arbitrary (``CALC<Chn>:MARK<Mk>:TYPE``)."""
        self.write(f"{self._base()}:TYPE {_MODE_SCPI[mode]}")

    def set_format(self, marker_format: str) -> None:
        """Set the marker's output format (``CALC<Chn>:MARK<Mk>:FORM``).

        Accepts the R&S marker-format keywords (e.g. ``MLOG``, ``PHAS``,
        ``IMP``); ``DEF`` uses the trace's default marker format.
        """
        self.write(f"{self._base()}:FORM {marker_format}")

    def search(self, mode: SearchMode = "MAX") -> None:
        """Move the marker to a peak/minimum (``CALC<Chn>:MARK<Mk>:FUNC:EXEC``).

        `mode` selects maximum, minimum, next peak, or the peak to the left/right
        of the current position.
        """
        self.write(f"{self._base()}:FUNC:EXEC {_SEARCH_SCPI[mode]}")

    def peak_search(self) -> None:
        """Move the marker to the trace maximum (``…:FUNC:EXEC MAX``)."""
        self.search("MAX")

    def min_search(self) -> None:
        """Move the marker to the trace minimum (``…:FUNC:EXEC MIN``)."""
        self.search("MIN")

    def get_search_result(self) -> tuple[float, float]:
        """Return the last search result as ``(response, stimulus)`` (``…:FUNC:RES?``)."""
        values = c.parse_float_array(self.query(f"{self._base()}:FUNC:RES?"))
        return float(values[0]), float(values[1])

    def set_delta(self, enabled: bool) -> None:
        """Reference this marker's readings to the reference marker (``…:DELT:STAT``)."""
        self.write(f"{self._base()}:DELT:STAT {c.onoff(enabled)}")

    def all_off(self) -> None:
        """Remove all markers on the active trace (``CALC<Chn>:MARK<Mk>:AOFF``)."""
        self.write(f"CALC{self.channel}:MARK:AOFF")
