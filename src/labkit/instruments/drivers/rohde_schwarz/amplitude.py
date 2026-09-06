"""Amplitude and RF input path (``DISPlay``, ``INPut``, ``CALCulate:UNIT``)."""

from __future__ import annotations

from typing import Literal

from ....units import Quantity
from ...base import Menu
from . import _common as c

__all__ = ["Amplitude", "PowerUnit", "Coupling", "Impedance"]

#: Amplitude (y-axis) units the FSV3000 can display.
PowerUnit = Literal["DBM", "DBMV", "DBUV", "DBUA", "V", "W", "A"]
Coupling = Literal["AC", "DC"]
Impedance = Literal[50, 75]


class Amplitude(Menu):
    """Reference level, attenuation, preamplifier, y-unit and RF input path."""

    # -- reference level ---------------------------------------------------
    def set_ref_level(self, level: Quantity) -> None:
        """Set the reference level (``DISP:TRAC:Y:SCAL:RLEV``), in dBm."""
        self.write(f"DISP:TRAC:Y:SCAL:RLEV {c.dbm(level)}")

    def get_ref_level(self) -> Quantity:
        return c.as_power(self.query("DISP:TRAC:Y:SCAL:RLEV?"))

    def set_ref_level_offset(self, offset: Quantity) -> None:
        """Set a level offset added to displayed levels (``...:RLEV:OFFS``), in dB."""
        self.write(f"DISP:TRAC:Y:SCAL:RLEV:OFFS {c.db(offset)}")

    def set_range(self, span: Quantity) -> None:
        """Set the displayed y-axis range (``DISP:TRAC:Y:SCAL``), in dB."""
        self.write(f"DISP:TRAC:Y:SCAL {c.db(span)}")

    def adjust_ref_level(self) -> None:
        """Auto-set the reference level to the current signal (``ADJ:LEV``)."""
        self.write("ADJ:LEV")

    def set_unit(self, unit: PowerUnit) -> None:
        """Set the amplitude (y-axis) unit (``CALC:UNIT:POW``)."""
        self.write(f"CALC:UNIT:POW {unit}")

    def get_unit(self) -> str:
        return self.query("CALC:UNIT:POW?").strip()

    # -- attenuation / preamp ----------------------------------------------
    def set_attenuation(self, attenuation: Quantity) -> None:
        """Set the RF input attenuation (``INP:ATT``), in dB. Disables auto."""
        self.write(f"INP:ATT {c.db(attenuation)}")

    def get_attenuation(self) -> Quantity:
        return c.as_ratio(self.query("INP:ATT?"))

    def set_attenuation_auto(self, enabled: bool) -> None:
        """Couple the attenuation to the reference level (``INP:ATT:AUTO``)."""
        self.write(f"INP:ATT:AUTO {c.onoff(enabled)}")

    def set_preamp(self, enabled: bool) -> None:
        """Switch the internal preamplifier on/off (``INP:GAIN:STAT``)."""
        self.write(f"INP:GAIN:STAT {c.onoff(enabled)}")

    def set_preamp_level(self, gain: Quantity) -> None:
        """Select the preamplifier gain (``INP:GAIN``), e.g. 15 dB or 30 dB."""
        self.write(f"INP:GAIN {c.db(gain)}")

    # -- input path --------------------------------------------------------
    def set_coupling(self, coupling: Coupling) -> None:
        """Set AC or DC input coupling (``INP:COUP``)."""
        self.write(f"INP:COUP {coupling}")

    def set_impedance(self, impedance: Impedance) -> None:
        """Set the reference input impedance in ohms (``INP:IMP``)."""
        self.write(f"INP:IMP {impedance}")
