"""Analog modulation: AM, FM, ΦM and pulse.

The MXG analog generators carry AM/FM/ΦM with Option UNT and pulse modulation
with Option UNU (or UNW, narrow pulse). Each modulation has its own sub-menu
with the same shape — a source (internal generator or the rear-panel external
input), the internal generator's rate and waveform, the modulation depth or
deviation, and an on/off state:

    gen.modulation.am.set_depth(30.0)
    gen.modulation.am.set_rate(quantity(1, "kHz"))
    gen.modulation.am.enable(True)
    gen.power.set_modulation_enabled(True)   # the global Mod On/Off key

Remember that no modulation reaches the RF output until the *global*
modulation switch is on (:meth:`~labkit.instruments.drivers.keysight.power.Power.set_modulation_enabled`).

Verified against the *MXG SCPI Command Reference* (N5180-90004), "Analog
Modulation Commands": the AM, FM and PM subsystems (Option UNT) and the Pulse
Modulation subsystem (Options UNU/UNW).
"""

from __future__ import annotations

from typing import Literal

from ....units import Quantity
from ...base import BaseInstrument, Menu
from . import _common as c

__all__ = [
    "Modulation",
    "AmplitudeModulation",
    "FrequencyModulation",
    "PhaseModulation",
    "PulseModulation",
    "ModulationSource",
    "AmMode",
    "AmType",
    "PmBandwidth",
    "PulseSource",
    "PulsePolarity",
]

#: Internal function generator or the rear-panel external modulation input.
ModulationSource = Literal["INTERNAL", "EXTERNAL"]
#: ``DEEP`` gives greater AM depth dynamic range; ``NORMAL`` is standard operation.
AmMode = Literal["DEEP", "NORMAL"]
#: Linear (percent) or exponential (dB) AM depth.
AmType = Literal["LINEAR", "EXPONENTIAL"]
#: ΦM modulation bandwidth mode.
PmBandwidth = Literal["NORMAL", "HIGH"]
#: Internal pulse-generator mode (``EXTERNAL`` selects the rear-panel PULSE input).
PulseSource = Literal[
    "SQUARE", "FREE_RUN", "TRIGGERED", "ADOUBLET", "DOUBLET", "GATED", "TRAIN", "EXTERNAL",
]
#: Polarity of the external pulse input.
PulsePolarity = Literal["NORMAL", "INVERTED"]

_SOURCE_SCPI = {"INTERNAL": "INT", "EXTERNAL": "EXT"}
_AM_MODE_SCPI = {"DEEP": "DEEP", "NORMAL": "NORM"}
_AM_TYPE_SCPI = {"LINEAR": "LIN", "EXPONENTIAL": "EXP"}
_PM_BW_SCPI = {"NORMAL": "NORM", "HIGH": "HIGH"}
_PULSE_INTERNAL_SCPI = {
    "SQUARE": "SQU", "FREE_RUN": "FRUN", "TRIGGERED": "TRIG", "ADOUBLET": "ADO",
    "DOUBLET": "DOUB", "GATED": "GATE", "TRAIN": "PTR",
}
_POLARITY_SCPI = {"NORMAL": "NORM", "INVERTED": "INV"}


class _AnalogModulation(Menu):
    """Common shape of the AM/FM/ΦM sub-menus (``<prefix>`` is ``AM``, ``FM`` or ``PM``)."""

    _prefix: str

    def enable(self, enabled: bool = True) -> None:
        """Switch this modulation on/off (``<prefix>:STAT``)."""
        self.write(f"{self._prefix}:STAT {c.onoff(enabled)}")

    def get_enabled(self) -> bool:
        """Read whether this modulation is on (``<prefix>:STAT?``)."""
        return c.parse_bool(self.query(f"{self._prefix}:STAT?"))

    def set_source(self, source: ModulationSource) -> None:
        """Select the internal generator or the external input (``<prefix>:SOUR``)."""
        self.write(f"{self._prefix}:SOUR {_SOURCE_SCPI[source]}")

    def set_rate(self, rate: Quantity) -> None:
        """Set the internal modulation rate (``<prefix>:INT:FREQ``, in Hz)."""
        self.write(f"{self._prefix}:INT:FREQ {c.hz(rate)}")

    def get_rate(self) -> Quantity:
        """Read the internal modulation rate (``<prefix>:INT:FREQ?``)."""
        return c.as_frequency(self.query(f"{self._prefix}:INT:FREQ?"))

    def set_external_coupling(self, coupling: Literal["AC", "DC"]) -> None:
        """Set the external input coupling (``<prefix>:EXT:COUP``)."""
        self.write(f"{self._prefix}:EXT:COUP {coupling}")


class AmplitudeModulation(_AnalogModulation):
    """Amplitude modulation (Option UNT)."""

    _prefix = "AM"

    def set_depth(self, depth_percent: float) -> None:
        """Set the linear AM depth in percent, 0–90 (``AM:DEPT``)."""
        self.write(f"AM:DEPT {c.percent(depth_percent)}")

    def get_depth(self) -> float:
        """Read the linear AM depth in percent (``AM:DEPT?``)."""
        return c.parse_float(self.query("AM:DEPT?"))

    def set_depth_exponential(self, depth_db: float) -> None:
        """Set the exponential AM depth in dB (``AM:DEPT:EXP``)."""
        self.write(f"AM:DEPT:EXP {c.scpi_number(depth_db)}")

    def set_type(self, am_type: AmType) -> None:
        """Select linear (%/V) or exponential (dB/V) AM (``AM:TYPE``)."""
        self.write(f"AM:TYPE {_AM_TYPE_SCPI[am_type]}")

    def set_mode(self, mode: AmMode) -> None:
        """Select deep or normal AM mode (``AM:MODE``)."""
        self.write(f"AM:MODE {_AM_MODE_SCPI[mode]}")


class FrequencyModulation(_AnalogModulation):
    """Frequency modulation (Option UNT)."""

    _prefix = "FM"

    def set_deviation(self, deviation: Quantity) -> None:
        """Set the FM deviation (``FM:DEV``, in Hz)."""
        self.write(f"FM:DEV {c.hz(deviation)}")

    def get_deviation(self) -> Quantity:
        """Read the FM deviation (``FM:DEV?``) as a frequency quantity."""
        return c.as_frequency(self.query("FM:DEV?"))


class PhaseModulation(_AnalogModulation):
    """Phase modulation (Option UNT)."""

    _prefix = "PM"

    def set_deviation(self, deviation: Quantity) -> None:
        """Set the ΦM deviation (``PM:DEV``, sent in radians).

        Accepts any angle quantity (``quantity(90, "deg")``, ``quantity(1, "rad")``).
        """
        self.write(f"PM:DEV {c.radians(deviation)}")

    def get_deviation(self) -> Quantity:
        """Read the ΦM deviation (``PM:DEV?``) as an angle quantity in radians."""
        return c.as_radians(self.query("PM:DEV?"))

    def set_bandwidth(self, bandwidth: PmBandwidth) -> None:
        """Select the ΦM bandwidth mode (``PM:BAND``): normal or high."""
        self.write(f"PM:BAND {_PM_BW_SCPI[bandwidth]}")


class PulseModulation(Menu):
    """Pulse modulation (Options UNU/UNW).

    Select an internal pulse mode or the external input with :meth:`set_source`,
    then set the timing (:meth:`set_period`, :meth:`set_width`, :meth:`set_delay`)
    and switch it on with :meth:`enable`.
    """

    def enable(self, enabled: bool = True) -> None:
        """Switch pulse modulation on/off (``PULM:STAT``)."""
        self.write(f"PULM:STAT {c.onoff(enabled)}")

    def get_enabled(self) -> bool:
        """Read whether pulse modulation is on (``PULM:STAT?``)."""
        return c.parse_bool(self.query("PULM:STAT?"))

    def set_source(self, source: PulseSource) -> None:
        """Select the pulse source (``PULM:SOUR`` / ``PULM:SOUR:INT``).

        ``EXTERNAL`` uses the rear-panel PULSE input; any other value selects the
        internal generator in that mode (square, free-run, triggered, doublet,
        gated, pulse train, …).
        """
        if source == "EXTERNAL":
            self.write("PULM:SOUR EXT")
            return
        self.write("PULM:SOUR INT")
        self.write(f"PULM:SOUR:INT {_PULSE_INTERNAL_SCPI[source]}")

    def set_period(self, period: Quantity) -> None:
        """Set the internal pulse period (``PULM:INT:PER``, in seconds)."""
        self.write(f"PULM:INT:PER {c.seconds(period)}")

    def get_period(self) -> Quantity:
        """Read the internal pulse period (``PULM:INT:PER?``)."""
        return c.as_seconds(self.query("PULM:INT:PER?"))

    def set_width(self, width: Quantity) -> None:
        """Set the internal pulse width (``PULM:INT:PWID``, in seconds)."""
        self.write(f"PULM:INT:PWID {c.seconds(width)}")

    def get_width(self) -> Quantity:
        """Read the internal pulse width (``PULM:INT:PWID?``)."""
        return c.as_seconds(self.query("PULM:INT:PWID?"))

    def set_delay(self, delay: Quantity) -> None:
        """Set the internal pulse delay (``PULM:INT:DEL``, in seconds)."""
        self.write(f"PULM:INT:DEL {c.seconds(delay)}")

    def set_rate(self, rate: Quantity) -> None:
        """Set the internal square-wave pulse rate (``PULM:INT:FREQ``, in Hz)."""
        self.write(f"PULM:INT:FREQ {c.hz(rate)}")

    def set_external_polarity(self, polarity: PulsePolarity) -> None:
        """Set the external pulse input polarity (``PULM:EXT:POL``)."""
        self.write(f"PULM:EXT:POL {_POLARITY_SCPI[polarity]}")


class Modulation(Menu):
    """The generator's modulations, one sub-menu each: ``am``, ``fm``, ``pm``, ``pulse``."""

    am: AmplitudeModulation
    fm: FrequencyModulation
    pm: PhaseModulation
    pulse: PulseModulation

    def __init__(self, parent: BaseInstrument) -> None:
        super().__init__(parent)
        self.am = AmplitudeModulation(parent)
        self.fm = FrequencyModulation(parent)
        self.pm = PhaseModulation(parent)
        self.pulse = PulseModulation(parent)

    def is_supported(self) -> bool:
        """Return ``True``: the MXG analog generators support AM/FM/ΦM/pulse (with options)."""
        return True

    def disable(self) -> None:
        """Switch every modulation off (AM, FM, ΦM and pulse)."""
        self.am.enable(False)
        self.fm.enable(False)
        self.pm.enable(False)
        self.pulse.enable(False)
