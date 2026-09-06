"""Display and reference-oscillator control (``SYSTem``, ``[SENSe:]ROSCillator``)."""

from __future__ import annotations

from typing import Literal

from ....units import Quantity
from ...base import Menu
from . import _common as c

__all__ = ["Display", "ReferenceOscillator", "ReferenceSource"]

#: Reference-oscillator source.
ReferenceSource = Literal["INTERNAL", "EXTERNAL"]

_SOURCE_SCPI = {"INTERNAL": "INT", "EXTERNAL": "EXT"}


class Display(Menu):
    """Front-panel display behaviour during remote control."""

    def set_update(self, enabled: bool) -> None:
        """Update the display while remotely controlled (``SYST:DISP:UPD``).

        Off by default on the instrument (for speed); turning it on is useful
        while developing a measurement.
        """
        self.write(f"SYST:DISP:UPD {c.onoff(enabled)}")


class ReferenceOscillator(Menu):
    """Internal/external 10 MHz reference and its output."""

    def set_source(self, source: ReferenceSource) -> None:
        """Select the internal or external reference (``ROSC:SOUR``)."""
        self.write(f"ROSC:SOUR {_SOURCE_SCPI[source]}")

    def get_source(self) -> str:
        return self.query("ROSC:SOUR?").strip()

    def set_external_frequency(self, frequency: Quantity) -> None:
        """Tell the instrument the external reference frequency (``ROSC:EXT:FREQ``)."""
        self.write(f"ROSC:EXT:FREQ {c.hz(frequency)}")

    def get_external_frequency(self) -> Quantity:
        return c.as_frequency(self.query("ROSC:EXT:FREQ?"))

    def set_output(self, enabled: bool) -> None:
        """Switch the reference-output signal on/off (``ROSC:OUTP:STAT``)."""
        self.write(f"ROSC:OUTP:STAT {c.onoff(enabled)}")
