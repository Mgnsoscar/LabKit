"""Channel management (``CONFigure:CHANnel`` subsystem).

A VNA groups its stimulus/receiver settings into *channels*; each channel drives
its own set of traces. These commands create, delete, name and enumerate
channels. Verified against the *R&S ZNL/ZNLE User Manual*,
``CONFigure:CHANnel...``.
"""

from __future__ import annotations

from ....base import Menu
from . import _common as c

__all__ = ["Channel"]


class Channel(Menu):
    """Create, delete, activate and list measurement channels."""

    def create(self, channel: int) -> None:
        """Create channel `channel` (and make it active) (``CONF:CHAN<Ch> ON``).

        The new channel copies the active channel's settings and starts with no
        traces; add one with
        :meth:`~labkit.instruments.drivers.rohde_schwarz.vna.trace.Trace.create`.
        """
        self.write(f"CONF:CHAN{channel} ON")

    def delete(self, channel: int) -> None:
        """Delete channel `channel` (``CONF:CHAN<Ch> OFF``)."""
        self.write(f"CONF:CHAN{channel} OFF")

    def exists(self, channel: int) -> bool:
        """Return ``True`` if channel `channel` exists (``CONF:CHAN<Ch>:STAT?``)."""
        return c.parse_bool(self.query(f"CONF:CHAN{channel}:STAT?"))

    def set_name(self, channel: int, name: str) -> None:
        """Set the name of channel `channel` (``CONF:CHAN<Ch>:NAME``)."""
        self.write(f"CONF:CHAN{channel}:NAME {c.quoted(name)}")

    def get_name(self, channel: int) -> str:
        """Read the name of channel `channel` (``CONF:CHAN<Ch>:NAME?``)."""
        return c.parse_name(self.query(f"CONF:CHAN{channel}:NAME?"))

    def catalog(self) -> list[tuple[str, str]]:
        """List channels as ``(number, name)`` pairs (``CONF:CHAN:CAT?``)."""
        return c.parse_catalog(self.query("CONF:CHAN:CAT?"))
