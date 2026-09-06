"""Diagram (window) and trace-display control (``DISPlay``, ``SYSTem:DISPlay``).

Creates and deletes diagram areas ("windows"), assigns traces to them, autoscales,
and sets the vertical scale — plus the remote display-update switch. A trace
created with
:meth:`~labkit.instruments.drivers.rohde_schwarz.vna.trace.Trace.create` is not
visible until :meth:`feed_trace` assigns it to a window. Verified against the *R&S
ZNL/ZNLE User Manual*: ``DISPlay[:WINDow<Wnd>]...`` and ``SYSTem:DISPlay:UPDate``.

Vertical-scale values (reference level, scale-per-division) are in the displayed
trace's format unit (e.g. dB), so they are passed and returned as plain floats.
"""

from __future__ import annotations

from ....base import Menu
from . import _common as c

__all__ = ["Display"]


class Display(Menu):
    """Diagram windows, trace assignment, scaling and the display-update switch."""

    # -- windows -----------------------------------------------------------
    def set_window_state(self, window: int, enabled: bool) -> None:
        """Create (``True``) or delete (``False``) a diagram window (``DISP:WIND<w>:STAT``)."""
        self.write(f"DISP:WIND{window}:STAT {c.onoff(enabled)}")

    def window_catalog(self) -> list[str]:
        """List the numbers of the existing diagram windows (``DISP:WIND:CAT?``)."""
        return [w for w in c.parse_name(self.query("DISP:WIND:CAT?")).split(",") if w]

    # -- traces in windows -------------------------------------------------
    def feed_trace(self, window: int, window_trace: int, name: str) -> None:
        """Assign an existing trace to a window and show it (``DISP:WIND<w>:TRAC<t>:FEED``)."""
        self.write(f"DISP:WIND{window}:TRAC{window_trace}:FEED {c.quoted(name)}")

    def delete_trace(self, window: int, window_trace: int) -> None:
        """Remove a trace from a window (``DISP:WIND<w>:TRAC<t>:DEL``)."""
        self.write(f"DISP:WIND{window}:TRAC{window_trace}:DEL")

    # -- vertical scale ----------------------------------------------------
    def autoscale(self, window: int, window_trace: int) -> None:
        """Autoscale a displayed trace once (``DISP:WIND<w>:TRAC<t>:Y:SCAL:AUTO ONCE``)."""
        self.write(f"DISP:WIND{window}:TRAC{window_trace}:Y:SCAL:AUTO ONCE")

    def set_reference_level(self, window: int, level: float, window_trace: int = 1) -> None:
        """Set the reference level of a displayed trace (``…:Y:SCAL:RLEV``), in the trace unit."""
        self.write(
            f"DISP:WIND{window}:TRAC{window_trace}:Y:SCAL:RLEV {c.scpi_number(level)}"
        )

    def set_scale_per_division(
        self, window: int, value: float, window_trace: int = 1
    ) -> None:
        """Set the vertical scale per division (``…:Y:SCAL:PDIV``), in the trace unit."""
        self.write(
            f"DISP:WIND{window}:TRAC{window_trace}:Y:SCAL:PDIV {c.scpi_number(value)}"
        )

    # -- remote display ----------------------------------------------------
    def set_update(self, enabled: bool) -> None:
        """Update the screen during remote control (``SYST:DISP:UPD``).

        Off by default under remote control (for speed); turning it on is useful
        while developing a measurement.
        """
        self.write(f"SYST:DISP:UPD {c.onoff(enabled)}")
