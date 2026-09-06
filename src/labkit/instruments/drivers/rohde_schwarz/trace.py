"""Trace configuration and data retrieval (``DISPlay:TRACe``, ``TRACe``)."""

from __future__ import annotations

from typing import Literal

import numpy as np

from ....units import Quantity, quantity
from ...base import Menu
from . import _common as c

__all__ = ["Trace", "TraceMode", "Detector"]

#: How a trace accumulates successive sweeps.
TraceMode = Literal["WRITE", "AVERAGE", "MAXHOLD", "MINHOLD", "VIEW", "BLANK"]
#: Detector applied when compressing samples into trace points.
Detector = Literal["AUTO", "POSITIVE", "NEGATIVE", "SAMPLE", "RMS", "AVERAGE", "QPEAK"]

_MODE_SCPI = {
    "WRITE": "WRIT", "AVERAGE": "AVER", "MAXHOLD": "MAXH",
    "MINHOLD": "MINH", "VIEW": "VIEW", "BLANK": "BLAN",
}
_DETECTOR_SCPI = {
    "AUTO": "APE", "POSITIVE": "POS", "NEGATIVE": "NEG", "SAMPLE": "SAMP",
    "RMS": "RMS", "AVERAGE": "AVER", "QPEAK": "QPE",
}


class Trace(Menu):
    """Configure the six traces and read their data.

    Methods take a 1-based `trace` index (1-6); it defaults to trace 1.
    """

    def set_mode(self, mode: TraceMode, trace: int = 1) -> None:
        """Set the trace mode, e.g. write, average, max-hold (``DISP:TRAC:MODE``)."""
        self.write(f"DISP:TRAC{trace}:MODE {_MODE_SCPI[mode]}")

    def set_state(self, enabled: bool, trace: int = 1) -> None:
        """Show or hide a trace (``DISP:TRAC<t>``)."""
        self.write(f"DISP:TRAC{trace} {c.onoff(enabled)}")

    def set_detector(self, detector: Detector, trace: int = 1) -> None:
        """Set the trace detector (``DET<t>``)."""
        self.write(f"DET{trace} {_DETECTOR_SCPI[detector]}")

    def _set_ascii_format(self) -> None:
        self.write("FORM ASC")

    def get_y(self, trace: int = 1) -> Quantity:
        """Fetch a trace's y-values as a power array in dBm (``TRAC:DATA?``).

        The values are returned in the instrument's current amplitude unit,
        which is dBm by default.
        """
        self._set_ascii_format()
        response = self.query(f"TRAC:DATA? TRACE{trace}")
        values = np.array([float(v) for v in response.split(",") if v.strip()])
        return quantity(values, "dBm")

    def get_x(self, trace: int = 1) -> Quantity:
        """Compute the frequency axis for a trace from start/stop/points.

        Deriving x from the span settings is firmware-independent (more robust
        than the optional ``TRAC:DATA:X?`` query).
        """
        start = c.parse_float(self.query("FREQ:STAR?"))
        stop = c.parse_float(self.query("FREQ:STOP?"))
        points = c.parse_int(self.query("SWE:POIN?"))
        return quantity(np.linspace(start, stop, points), "Hz")

    def get_data(self, trace: int = 1) -> tuple[Quantity, Quantity]:
        """Return ``(frequencies, levels)`` for a trace as quantity arrays."""
        return self.get_x(trace), self.get_y(trace)
