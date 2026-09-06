"""Measurement (IF) bandwidth (``[SENSe<Ch>:]BANDwidth[:RESolution]``).

The IF bandwidth sets the width of the receiver filter: narrower bandwidths lower
the noise floor at the cost of sweep speed. The R&S ZNL/ZNLE accepts 1 Hz to
500 kHz in 1-1.5-2-3-5-7 steps (the instrument rounds an intermediate value up to
the next step). Verified against the *R&S ZNL/ZNLE User Manual*,
``[SENSe<Ch>:]BANDwidth[:RESolution]``.
"""

from __future__ import annotations

from .....units import Quantity
from ....base import Menu
from . import _common as c

__all__ = ["Bandwidth"]


class Bandwidth(Menu):
    """The receiver IF (measurement) bandwidth."""

    def set_if_bandwidth(self, bandwidth: Quantity, channel: int = 1) -> None:
        """Set the IF bandwidth (``SENS<Ch>:BAND:RES``), 1 Hz – 500 kHz."""
        self.write(f"SENS{channel}:BAND:RES {c.hz(bandwidth)}")

    def get_if_bandwidth(self, channel: int = 1) -> Quantity:
        """Read the IF bandwidth (``SENS<Ch>:BAND:RES?``).

        Returns the value the instrument rounded to, which may differ from the
        requested one because of the 1-1.5-2-3-5-7 step grid.
        """
        return c.as_frequency(self.query(f"SENS{channel}:BAND:RES?"))
