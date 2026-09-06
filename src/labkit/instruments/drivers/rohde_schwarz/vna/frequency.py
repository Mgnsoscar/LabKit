"""Stimulus frequency configuration (``[SENSe<Ch>:]FREQuency`` subsystem).

Start/stop and center/span are two views of the same sweep range; setting one
pair updates the other on the instrument. The CW (fixed) frequency applies to the
fixed-frequency sweep types (``CW``/``POINt``); see
:class:`~labkit.instruments.drivers.rohde_schwarz.vna.sweep.Sweep`.

Verified against the *R&S ZNL/ZNLE User Manual*, ``[SENSe<Ch>:]FREQuency:...``.
All values are sent in Hz.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .....units import Quantity
from ....base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._network_analyzer import NetworkAnalyzer

__all__ = ["Frequency"]


class Frequency(Menu):
    """The stimulus (sweep) frequency range of a channel."""

    def __init__(self, parent: "NetworkAnalyzer") -> None:
        super().__init__(parent)
        self._na = parent

    def _check(self, frequency: Quantity, label: str) -> None:
        low, high = self._na.frequency_range
        c.check_frequency_range(frequency, low, high, label)

    def set_start(self, frequency: Quantity, channel: int = 1) -> None:
        """Set the start frequency (``SENS<Ch>:FREQ:STAR``)."""
        self._check(frequency, "Start frequency")
        self.write(f"SENS{channel}:FREQ:STAR {c.hz(frequency)}")

    def get_start(self, channel: int = 1) -> Quantity:
        """Read the start frequency (``SENS<Ch>:FREQ:STAR?``)."""
        return c.as_frequency(self.query(f"SENS{channel}:FREQ:STAR?"))

    def set_stop(self, frequency: Quantity, channel: int = 1) -> None:
        """Set the stop frequency (``SENS<Ch>:FREQ:STOP``)."""
        self._check(frequency, "Stop frequency")
        self.write(f"SENS{channel}:FREQ:STOP {c.hz(frequency)}")

    def get_stop(self, channel: int = 1) -> Quantity:
        """Read the stop frequency (``SENS<Ch>:FREQ:STOP?``)."""
        return c.as_frequency(self.query(f"SENS{channel}:FREQ:STOP?"))

    def set_center(self, frequency: Quantity, channel: int = 1) -> None:
        """Set the center frequency (``SENS<Ch>:FREQ:CENT``)."""
        self._check(frequency, "Center frequency")
        self.write(f"SENS{channel}:FREQ:CENT {c.hz(frequency)}")

    def get_center(self, channel: int = 1) -> Quantity:
        """Read the center frequency (``SENS<Ch>:FREQ:CENT?``)."""
        return c.as_frequency(self.query(f"SENS{channel}:FREQ:CENT?"))

    def set_span(self, span: Quantity, channel: int = 1) -> None:
        """Set the frequency span (``SENS<Ch>:FREQ:SPAN``)."""
        self.write(f"SENS{channel}:FREQ:SPAN {c.hz(span)}")

    def get_span(self, channel: int = 1) -> Quantity:
        """Read the frequency span (``SENS<Ch>:FREQ:SPAN?``)."""
        return c.as_frequency(self.query(f"SENS{channel}:FREQ:SPAN?"))

    def set_cw(self, frequency: Quantity, channel: int = 1) -> None:
        """Set the fixed (CW) frequency for time/CW sweeps (``SENS<Ch>:FREQ:CW``)."""
        self._check(frequency, "CW frequency")
        self.write(f"SENS{channel}:FREQ:CW {c.hz(frequency)}")

    def get_cw(self, channel: int = 1) -> Quantity:
        """Read the fixed (CW) frequency (``SENS<Ch>:FREQ:CW?``)."""
        return c.as_frequency(self.query(f"SENS{channel}:FREQ:CW?"))
