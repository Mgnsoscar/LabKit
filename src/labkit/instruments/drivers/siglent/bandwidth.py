"""Resolution and video bandwidth (``[:SENSe]:BWIDth`` subsystem).

Verified against the *SHA850A User Manual* (EN01D) §3.2.1–§3.2.3.

The resolution bandwidths disagree between the documents: the manual's command
table lists 1 Hz … 10 MHz in a 1-3-10 sequence, the datasheet 1 Hz … 3 MHz
(with 1 Hz … 10 kHz available in FFT mode and 3 kHz … 3 MHz in swept mode).
:meth:`Bandwidth.set_rbw` accepts only what both documents promise, 1 Hz …
3 MHz. The instrument picks the nearest available RBW, rounding up, so read the
setting back with :meth:`Bandwidth.get_rbw` when an odd value matters. The video
bandwidths agree (1 Hz … 10 MHz, 1-3-10).
"""

from __future__ import annotations

from ....units import Quantity, ensure_frequency
from ...base import Menu
from . import _common as c

__all__ = ["Bandwidth"]

#: The discrete VBW/RBW ratios the instrument accepts (§3.2.3).
_RATIOS = (0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0)
_RBW_RANGE_HZ = (1.0, 3e6)
_VBW_RANGE_HZ = (1.0, 10e6)


class Bandwidth(Menu):
    """Resolution bandwidth (RBW) and video bandwidth (VBW)."""

    def set_rbw(self, bandwidth: Quantity) -> None:
        """Set the resolution bandwidth (``:BWID``), 1 Hz … 3 MHz.

        The analyzer rounds up to the next value of its 1-3-10 sequence (§3.2.1).
        An RBW of 10 kHz or less puts it into FFT mode.
        """
        value = ensure_frequency(bandwidth).to("Hz").magnitude
        c.check_range(value, *_RBW_RANGE_HZ, "RBW", "Hz")
        self.write(f":BWID {c.hz(bandwidth)}")

    def get_rbw(self) -> Quantity:
        return c.as_frequency(self.query(":BWID?"))

    def set_rbw_auto(self, enabled: bool) -> None:
        """Couple the RBW to the span (``:BWID:AUTO``)."""
        self.write(f":BWID:AUTO {c.onoff(enabled)}")

    def is_rbw_auto(self) -> bool:
        return c.parse_bool(self.query(":BWID:AUTO?"))

    def set_vbw(self, bandwidth: Quantity) -> None:
        """Set the video bandwidth (``:BWID:VID``), 1 Hz … 10 MHz."""
        value = ensure_frequency(bandwidth).to("Hz").magnitude
        c.check_range(value, *_VBW_RANGE_HZ, "VBW", "Hz")
        self.write(f":BWID:VID {c.hz(bandwidth)}")

    def get_vbw(self) -> Quantity:
        return c.as_frequency(self.query(":BWID:VID?"))

    def set_vbw_auto(self, enabled: bool) -> None:
        """Couple the VBW to the RBW (``:BWID:VID:AUTO``)."""
        self.write(f":BWID:VID:AUTO {c.onoff(enabled)}")

    def is_vbw_auto(self) -> bool:
        return c.parse_bool(self.query(":BWID:VID:AUTO?"))

    def set_vbw_rbw_ratio(self, ratio: float) -> None:
        """Set the VBW/RBW ratio used while the VBW is auto-coupled (``:BWID:VID:RAT``).

        Only the discrete values of §3.2.3 are accepted (1–3 suits CW signals,
        0.1 noise).
        """
        if float(ratio) not in _RATIOS:
            raise ValueError(f"VBW/RBW ratio must be one of {_RATIOS}, not {ratio!r}.")
        self.write(f":BWID:VID:RAT {c.scpi_number(ratio)}")
