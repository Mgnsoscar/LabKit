"""Internal source power and RF output (``SOURce<Ch>:POWer``, ``OUTPut<Ch>``).

Sets the channel base power that drives the DUT, the start/stop levels of a power
sweep, and the master RF-output switch. The usable power range is
frequency-dependent (see the R&S ZNLE data sheet), so the level is passed through
as given rather than range-checked here. Verified against the *R&S ZNL/ZNLE User
Manual*: ``SOURce<Ch>:POWer...`` and ``OUTPut<Ch>[:STATe]``.
"""

from __future__ import annotations

from .....units import Quantity
from ....base import Menu
from . import _common as c

__all__ = ["Power"]


class Power(Menu):
    """Source power level, power-sweep range, and RF output on/off."""

    def set_power(self, level: Quantity, channel: int = 1) -> None:
        """Set the internal source (base) power in dBm (``SOUR<Ch>:POW``)."""
        self.write(f"SOUR{channel}:POW {c.dbm(level)}")

    def get_power(self, channel: int = 1) -> Quantity:
        """Read the internal source power (``SOUR<Ch>:POW?``)."""
        return c.as_power(self.query(f"SOUR{channel}:POW?"))

    def set_power_start(self, level: Quantity, channel: int = 1) -> None:
        """Set the start level of a power sweep (``SOUR<Ch>:POW:STAR``)."""
        self.write(f"SOUR{channel}:POW:STAR {c.dbm(level)}")

    def set_power_stop(self, level: Quantity, channel: int = 1) -> None:
        """Set the stop level of a power sweep (``SOUR<Ch>:POW:STOP``)."""
        self.write(f"SOUR{channel}:POW:STOP {c.dbm(level)}")

    def set_output(self, enabled: bool) -> None:
        """Switch the internal RF source power at all ports on/off (``OUTP``)."""
        self.write(f"OUTP {c.onoff(enabled)}")

    def get_output(self) -> bool:
        """Return ``True`` if the RF source output is on (``OUTP?``)."""
        return c.parse_bool(self.query("OUTP?"))
