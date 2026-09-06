"""Resolution and video bandwidth (``[SENSe:]BANDwidth`` subsystem)."""

from __future__ import annotations

from typing import Literal

from ....units import Quantity
from ...base import Menu
from . import _common as c

__all__ = ["Bandwidth", "FilterType"]

#: Resolution-filter shapes offered by the FSV3000.
FilterType = Literal["NORMAL", "CHANNEL", "RRC", "PULSE", "P5"]

_FILTER_SCPI = {
    "NORMAL": "NORM",   # 3 dB Gaussian
    "CHANNEL": "CFIL",  # channel filter
    "RRC": "RRC",       # root-raised-cosine
    "PULSE": "PULS",    # 6 dB pulse bandwidth
    "P5": "P5",         # 5-pole filter
}


class Bandwidth(Menu):
    """Resolution bandwidth (RBW) and video bandwidth (VBW)."""

    def set_rbw(self, bandwidth: Quantity) -> None:
        """Set the resolution bandwidth (``BAND``). Disables RBW auto-coupling."""
        self.write(f"BAND {c.hz(bandwidth)}")

    def get_rbw(self) -> Quantity:
        return c.as_frequency(self.query("BAND?"))

    def set_rbw_auto(self, enabled: bool) -> None:
        """Couple the RBW to the span (``BAND:AUTO``)."""
        self.write(f"BAND:AUTO {c.onoff(enabled)}")

    def set_vbw(self, bandwidth: Quantity) -> None:
        """Set the video bandwidth (``BAND:VID``). Disables VBW auto-coupling."""
        self.write(f"BAND:VID {c.hz(bandwidth)}")

    def get_vbw(self) -> Quantity:
        return c.as_frequency(self.query("BAND:VID?"))

    def set_vbw_auto(self, enabled: bool) -> None:
        """Couple the VBW to the RBW (``BAND:VID:AUTO``)."""
        self.write(f"BAND:VID:AUTO {c.onoff(enabled)}")

    def set_vbw_rbw_ratio(self, ratio: float) -> None:
        """Set the VBW/RBW ratio used when VBW is auto-coupled (``BAND:VID:RAT``)."""
        self.write(f"BAND:VID:RAT {c.scpi_number(ratio)}")

    def set_span_rbw_ratio(self, ratio: float) -> None:
        """Set the span/RBW ratio used when RBW is auto-coupled (``BAND:RAT``)."""
        self.write(f"BAND:RAT {c.scpi_number(ratio)}")

    def set_filter_type(self, filter_type: FilterType) -> None:
        """Select the resolution-filter shape (``BAND:TYPE``)."""
        self.write(f"BAND:TYPE {_FILTER_SCPI[filter_type]}")
