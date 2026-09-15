"""Reference oscillator (``[:SOURce]:ROSCillator``).

The MXG locks to an external 10 MHz reference at the rear-panel ``REF IN``
connector and always outputs its own reference at ``10 MHz OUT``. The
*selection* between internal and external is automatic (the generator detects a
valid external signal) and can only be queried, not forced, over SCPI; what can
be set is whether that automatic switching is enabled.

Verified against the *MXG SCPI Command Reference* (N5180-90004), "Reference
Oscillator Subsystem ([:SOURce]:ROSCillator)".
"""

from __future__ import annotations

from ...base import Menu
from . import _common as c

__all__ = ["Reference"]


class Reference(Menu):
    """The 10 MHz reference oscillator: which source is in use, and auto-selection."""

    def get_source(self) -> str:
        """Return the reference in use (``ROSC:SOUR?``): ``INT`` or ``EXT``."""
        return c.parse_word(self.query("ROSC:SOUR?"))

    def is_external(self) -> bool:
        """Return ``True`` if the generator is locked to the external reference."""
        return self.get_source() == "EXT"

    def set_auto_select(self, enabled: bool) -> None:
        """Enable/disable automatic switching to an external reference (``ROSC:SOUR:AUTO``).

        With auto-select on, the generator uses ``REF IN`` whenever a valid
        signal is present and falls back to the internal reference otherwise;
        with it off, the internal reference is always used.
        """
        self.write(f"ROSC:SOUR:AUTO {c.onoff(enabled)}")

    def get_auto_select(self) -> bool:
        """Read whether automatic reference selection is on (``ROSC:SOUR:AUTO?``)."""
        return c.parse_bool(self.query("ROSC:SOUR:AUTO?"))
