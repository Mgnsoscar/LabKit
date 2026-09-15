"""Carrier-frequency control (``[:SOURce]:FREQuency`` subsystem).

Covers the CW frequency and its mode, the frequency offset/multiplier
applied to the *displayed* frequency, the frequency reference, and the carrier
phase adjustment. Sweep-related frequency commands (start/stop/center/span)
live in the :mod:`~labkit.instruments.drivers.keysight.sweep` menu.

Verified against the *MXG SCPI Command Reference* (N5180-90004), "Frequency
Subsystem ([:SOURce])".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ....units import Quantity, ensure_frequency
from ...base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._signal_generator import AnalogSignalGenerator

__all__ = ["Frequency", "FrequencyMode"]

#: ``CW``/``FIXed`` operate at a set frequency; ``LIST`` enables the frequency sweep.
FrequencyMode = Literal["CW", "FIXED", "LIST"]

_MODE_SCPI = {"CW": "CW", "FIXED": "FIX", "LIST": "LIST"}


class Frequency(Menu):
    """The carrier (output) frequency of the generator."""

    def __init__(self, parent: "AnalogSignalGenerator") -> None:
        super().__init__(parent)
        self._gen = parent

    # -- CW frequency ------------------------------------------------------
    def set_frequency(self, frequency: Quantity) -> None:
        """Set the CW output frequency (``FREQ:CW``, sent in Hz).

        Accepts any frequency quantity (``quantity(915, "MHz")``,
        ``quantity(2.45, "GHz")``). Raises :class:`~labkit.units.DimensionalityError`
        if `frequency` is not a frequency and :class:`ValueError` if it is
        outside the model's range.
        """
        ensure_frequency(frequency)
        low, high = self._gen.frequency_range
        c.check_range(frequency, low, high, "Hz", "Frequency")
        self.write(f"FREQ:CW {c.hz(frequency)}")

    def get_frequency(self) -> Quantity:
        """Read the CW output frequency (``FREQ:CW?``) as a frequency quantity."""
        return c.as_frequency(self.query("FREQ:CW?"))

    def set_mode(self, mode: FrequencyMode) -> None:
        """Set the frequency mode (``FREQ:MODE``): ``CW``/``FIXED`` or ``LIST`` (swept)."""
        self.write(f"FREQ:MODE {_MODE_SCPI[mode]}")

    def get_mode(self) -> str:
        """Read the frequency mode (``FREQ:MODE?``), e.g. ``CW`` or ``LIST``."""
        return c.parse_word(self.query("FREQ:MODE?"))

    # -- offset / multiplier (display only; the RF output is unchanged) ------
    def set_offset(self, offset: Quantity, enabled: bool = True) -> None:
        """Set the displayed-frequency offset (``FREQ:OFFS``) and its state.

        The offset is added to the displayed frequency to account for, e.g., a
        downstream mixer; it does not change the RF output frequency.
        """
        self.write(f"FREQ:OFFS {c.hz(offset)}")
        self.write(f"FREQ:OFFS:STAT {c.onoff(enabled)}")

    def get_offset(self) -> Quantity:
        """Read the displayed-frequency offset (``FREQ:OFFS?``)."""
        return c.as_frequency(self.query("FREQ:OFFS?"))

    def set_multiplier(self, multiplier: int) -> None:
        """Set the displayed-frequency multiplier (``FREQ:MULT``), e.g. for a doubler."""
        self.write(f"FREQ:MULT {int(multiplier)}")

    def get_multiplier(self) -> int:
        """Read the displayed-frequency multiplier (``FREQ:MULT?``)."""
        return c.parse_int(self.query("FREQ:MULT?"))

    # -- frequency reference -----------------------------------------------
    def set_reference(self, frequency: Quantity, enabled: bool = True) -> None:
        """Set the frequency reference (``FREQ:REF``) and switch it on/off.

        With the reference on, the displayed frequency is *relative* to it.
        """
        self.write(f"FREQ:REF {c.hz(frequency)}")
        self.write(f"FREQ:REF:STAT {c.onoff(enabled)}")

    def set_reference_to_current(self) -> None:
        """Use the current frequency as the reference (``FREQ:REF:SET``)."""
        self.write("FREQ:REF:SET")

    def set_reference_enabled(self, enabled: bool) -> None:
        """Switch the frequency reference on/off (``FREQ:REF:STAT``)."""
        self.write(f"FREQ:REF:STAT {c.onoff(enabled)}")

    # -- carrier phase -----------------------------------------------------
    def set_phase_adjust(self, phase: Quantity) -> None:
        """Adjust the carrier phase relative to the reference (``PHAS``, in radians)."""
        self.write(f"PHAS {c.radians(phase)}")

    def get_phase_adjust(self) -> Quantity:
        """Read the carrier phase adjustment (``PHAS?``) as an angle quantity."""
        return c.as_radians(self.query("PHAS?"))

    def set_phase_reference(self) -> None:
        """Make the current phase the zero reference (``PHAS:REF``)."""
        self.write("PHAS:REF")
