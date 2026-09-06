"""System-error correction and calibration-pool management.

Covers the *use* of calibration: switching system-error correction on/off for a
channel, querying the calibration's state and date, and loading/saving correction
data sets ("cal groups") from the instrument's calibration pool.

The interactive *guided calibration* sequence (``[SENSe:]CORRection:COLLect...``:
selecting a method, measuring each standard, computing the error terms) is
intentionally **not** wrapped here — it is a stateful, standard-by-standard
procedure best driven explicitly against the manual for the cal kit in use. This
menu manages correction data that already exists. Verified against the *R&S
ZNL/ZNLE User Manual*: ``[SENSe<Ch>:]CORRection...`` and
``MMEMory:LOAD|STORe:CORRection``.
"""

from __future__ import annotations

from ....base import Menu
from . import _common as c

__all__ = ["Calibration"]


class Calibration(Menu):
    """Enable/disable system-error correction and manage cal-pool files."""

    def set_correction_enabled(self, enabled: bool, channel: int = 1) -> None:
        """Enable/disable system-error correction for a channel (``SENS<Ch>:CORR:STAT``)."""
        self.write(f"SENS{channel}:CORR:STAT {c.onoff(enabled)}")

    def is_correction_enabled(self, channel: int = 1) -> bool:
        """Return ``True`` if correction is active (``SENS<Ch>:CORR:STAT?``)."""
        return c.parse_bool(self.query(f"SENS{channel}:CORR:STAT?"))

    def get_correction_date(self, channel: int = 1) -> str:
        """Return the date/time of the active calibration (``SENS<Ch>:CORR:DATE?``)."""
        return c.parse_name(self.query(f"SENS{channel}:CORR:DATE?"))

    def get_system_correction_state(self, channel: int = 1) -> str:
        """Return the system-correction state string (``SENS<Chn>:CORR:SST?``)."""
        return c.parse_name(self.query(f"SENS{channel}:CORR:SST?"))

    def load(self, channel: int, cal_group_file: str) -> None:
        """Apply a stored cal group to a channel (``MMEM:LOAD:CORR <Ch>,'<file>'``).

        `cal_group_file` is a ``*.cal`` file name in the instrument's cal pool
        (no directory path).
        """
        self.write(f"MMEM:LOAD:CORR {channel},{c.quoted(cal_group_file)}")

    def save(self, channel: int, cal_group_file: str) -> None:
        """Copy a channel's correction data to a cal group (``MMEM:STOR:CORR <Ch>,'<file>'``)."""
        self.write(f"MMEM:STOR:CORR {channel},{c.quoted(cal_group_file)}")
