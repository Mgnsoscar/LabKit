"""Trace management, formatting and data retrieval.

A VNA trace is a named object that measures one result (an S-parameter such as
``S21``) in a channel; its *format* (dB magnitude, phase, Smith, …) decides how
the complex result is post-processed for display and for formatted reads.

This menu covers the whole trace life cycle — create, select, rename the measured
result, list, delete — the display format, and the three ways to read data:

- :meth:`get_formatted_data` — the trace in its current format (``CALC:DATA? FDAT``),
- :meth:`get_complex_data` — the raw complex result (``CALC:DATA? SDAT``),
- :meth:`get_stimulus` — the stimulus (frequency) axis (``CALC:DATA:STIM?``).

Verified against the *R&S ZNL/ZNLE User Manual*: ``CALCulate<Ch>:PARameter:...``,
``CALCulate<Chn>:FORMat`` and ``CALCulate<Chn>:DATA...``.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from .....units import Quantity
from ....base import Menu
from . import _common as c

__all__ = ["Trace", "SParameter", "TraceFormat"]

#: The S-parameters a 2-port VNA can measure.
SParameter = Literal["S11", "S12", "S21", "S22"]

#: How the complex result is post-processed for display / formatted reads.
TraceFormat = Literal[
    "MLOG", "MLIN", "PHASE", "UPHASE", "POLAR", "SMITH", "ISMITH",
    "GDELAY", "REAL", "IMAG", "SWR", "COMPLEX",
]

_FORMAT_SCPI = {
    "MLOG": "MLOG", "MLIN": "MLIN", "PHASE": "PHAS", "UPHASE": "UPH",
    "POLAR": "POL", "SMITH": "SMIT", "ISMITH": "ISM", "GDELAY": "GDEL",
    "REAL": "REAL", "IMAG": "IMAG", "SWR": "SWR", "COMPLEX": "COMP",
}


class Trace(Menu):
    """Create, select, format and read the traces of a channel.

    Most methods take a 1-based `channel` (default 1). Traces are addressed by a
    string `name` (e.g. ``"Trc1"``); the name must be unique across channels and
    diagrams. A newly created trace becomes the channel's active trace but is not
    shown until assigned to a diagram with
    :meth:`~labkit.instruments.drivers.rohde_schwarz.vna.display.Display.feed_trace`.
    """

    # -- life cycle --------------------------------------------------------
    def create(self, name: str, parameter: SParameter, channel: int = 1) -> None:
        """Create a trace measuring `parameter` (``CALC<Ch>:PAR:SDEF``).

        If channel `channel` does not exist it is created. If a trace with `name`
        already exists in the channel it is overwritten.
        """
        self.write(
            f"CALC{channel}:PAR:SDEF {c.quoted(name)},{c.quoted(parameter)}"
        )

    def select(self, name: str, channel: int = 1) -> None:
        """Select `name` as the channel's active trace (``CALC<Ch>:PAR:SEL``)."""
        self.write(f"CALC{channel}:PAR:SEL {c.quoted(name)}")

    def get_selected(self, channel: int = 1) -> str:
        """Return the channel's active trace name (``CALC<Ch>:PAR:SEL?``)."""
        return c.parse_name(self.query(f"CALC{channel}:PAR:SEL?"))

    def set_measured_parameter(
        self, name: str, parameter: SParameter, channel: int = 1
    ) -> None:
        """Change the S-parameter an existing trace measures (``CALC<Ch>:PAR:MEAS``)."""
        self.write(
            f"CALC{channel}:PAR:MEAS {c.quoted(name)},{c.quoted(parameter)}"
        )

    def catalog(self, channel: int = 1) -> list[tuple[str, str]]:
        """List the channel's traces as ``(name, parameter)`` (``CALC<Ch>:PAR:CAT?``)."""
        return c.parse_catalog(self.query(f"CALC{channel}:PAR:CAT?"))

    def delete(self, name: str, channel: int = 1) -> None:
        """Delete the named trace (``CALC<Ch>:PAR:DEL``)."""
        self.write(f"CALC{channel}:PAR:DEL {c.quoted(name)}")

    def delete_all(self) -> None:
        """Delete every trace in every channel (``CALC:PAR:DEL:ALL``)."""
        self.write("CALC:PAR:DEL:ALL")

    # -- format ------------------------------------------------------------
    def set_format(self, trace_format: TraceFormat, channel: int = 1) -> None:
        """Set the active trace's display format (``CALC<Chn>:FORM``)."""
        self.write(f"CALC{channel}:FORM {_FORMAT_SCPI[trace_format]}")

    def get_format(self, channel: int = 1) -> str:
        """Read the active trace's display format (``CALC<Chn>:FORM?``)."""
        return self.query(f"CALC{channel}:FORM?").strip()

    # -- data --------------------------------------------------------------
    def _set_ascii_format(self) -> None:
        self.write("FORM ASC")

    def get_stimulus(self, channel: int = 1) -> Quantity:
        """Read the active trace's stimulus (frequency) axis (``CALC<Chn>:DATA:STIM?``)."""
        self._set_ascii_format()
        values = c.parse_float_array(self.query(f"CALC{channel}:DATA:STIM?"))
        return Quantity(values, "Hz")

    def get_formatted_data(self, channel: int = 1) -> tuple[Quantity, np.ndarray]:
        """Return ``(stimulus, values)`` for the active trace (``CALC<Chn>:DATA? FDAT``).

        `values` is the trace in its current :meth:`set_format` format; its unit
        depends on that format (dB for ``MLOG``, degrees for ``PHASE``, …) so it
        is returned as a plain array rather than a quantity.
        """
        self._set_ascii_format()
        stimulus = self.get_stimulus(channel)
        values = c.parse_float_array(self.query(f"CALC{channel}:DATA? FDAT"))
        return stimulus, values

    def get_complex_data(self, channel: int = 1) -> tuple[Quantity, np.ndarray]:
        """Return ``(stimulus, values)`` with the raw complex result (``CALC<Chn>:DATA? SDAT``).

        `values` is a complex array (the unformatted measured S-parameter), with
        `stimulus` the matching frequency axis.
        """
        self._set_ascii_format()
        stimulus = self.get_stimulus(channel)
        values = c.parse_complex_array(self.query(f"CALC{channel}:DATA? SDAT"))
        return stimulus, values
