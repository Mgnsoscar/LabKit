"""RF output level and on/off control.

Groups the TGR6000 "Output Parameters" commands that are not the carrier
frequency: the output level (in its several unit forms) and the RF-output
enable. Levels have no query form in the remote command set, so the current
level cannot be read back over the interface.

Verified against the TGR6000 Instruction Manual (Iss 9), "Command List" →
"Output Parameters":

- ``DBMLEV <nrf>``  — level in dBm (the primary, quantity-checked path)
- ``UVLEV <nrf>``   — level in microvolts
- ``MVLEV <nrf>``   — level in millivolts
- ``DBUVLEV <nrf>`` — level in dBµV
- ``RFON`` / ``RFOFF`` — RF output on / off
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....units import Quantity, ensure_power
from ...base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._signal_generator import SignalGenerator

__all__ = ["Output"]


class Output(Menu):
    """The RF output: its level and its on/off state."""

    def __init__(self, parent: "SignalGenerator") -> None:
        super().__init__(parent)
        self._gen = parent

    # -- level -------------------------------------------------------------
    def set_level(self, level: Quantity) -> None:
        """Set the output level (``DBMLEV``, sent in dBm).

        Accepts any power quantity (``quantity(-10, "dBm")``,
        ``quantity(1, "mW")``); it is converted to dBm for the command. Raises
        :class:`~labkit.units.DimensionalityError` if `level` is not a power and
        :class:`ValueError` if it is outside the model's level range.
        """
        ensure_power(level)
        low, high = self._gen.level_range
        c.check_range(level, low, high, "dBm", "Level")
        self.write(f"DBMLEV {c.dbm(level)}")

    def set_level_microvolts(self, level: Quantity) -> None:
        """Set the output level in microvolts (``UVLEV``), from a voltage quantity."""
        self.write(f"UVLEV {c.microvolts(level)}")

    def set_level_millivolts(self, level: Quantity) -> None:
        """Set the output level in millivolts (``MVLEV``), from a voltage quantity."""
        self.write(f"MVLEV {c.millivolts(level)}")

    def set_level_dbuv(self, level_dbuv: float) -> None:
        """Set the output level in dBµV (``DBUVLEV``).

        Takes a plain number: dBµV is a voltage-referenced logarithmic unit that
        :mod:`labkit.units` does not model, so there is no quantity form here.
        """
        self.write(f"DBUVLEV {c.scpi_number(level_dbuv)}")

    # -- enable ------------------------------------------------------------
    def set_rf_enabled(self, enabled: bool) -> None:
        """Switch the RF output on (``RFON``) or off (``RFOFF``)."""
        self.write("RFON" if enabled else "RFOFF")

    def on(self) -> None:
        """Switch the RF output on (``RFON``)."""
        self.write("RFON")

    def off(self) -> None:
        """Switch the RF output off (``RFOFF``)."""
        self.write("RFOFF")
