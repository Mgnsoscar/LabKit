"""Carrier-frequency control (``FREQ``).

The TGR6000 has a single carrier-frequency command, ``FREQ <nrf>``, taking a
value in **MHz**. There is no query form in the remote command set, so the
current frequency cannot be read back over the interface (see the module note in
:mod:`~labkit.instruments.drivers.aim_tti._signal_generator`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....units import Quantity, ensure_frequency
from ...base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._signal_generator import SignalGenerator

__all__ = ["Frequency"]


class Frequency(Menu):
    """The carrier (output) frequency of the generator."""

    def __init__(self, parent: "SignalGenerator") -> None:
        super().__init__(parent)
        self._gen = parent

    def set_frequency(self, frequency: Quantity) -> None:
        """Set the carrier frequency (``FREQ``, sent in MHz).

        Accepts any frequency quantity (``quantity(915, "MHz")``,
        ``quantity(2.45, "GHz")``); it is converted to MHz for the command.
        Raises :class:`~labkit.units.DimensionalityError` if `frequency` is not a
        frequency and :class:`ValueError` if it is outside the model's range.
        """
        ensure_frequency(frequency)
        low, high = self._gen.frequency_range
        c.check_range(frequency, low, high, "MHz", "Frequency")
        self.write(f"FREQ {c.megahertz(frequency)}")
