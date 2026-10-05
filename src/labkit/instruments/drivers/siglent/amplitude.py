"""Amplitude and RF input path (``:DISPlay``, ``[:SENSe]:POWer``, ``:UNIT``).

Verified against the *SHA850A User Manual* (EN01D) §3.4.1–§3.4.5 and §3.5
(amplitude corrections). Any change of reference level, attenuation,
preamplifier or reference offset restarts the sweep (§3.4).

The reference level offset "changes both the reference level readout and the
amplitude readout of the marker; but does not impact the position of traces"
(§3.4.4), and an enabled correction set shifts every level read (§3.5): both are
front-panel settings that persist, which
:meth:`~labkit.instruments.drivers.siglent._spectrum_analyzer.SHA850A.measure_cw`
switches off before it reads.

Limits
------
- **Attenuation** is 0 … 50 dB in **2 dB steps** ("even gears only", §3.4.2; the
  datasheet agrees). An odd or out-of-range value is refused with
  :class:`ValueError` here rather than left to the instrument's rounding, so a
  calibration never runs at an attenuation it did not ask for.
- **Reference level**: the manual gives −170 … +23 dBm (§3.4.1), the datasheet
  −200 … +30 dBm. Only the range both promise, −170 … +23 dBm, is accepted.
"""

from __future__ import annotations

from typing import Literal

from ....units import DimensionalityError, Quantity, ensure_power, is_dimensionless_decibel, quantity
from ...base import Menu
from . import _common as c

__all__ = ["Amplitude", "PowerUnit", "ScaleType", "CORRECTION_SETS"]

#: Amplitude (y-axis) units (§3.4.5.3).
PowerUnit = Literal["DBM", "DBMV", "DBUV", "DBUA", "V", "W"]
#: Y-axis scale type (§3.4.5.2).
ScaleType = Literal["LINear", "LOGarithmic"]

_REF_LEVEL_RANGE_DBM = (-170.0, 23.0)
_ATTENUATION_MAX_DB = 50
#: The amplitude-correction sets (``:CORR:CSET1`` … ``CSET8``, §3.5).
CORRECTION_SETS = range(1, 9)


def _even_attenuation(attenuation: Quantity) -> int:
    """`attenuation` in dB as an even integer 0 … 50, or :class:`ValueError`."""
    if not is_dimensionless_decibel(attenuation):
        got = getattr(attenuation, "units", type(attenuation).__name__)
        raise DimensionalityError(f"Expected an attenuation in dB (e.g. quantity(20, 'dB')). Got '{got}'.")
    value = float(attenuation.to("dB").magnitude)
    nearest = round(value)
    if abs(value - nearest) > 1e-9 or nearest % 2 or not 0 <= nearest <= _ATTENUATION_MAX_DB:
        raise ValueError(
            f"Attenuation {attenuation} is not available: the SHA850A takes even values "
            f"0–{_ATTENUATION_MAX_DB} dB (2 dB steps)."
        )
    return int(nearest)


def _correction_set(number: int) -> int:
    if int(number) not in CORRECTION_SETS:
        raise ValueError(f"Correction set must be 1–8, got {number}.")
    return int(number)


class Amplitude(Menu):
    """Reference level and its offset, attenuation, preamplifier, y-axis scale and unit, corrections."""

    # -- reference level ---------------------------------------------------
    @staticmethod
    def check_ref_level(level: Quantity) -> float:
        """`level` in dBm when it is a valid reference level (−170 … +23 dBm), else :class:`ValueError`."""
        value = float(ensure_power(level).to("dBm").magnitude)
        c.check_range(value, *_REF_LEVEL_RANGE_DBM, "Reference level", "dBm")
        return value

    def set_ref_level(self, level: Quantity) -> None:
        """Set the reference level (``:DISP:WIND:TRAC:Y:RLEV``), −170 … +23 dBm.

        Sent with an explicit ``DBM`` suffix (the manual's own example), so the
        value means dBm whatever y-axis unit is selected.
        """
        self.check_ref_level(level)
        self.write(f":DISP:WIND:TRAC:Y:RLEV {c.dbm(level)} DBM")

    def get_ref_level(self) -> Quantity:
        return c.as_power(self.query(":DISP:WIND:TRAC:Y:RLEV?"))

    def set_ref_level_offset(self, offset: Quantity) -> None:
        """Offset the reference level and marker readouts (``:DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS``), dB.

        The traces do not move (§3.4.4): the displayed reference level changes
        by the offset while the analyzer's own stays put.
        """
        self.write(f":DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS {c.db(offset)}")

    def get_ref_level_offset(self) -> Quantity:
        return c.as_ratio(self.query(":DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS?"))

    def set_scale(self, per_division: Quantity) -> None:
        """Set the log-scale y-axis per division (``:DISP:WIND:TRAC:Y:PDIV``), 0.1 … 20 dB."""
        self.write(f":DISP:WIND:TRAC:Y:PDIV {c.db(per_division)}")

    def set_scale_type(self, scale: ScaleType) -> None:
        """Select a linear or logarithmic y-axis (``:DISP:WIND:TRAC:Y:SPAC``)."""
        self.write(f":DISP:WIND:TRAC:Y:SPAC {scale}")

    def set_unit(self, unit: PowerUnit) -> None:
        """Set the amplitude (y-axis) unit (``:UNIT:POW``)."""
        self.write(f":UNIT:POW {unit}")

    def get_unit(self) -> str:
        return self.query(":UNIT:POW?").strip()

    # -- attenuation / preamp ----------------------------------------------
    def set_attenuation(self, attenuation: Quantity) -> None:
        """Set the RF input attenuation (``:POW:ATT``), an even value 0 … 50 dB.

        Raises :class:`ValueError` for an odd or out-of-range value (2 dB steps).
        """
        self.write(f":POW:ATT {_even_attenuation(attenuation)}")

    def get_attenuation(self) -> Quantity:
        return quantity(c.parse_int(self.query(":POW:ATT?")), "dB")

    def set_attenuation_auto(self, enabled: bool) -> None:
        """Couple the attenuation to reference level and preamp (``:POW:ATT:AUTO``)."""
        self.write(f":POW:ATT:AUTO {c.onoff(enabled)}")

    def is_attenuation_auto(self) -> bool:
        return c.parse_bool(self.query(":POW:ATT:AUTO?"))

    def set_preamp(self, enabled: bool) -> None:
        """Switch the internal preamplifier (25 dB nominal) on/off (``:POW:GAIN``)."""
        self.write(f":POW:GAIN {c.onoff(enabled)}")

    def get_preamp(self) -> bool:
        return c.parse_bool(self.query(":POW:GAIN?"))

    # -- amplitude corrections ---------------------------------------------
    def set_correction(self, number: int, enabled: bool) -> None:
        """Switch amplitude correction set `number` (1-8) on/off (``:CORR:CSET<n>``, takes 0|1).

        "There are eight corrections, which enter into force at the same time"
        (§3.5): an enabled set shifts every level read, markers included.
        """
        self.write(f":CORR:CSET{_correction_set(number)} {int(bool(enabled))}")

    def get_correction(self, number: int) -> bool:
        """``True`` while amplitude correction set `number` (1-8) is on (``:CORR:CSET<n>?``)."""
        return c.parse_bool(self.query(f":CORR:CSET{_correction_set(number)}?"))
