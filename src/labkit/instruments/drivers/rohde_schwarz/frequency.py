"""Frequency-axis configuration (``[SENSe:]FREQuency`` subsystem)."""

from __future__ import annotations

from ....units import Quantity
from ...base import Menu
from . import _common as c

__all__ = ["Frequency"]


class Frequency(Menu):
    """Center/span or start/stop frequency of the spectrum measurement.

    Center + span and start + stop are two views of the same setting; changing
    one updates the others on the instrument.
    """

    def set_center(self, frequency: Quantity) -> None:
        """Set the center frequency (``FREQ:CENT``)."""
        self.write(f"FREQ:CENT {c.hz(frequency)}")

    def get_center(self) -> Quantity:
        return c.as_frequency(self.query("FREQ:CENT?"))

    def set_span(self, span: Quantity) -> None:
        """Set the frequency span (``FREQ:SPAN``)."""
        self.write(f"FREQ:SPAN {c.hz(span)}")

    def get_span(self) -> Quantity:
        return c.as_frequency(self.query("FREQ:SPAN?"))

    def set_start(self, frequency: Quantity) -> None:
        """Set the start frequency (``FREQ:STAR``)."""
        self.write(f"FREQ:STAR {c.hz(frequency)}")

    def get_start(self) -> Quantity:
        return c.as_frequency(self.query("FREQ:STAR?"))

    def set_stop(self, frequency: Quantity) -> None:
        """Set the stop frequency (``FREQ:STOP``)."""
        self.write(f"FREQ:STOP {c.hz(frequency)}")

    def get_stop(self) -> Quantity:
        return c.as_frequency(self.query("FREQ:STOP?"))

    def set_full_span(self) -> None:
        """Span the instrument's full frequency range (``FREQ:SPAN:FULL``)."""
        self.write("FREQ:SPAN:FULL")

    def set_zero_span(self) -> None:
        """Switch to zero span (time-domain at the center frequency)."""
        self.write("FREQ:SPAN 0")

    def set_center_step(self, step: Quantity) -> None:
        """Set the center-frequency step size (``FREQ:CENT:STEP``)."""
        self.write(f"FREQ:CENT:STEP {c.hz(step)}")

    def set_center_step_auto(self, enabled: bool) -> None:
        """Couple the center-frequency step to the span (``FREQ:CENT:STEP:AUTO``)."""
        self.write(f"FREQ:CENT:STEP:AUTO {c.onoff(enabled)}")

    def set_offset(self, offset: Quantity) -> None:
        """Set a frequency offset added to displayed frequencies (``FREQ:OFFS``)."""
        self.write(f"FREQ:OFFS {c.hz(offset)}")

    def get_offset(self) -> Quantity:
        return c.as_frequency(self.query("FREQ:OFFS?"))
