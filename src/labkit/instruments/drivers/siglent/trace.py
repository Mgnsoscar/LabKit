"""Trace configuration and data retrieval (``:TRACe``, ``:FORMat``, detector, averaging).

Verified against the *SHA850A User Manual* (EN01D) §3.8–§3.8.4 (trace data,
format, type, state and detector) and §3.11.1.1–§3.11.1.2 (average type and
count). The SHA850A sets a trace's accumulation with ``:TRACe<n>:TYPE`` — the
SSA3000X Plus uses ``:TRACe<n>:MODE`` for the same thing — and its view/blank
state separately with ``:TRACe<n>:DISPlay``.

Trace data
----------
:meth:`Trace.get_data` reads the trace as **ASCII**. The analyzer also offers
``REAL32``/``REAL`` definite-length binary blocks, but over the raw socket (port
5025, ``\\n`` read termination) a binary block is fragile: any ``0x0A`` byte
inside the data ends the read early, and neither document states the byte order.
ASCII costs some transfer time and is unambiguous. The frequency axis is rebuilt
from start/stop and the number of values actually **returned**: in FFT mode the
analyzer may return fewer points than the sweep-point setting (§3.3.1).

Averaging bookkeeping
---------------------
The menu remembers which accumulation type and count it set on each trace, so
:meth:`~labkit.instruments.drivers.siglent._spectrum_analyzer.SHA850A.single_sweep`
knows how many sweeps one single acquisition takes and which averages to restart.
Settings made at the front panel are not seen; pass ``sweeps=`` to
``single_sweep`` then.
"""

from __future__ import annotations

from typing import Literal, Optional

import numpy as np

from ....units import Quantity, quantity
from ...base import BaseInstrument, Menu
from . import _common as c

__all__ = ["Trace", "TraceType", "TraceState", "Detector", "AverageType", "TraceFormat"]

#: How a trace accumulates successive sweeps (§3.8.2).
TraceType = Literal["WRITe", "MAXHold", "MINHold", "AVERage"]
#: Refresh/display state of a trace (§3.8.3).
TraceState = Literal["ACTIve", "VIEW", "BLANk", "BACKground"]
#: Detector applied when compressing samples into trace points (§3.8.4).
Detector = Literal["POSitive", "NEGative", "SAMPle", "AVERage", "NORMAL"]
#: What the average detector and trace averaging operate on (§3.11.1.1):
#: log power (video), power (RMS) or voltage.
AverageType = Literal["LOGPower", "POWer", "VOLTage"]
#: Trace-data transfer format (§3.8); only ASCII is read by :meth:`Trace.get_data`.
TraceFormat = Literal["ASCii", "REAL32", "REAL"]

_TRACES = range(1, 7)
#: Trace types whose terminal count N makes one single acquisition N sweeps.
_ACCUMULATING = ("AVERage", "MAXHold", "MINHold")
_COUNT_RANGE = (1, 999)


class Trace(Menu):
    """Configure the six traces and read their data.

    Methods take a 1-based `trace` index (1-6); it defaults to trace 1, except
    :meth:`set_type`, whose signature puts the trace first.
    """

    def __init__(self, parent: BaseInstrument) -> None:
        super().__init__(parent)
        self._types: dict[int, str] = {}
        self._counts: dict[int, int] = {}

    @staticmethod
    def _check(trace: int) -> int:
        if int(trace) not in _TRACES:
            raise ValueError(f"Trace must be 1–6, got {trace}.")
        return int(trace)

    # -- accumulation ---------------------------------------------------------
    def set_type(self, trace: int, trace_type: TraceType) -> None:
        """Set how a trace accumulates sweeps (``:TRAC<n>:TYPE``): clear-write, hold or average."""
        n = self._check(trace)
        self.write(f":TRAC{n}:TYPE {trace_type}")
        self._types[n] = trace_type

    def get_type(self, trace: int = 1) -> str:
        """The trace's accumulation type as the analyzer reports it (``WRITE``, ``AVER``, …)."""
        return self.query(f":TRAC{self._check(trace)}:TYPE?").strip()

    def set_average_count(self, count: int, trace: int = 1) -> None:
        """Set the average / hold count N, 1 … 999 (``:AVER:TRAC<n>:COUN``)."""
        n = self._check(trace)
        if not _COUNT_RANGE[0] <= int(count) <= _COUNT_RANGE[1]:
            raise ValueError(f"Average count must be {_COUNT_RANGE[0]}–{_COUNT_RANGE[1]}, got {count}.")
        self.write(f":AVER:TRAC{n}:COUN {int(count)}")
        self._counts[n] = int(count)

    def get_average_count(self, trace: int = 1) -> int:
        return c.parse_int(self.query(f":AVER:TRAC{self._check(trace)}:COUN?"))

    def clear_average(self, trace: int = 1) -> None:
        """Restart a trace's average (``:AVER:TRAC<n>:CLE``)."""
        self.write(f":AVER:TRAC{self._check(trace)}:CLE")

    def set_average_type(self, average_type: AverageType) -> None:
        """Select log-power, power (RMS) or voltage averaging (``:AVER:TYPE``).

        ``POWer`` with the ``AVERage`` detector is the RMS reading a power
        measurement wants.
        """
        self.write(f":AVER:TYPE {average_type}")

    def get_average_type(self) -> str:
        return self.query(":AVER:TYPE?").strip()

    def sweeps_per_acquisition(self) -> int:
        """How many sweeps one single acquisition takes, by what this menu configured.

        The largest count set on a trace whose type is average/max-hold/min-hold,
        else 1.
        """
        counts = [self._counts.get(n, 1) for n, kind in self._types.items() if kind in _ACCUMULATING]
        return max(counts, default=1)

    def averaging_traces(self) -> list[int]:
        """The traces this menu put into ``AVERage``, whose averages a single sweep restarts."""
        return sorted(n for n, kind in self._types.items() if kind == "AVERage")

    # -- state / detector -----------------------------------------------------
    def set_display_state(self, state: TraceState, trace: int = 1) -> None:
        """Set a trace active, frozen in view, blank or background (``:TRAC<n>:DISP``).

        A trace in ``VIEW`` is not refreshed — and an alignment run while a trace
        is in view gives a large error (firmware revision notes, 1.1.2.1.6R5).
        """
        self.write(f":TRAC{self._check(trace)}:DISP {state}")

    def set_detector(self, detector: Detector, trace: int = 1) -> None:
        """Set the trace detector (``:DET:TRAC<n>``)."""
        self.write(f":DET:TRAC{self._check(trace)} {detector}")

    def get_detector(self, trace: int = 1) -> str:
        return self.query(f":DET:TRAC{self._check(trace)}?").strip()

    def set_detector_auto(self, enabled: bool, trace: int = 1) -> None:
        """Let the analyzer choose the trace's detector (``:DET:TRAC<n>:AUTO``, takes 0|1)."""
        self.write(f":DET:TRAC{self._check(trace)}:AUTO {int(bool(enabled))}")

    # -- data -------------------------------------------------------------------
    def set_format(self, data_format: TraceFormat) -> None:
        """Set the trace-data transfer format (``:FORM``); :meth:`get_data` resets it to ASCII."""
        self.write(f":FORM {data_format}")

    def get_y(self, trace: int = 1) -> Quantity:
        """Fetch a trace's levels as a dBm array (``:FORM ASC``, ``:TRAC<n>:DATA?``).

        The values are in the instrument's y-axis unit, dBm unless changed with
        :meth:`~labkit.instruments.drivers.siglent.amplitude.Amplitude.set_unit`.
        Raises :class:`RuntimeError` when the analyzer returns no data.
        """
        n = self._check(trace)
        self.write(":FORM ASC")
        values = c.parse_float_list(self.query(f":TRAC{n}:DATA?"))
        if not values:
            raise RuntimeError(f"Trace {n} returned no data.")
        return quantity(np.array(values), "dBm")

    def get_x(self, trace: int = 1, *, points: Optional[int] = None) -> Quantity:
        """The frequency axis of a trace, from start/stop.

        The same call as the Rohde & Schwarz analyzers' ``get_x(trace)``. The
        number of points is the number of values the trace *returns*: FFT mode
        may return fewer than the sweep-point setting, so without `points` the
        trace is read (``:TRAC<n>:DATA?``) to size the axis. Pass `points` (a
        keyword) when the trace values are already in hand — :meth:`get_data`
        does — to skip that read.
        """
        n = self._check(trace)
        if points is None:
            points = len(self.get_y(n).magnitude)
        if int(points) < 1:
            raise ValueError(f"Points must be at least 1, got {points}.")
        start = c.parse_float(self.query(":FREQ:STAR?"))
        stop = c.parse_float(self.query(":FREQ:STOP?"))
        return quantity(np.linspace(start, stop, int(points)), "Hz")

    def get_data(self, trace: int = 1) -> tuple[Quantity, Quantity]:
        """Return ``(frequencies, levels)`` for a trace as quantity arrays (ASCII transfer)."""
        levels = self.get_y(trace)
        return self.get_x(trace, points=len(levels.magnitude)), levels
