"""Sweep configuration and trigger source.

Covers the number of points, sweep type, sweep time (and its auto-coupling),
single-sweep count, per-point dwell, continuous/single mode, and the trigger
source. Run control (``INITiate``) lives on the driver itself
(:meth:`~labkit.instruments.drivers.rohde_schwarz.vna._network_analyzer.NetworkAnalyzer.trigger`).

Verified against the *R&S ZNL/ZNLE User Manual*: ``[SENSe<Ch>:]SWEep:...``,
``INITiate<Ch>:CONTinuous`` and ``TRIGger<Ch>[:SEQuence]:SOURce``.
"""

from __future__ import annotations

from typing import Literal

from .....units import Quantity
from ....base import Menu
from . import _common as c

__all__ = ["Sweep", "SweepType", "TriggerSource"]

#: Sweep variable and point spacing.
SweepType = Literal["LINEAR", "LOGARITHMIC", "CW", "POINT", "SEGMENT"]
#: Source of the trigger events that start a measurement.
TriggerSource = Literal["IMMEDIATE", "EXTERNAL", "MANUAL", "MULTIPLE"]

_SWEEP_TYPE_SCPI = {
    "LINEAR": "LIN", "LOGARITHMIC": "LOG", "CW": "CW",
    "POINT": "POIN", "SEGMENT": "SEGM",
}
_TRIGGER_SOURCE_SCPI = {
    "IMMEDIATE": "IMM", "EXTERNAL": "EXT", "MANUAL": "MAN", "MULTIPLE": "MULT",
}


class Sweep(Menu):
    """Sweep points, type, timing, averaging count, run mode and trigger source."""

    def set_points(self, points: int, channel: int = 1) -> None:
        """Set the number of measurement points per sweep (``SENS<Ch>:SWE:POIN``).

        The R&S ZNLE allows 1 to 5001 points for frequency sweeps.
        """
        self.write(f"SENS{channel}:SWE:POIN {int(points)}")

    def get_points(self, channel: int = 1) -> int:
        """Read the number of points per sweep (``SENS<Ch>:SWE:POIN?``)."""
        return c.parse_int(self.query(f"SENS{channel}:SWE:POIN?"))

    def set_type(self, sweep_type: SweepType, channel: int = 1) -> None:
        """Select the sweep type (``SENS<Ch>:SWE:TYPE``)."""
        self.write(f"SENS{channel}:SWE:TYPE {_SWEEP_TYPE_SCPI[sweep_type]}")

    def get_type(self, channel: int = 1) -> str:
        """Read the sweep type (``SENS<Ch>:SWE:TYPE?``)."""
        return self.query(f"SENS{channel}:SWE:TYPE?").strip()

    def set_time(self, time: Quantity, channel: int = 1) -> None:
        """Set the sweep time (``SENS<Ch>:SWE:TIME``). Disables sweep-time auto."""
        self.write(f"SENS{channel}:SWE:TIME {c.seconds(time)}")

    def get_time(self, channel: int = 1) -> Quantity:
        """Read the sweep time (``SENS<Ch>:SWE:TIME?``)."""
        return c.as_seconds(self.query(f"SENS{channel}:SWE:TIME?"))

    def set_time_auto(self, enabled: bool, channel: int = 1) -> None:
        """Couple the sweep time to the other channel settings (``SENS<Ch>:SWE:TIME:AUTO``)."""
        self.write(f"SENS{channel}:SWE:TIME:AUTO {c.onoff(enabled)}")

    def set_count(self, count: int, channel: int = 1) -> None:
        """Set the number of sweeps buffered in single-sweep mode (``SENS<Ch>:SWE:COUN``)."""
        self.write(f"SENS{channel}:SWE:COUN {int(count)}")

    def get_count(self, channel: int = 1) -> int:
        """Read the single-sweep count (``SENS<Ch>:SWE:COUN?``)."""
        return c.parse_int(self.query(f"SENS{channel}:SWE:COUN?"))

    def set_dwell(self, dwell: Quantity, channel: int = 1) -> None:
        """Set the per-point measurement delay/dwell (``SENS<Ch>:SWE:DWEL``)."""
        self.write(f"SENS{channel}:SWE:DWEL {c.seconds(dwell)}")

    def set_continuous(self, enabled: bool, channel: int = 1) -> None:
        """Continuous (``True``) vs single (``False``) sweeping (``INIT<Ch>:CONT``)."""
        self.write(f"INIT{channel}:CONT {c.onoff(enabled)}")

    def is_continuous(self, channel: int = 1) -> bool:
        """Return ``True`` if sweeping continuously (``INIT<Ch>:CONT?``)."""
        return c.parse_bool(self.query(f"INIT{channel}:CONT?"))

    def set_trigger_source(self, source: TriggerSource, channel: int = 1) -> None:
        """Set the trigger source (``TRIG<Ch>:SEQ:SOUR``)."""
        self.write(f"TRIG{channel}:SEQ:SOUR {_TRIGGER_SOURCE_SCPI[source]}")

    def get_trigger_source(self, channel: int = 1) -> str:
        """Read the trigger source (``TRIG<Ch>:SEQ:SOUR?``)."""
        return self.query(f"TRIG{channel}:SEQ:SOUR?").strip()
