"""Sweep averaging (``[SENSe<Ch>:]AVERage`` subsystem).

Sweep averaging reduces noise by combining each measurement point over several
consecutive sweeps. It is channel-specific and independent of the single-sweep
count (:meth:`~labkit.instruments.drivers.rohde_schwarz.vna.sweep.Sweep.set_count`).
Verified against the *R&S ZNL/ZNLE User Manual*, ``[SENSe<Ch>:]AVERage...``.
"""

from __future__ import annotations

from typing import Literal

from ....base import Menu
from . import _common as c

__all__ = ["Average", "AverageMode"]

#: Averaging algorithm.
AverageMode = Literal["AUTO", "FLATTEN", "REDUCE", "MOVING"]

_AVERAGE_MODE_SCPI = {
    "AUTO": "AUTO", "FLATTEN": "FLAT", "REDUCE": "RED", "MOVING": "MOV",
}


class Average(Menu):
    """Enable, size, clear and configure the sweep average."""

    def set_state(self, enabled: bool, channel: int = 1) -> None:
        """Enable or disable the sweep average (``SENS<Ch>:AVER``)."""
        self.write(f"SENS{channel}:AVER {c.onoff(enabled)}")

    def get_state(self, channel: int = 1) -> bool:
        """Return ``True`` if averaging is enabled (``SENS<Ch>:AVER?``)."""
        return c.parse_bool(self.query(f"SENS{channel}:AVER?"))

    def set_count(self, count: int, channel: int = 1) -> None:
        """Set the averaging factor, 1–1000 (``SENS<Ch>:AVER:COUN``)."""
        self.write(f"SENS{channel}:AVER:COUN {int(count)}")

    def get_count(self, channel: int = 1) -> int:
        """Read the averaging factor (``SENS<Ch>:AVER:COUN?``)."""
        return c.parse_int(self.query(f"SENS{channel}:AVER:COUN?"))

    def clear(self, channel: int = 1) -> None:
        """Restart the average, clearing previous results (``SENS<Ch>:AVER:CLE``)."""
        self.write(f"SENS{channel}:AVER:CLE")

    def set_mode(self, mode: AverageMode, channel: int = 1) -> None:
        """Set the averaging algorithm (``SENS<Ch>:AVER:MODE``)."""
        self.write(f"SENS{channel}:AVER:MODE {_AVERAGE_MODE_SCPI[mode]}")
