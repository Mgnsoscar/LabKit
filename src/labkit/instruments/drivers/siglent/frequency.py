"""Frequency-axis configuration (``[:SENSe]:FREQuency`` subsystem).

Verified against the *SHA850A User Manual* (EN01D) §3.1.1 "Frequency & Span".
The manual gives the span range as "0 Hz, 100 Hz ~ 28GHz", a copy error from a
larger model; the setters here check every frequency against the model's
:attr:`~labkit.instruments.drivers.siglent._spectrum_analyzer.SHA850A.max_frequency`
instead, which also catches a value given in the wrong unit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....units import Quantity, ensure_frequency
from ...base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._spectrum_analyzer import SHA850A

__all__ = ["Frequency"]

#: Smallest non-zero span (§3.1.1).
_MIN_SPAN_HZ = 100.0


class Frequency(Menu):
    """Center/span or start/stop frequency of the spectrum measurement.

    Center + span and start + stop are two views of the same setting; changing
    one updates the others on the instrument (§3.1.1). Every change restarts the
    sweep. The range check assumes no frequency offset (:meth:`set_offset`
    shifts the displayed, and so the settable, frequencies).
    """

    def __init__(self, parent: "SHA850A") -> None:
        super().__init__(parent)
        self._analyzer = parent

    def _check(self, frequency: Quantity, label: str) -> float:
        value = ensure_frequency(frequency).to("Hz").magnitude
        top = self._analyzer.max_frequency.to("Hz").magnitude
        c.check_range(value, 0.0, top, label, "Hz")
        return float(value)

    def set_center(self, frequency: Quantity) -> None:
        """Set the center frequency (``:FREQ:CENT``)."""
        self._check(frequency, "Center frequency")
        self.write(f":FREQ:CENT {c.hz(frequency)}")

    def get_center(self) -> Quantity:
        return c.as_frequency(self.query(":FREQ:CENT?"))

    def set_span(self, span: Quantity) -> None:
        """Set the frequency span (``:FREQ:SPAN``); ``0 Hz`` selects zero span.

        A non-zero span must be at least 100 Hz (§3.1.1). Inside the channel-power
        measurement the analyzer uses its own span setting instead (see
        :meth:`~labkit.instruments.drivers.siglent.measurement.Measurement.channel_power`).
        """
        value = self._check(span, "Span")
        if 0.0 < value < _MIN_SPAN_HZ:
            raise ValueError(f"Span {span} is below the {_MIN_SPAN_HZ:g} Hz minimum (0 Hz = zero span).")
        self.write(f":FREQ:SPAN {c.hz(span)}")

    def get_span(self) -> Quantity:
        return c.as_frequency(self.query(":FREQ:SPAN?"))

    def set_start(self, frequency: Quantity) -> None:
        """Set the start frequency (``:FREQ:STAR``)."""
        self._check(frequency, "Start frequency")
        self.write(f":FREQ:STAR {c.hz(frequency)}")

    def get_start(self) -> Quantity:
        return c.as_frequency(self.query(":FREQ:STAR?"))

    def set_stop(self, frequency: Quantity) -> None:
        """Set the stop frequency (``:FREQ:STOP``)."""
        self._check(frequency, "Stop frequency")
        self.write(f":FREQ:STOP {c.hz(frequency)}")

    def get_stop(self) -> Quantity:
        return c.as_frequency(self.query(":FREQ:STOP?"))

    def set_full_span(self) -> None:
        """Span the instrument's full frequency range (``:FREQ:SPAN:FULL``)."""
        self.write(":FREQ:SPAN:FULL")

    def set_zero_span(self) -> None:
        """Switch to zero span, time domain at the center frequency (``:FREQ:SPAN:ZERO``)."""
        self.write(":FREQ:SPAN:ZERO")

    def set_offset(self, offset: Quantity) -> None:
        """Set a frequency offset added to displayed frequencies (``:FREQ:OFFS``, §3.1.3)."""
        self.write(f":FREQ:OFFS {c.hz(offset)}")

    def get_offset(self) -> Quantity:
        return c.as_frequency(self.query(":FREQ:OFFS?"))
