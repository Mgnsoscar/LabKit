"""Reading waveform records: channel and math data with their x axes.

The transfer format is ASCII (``FORMat:DATA ASCii``) and the x values are left
out of the transfer (``EXPort:WAVeform:INCXvalues OFF``): the header
(``...:DATA:HEADer?``) gives the x start, x stop and record length, from which
the axis is rebuilt exactly. That keeps the transport a plain text query the
LabKit backend understands; a binary ``REAL,32`` transfer would be faster for
very long records and can be added on the same header logic.

Verified against the *R&S RTO6 User Manual*, chapters 24.8.6 "Waveform data"
and 24.10 "Waveform analysis": ``FORMat[:DATA]``, ``EXPort:WAVeform:INCXvalues``,
``CHANnel<m>[:WAVeform<n>]:DATA:HEADer?``, ``CHANnel<m>[:WAVeform<n>]:DATA[:VALues]?``,
``CALCulate:MATH<m>:DATA:HEADer?`` and ``CALCulate:MATH<m>:DATA[:VALues]?``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, cast

import numpy as np

from .....units import Quantity, quantity
from ....base import Menu
from . import _common as c
from ._common import WaveformHeader

if TYPE_CHECKING:
    from ._oscilloscope import Oscilloscope

__all__ = ["Waveform"]


class Waveform(Menu):
    """Transfer of waveform records from the instrument."""

    def __init__(self, parent: "Oscilloscope") -> None:
        super().__init__(parent)
        self._scope = parent

    def _prepare_transfer(self) -> None:
        self.write("FORM ASC")
        self.write("EXP:WAV:INCX OFF")

    # -- channels ------------------------------------------------------------
    def get_header(self, channel: int, waveform: int = 1) -> WaveformHeader:
        """The record's x start/stop, length and values per sample (``CHAN<m>:WAV<n>:DATA:HEAD?``)."""
        self._scope.check_channel(channel)
        return c.parse_header(self.query(f"CHAN{channel}:WAV{waveform}:DATA:HEAD?"))

    def get_data(self, channel: int, waveform: int = 1) -> tuple[Quantity, Quantity]:
        """Read a channel's record as ``(time, voltage)`` quantity arrays.

        For envelope / peak-detect waveforms (two values per sample interval)
        the voltage array has shape ``(record_length, 2)`` — minimum and
        maximum per interval — and the time axis one entry per interval.
        """
        self._scope.check_channel(channel)
        self._prepare_transfer()
        header = self.get_header(channel, waveform)
        values = c.parse_float_array(self.query(f"CHAN{channel}:WAV{waveform}:DATA?"))
        time, voltage = self._pack(header, values, "s", "V")
        return time, cast(Quantity, voltage)

    # -- math ------------------------------------------------------------------
    def get_math_header(self, math: int) -> WaveformHeader:
        """The header of math waveform `math` (``CALC:MATH<m>:DATA:HEAD?``)."""
        self._scope.check_math(math)
        return c.parse_header(self.query(f"CALC:MATH{math}:DATA:HEAD?"))

    def get_math_data(
        self, math: int, x_unit: str = "s", y_unit: Optional[str] = None
    ) -> tuple[Quantity, np.ndarray | Quantity]:
        """Read math waveform `math` as ``(x, y)`` (``CALC:MATH<m>:DATA?``).

        The x axis is a quantity in `x_unit` — seconds for a time-domain
        expression, hertz for an FFT. The y values carry the unit `y_unit` if
        given (``"V"``, ``"dBm"``); otherwise they are returned as a plain
        array, since a math expression's unit is whatever the expression makes it.
        """
        self._scope.check_math(math)
        self._prepare_transfer()
        header = self.get_math_header(math)
        values = c.parse_float_array(self.query(f"CALC:MATH{math}:DATA?"))
        return self._pack(header, values, x_unit, y_unit)

    # -- helpers ---------------------------------------------------------------
    @staticmethod
    def _pack(
        header: WaveformHeader, values: np.ndarray, x_unit: str, y_unit: Optional[str]
    ) -> tuple[Quantity, np.ndarray | Quantity]:
        per_sample = max(header.values_per_sample, 1)
        expected = header.record_length * per_sample
        if len(values) != expected:
            raise ValueError(
                f"Waveform transfer returned {len(values)} values but the header "
                f"announced {header.record_length} points × {per_sample}."
            )
        y = values.reshape(header.record_length, per_sample) if per_sample > 1 else values
        x = quantity(header.x_axis(), x_unit)
        return x, quantity(y, y_unit) if y_unit is not None else y
