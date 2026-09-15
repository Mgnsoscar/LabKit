"""RF output level, RF on/off, ALC and attenuator control.

Groups the ``[:SOURce]:POWer`` subsystem with the ``:OUTPut`` subsystem: the
output amplitude and its mode, the RF-output enable, the global modulation
enable, the automatic levelling control (ALC), the step attenuator, and the
level offset/reference that affect the *displayed* amplitude.

Levels are sent with an explicit ``DBM`` suffix so the command is unambiguous
whatever the instrument's persistent ``:UNIT:POWer`` setting is.

Verified against the *MXG SCPI Command Reference* (N5180-90004), "Power
Subsystem ([:SOURce]:POWer)" and "Output Subsystem (:OUTPut)".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ....units import Quantity, ensure_power
from ...base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._signal_generator import AnalogSignalGenerator

__all__ = ["Power", "PowerMode", "AlcSource", "PowerUnit"]

#: ``FIXED`` holds a set level; ``LIST`` enables the power sweep.
PowerMode = Literal["FIXED", "LIST"]
#: Where the ALC takes its levelling feedback from.
AlcSource = Literal["INTERNAL", "DIODE"]
#: Amplitude unit used for entries without a suffix and for query responses.
PowerUnit = Literal["DBM", "DBUV", "DBUVEMF", "V", "VEMF", "DB"]

_MODE_SCPI = {"FIXED": "FIX", "LIST": "LIST"}
_ALC_SOURCE_SCPI = {"INTERNAL": "INT", "DIODE": "DIOD"}


class Power(Menu):
    """The RF output: level, on/off, ALC, attenuator and level references."""

    def __init__(self, parent: "AnalogSignalGenerator") -> None:
        super().__init__(parent)
        self._gen = parent

    # -- level -------------------------------------------------------------
    def set_level(self, level: Quantity) -> None:
        """Set the RF output level (``POW``, sent in dBm).

        Accepts any power quantity (``quantity(-10, "dBm")``,
        ``quantity(1, "mW")``). Raises :class:`~labkit.units.DimensionalityError`
        if `level` is not a power and :class:`ValueError` if it is outside the
        model's settable range.
        """
        ensure_power(level)
        low, high = self._gen.level_range
        c.check_range(level, low, high, "dBm", "Level")
        self.write(f"POW {c.dbm(level)}")

    def get_level(self) -> Quantity:
        """Read the RF output level (``POW?``) as a power quantity in dBm.

        The response is interpreted in dBm, the instrument's default amplitude
        unit; call :meth:`set_unit` with ``"DBM"`` if it has been changed.
        """
        return c.as_power(self.query("POW?"))

    def set_mode(self, mode: PowerMode) -> None:
        """Set the power mode (``POW:MODE``): ``FIXED`` or ``LIST`` (swept)."""
        self.write(f"POW:MODE {_MODE_SCPI[mode]}")

    def get_mode(self) -> str:
        """Read the power mode (``POW:MODE?``), ``FIX`` or ``LIST``."""
        return c.parse_word(self.query("POW:MODE?"))

    def set_unit(self, unit: PowerUnit) -> None:
        """Set the amplitude unit for unsuffixed entries and queries (``UNIT:POW``)."""
        self.write(f"UNIT:POW {unit}")

    # -- RF output enable --------------------------------------------------
    def set_rf_enabled(self, enabled: bool) -> None:
        """Switch the RF output on/off (``OUTP``)."""
        self.write(f"OUTP {c.onoff(enabled)}")

    def get_rf_enabled(self) -> bool:
        """Read whether the RF output is on (``OUTP?``)."""
        return c.parse_bool(self.query("OUTP?"))

    def on(self) -> None:
        """Switch the RF output on (``OUTP ON``)."""
        self.set_rf_enabled(True)

    def off(self) -> None:
        """Switch the RF output off (``OUTP OFF``)."""
        self.set_rf_enabled(False)

    def set_modulation_enabled(self, enabled: bool) -> None:
        """Globally enable/disable modulation of the RF output (``OUTP:MOD``).

        This is the front-panel *Mod On/Off* key: the individual modulations
        (AM/FM/PM/pulse) only reach the output while this is on.
        """
        self.write(f"OUTP:MOD {c.onoff(enabled)}")

    def get_modulation_enabled(self) -> bool:
        """Read the global modulation state (``OUTP:MOD?``)."""
        return c.parse_bool(self.query("OUTP:MOD?"))

    # -- ALC ---------------------------------------------------------------
    def set_alc_enabled(self, enabled: bool) -> None:
        """Switch the automatic levelling control on/off (``POW:ALC``).

        Switch it off for fast pulse work; then use :meth:`power_search` to
        calibrate the open-loop level.
        """
        self.write(f"POW:ALC {c.onoff(enabled)}")

    def get_alc_enabled(self) -> bool:
        """Read the ALC state (``POW:ALC?``)."""
        return c.parse_bool(self.query("POW:ALC?"))

    def set_alc_source(self, source: AlcSource) -> None:
        """Set the ALC feedback source (``POW:ALC:SOUR``): internal or external diode detector."""
        self.write(f"POW:ALC:SOUR {_ALC_SOURCE_SCPI[source]}")

    def set_alc_bandwidth_auto(self, enabled: bool) -> None:
        """Let the instrument choose the ALC bandwidth (``POW:ALC:BAND:AUTO``)."""
        self.write(f"POW:ALC:BAND:AUTO {c.onoff(enabled)}")

    def set_alc_bandwidth(self, bandwidth: Quantity) -> None:
        """Set the ALC bandwidth (``POW:ALC:BAND``, in Hz); disables auto selection."""
        self.write(f"POW:ALC:BAND {c.hz(bandwidth)}")

    def power_search(self, mode: Literal["ON", "OFF", "ONCE"] = "ONCE") -> None:
        """Run/configure the ALC-off power search (``POW:ALC:SEAR``).

        ``ONCE`` runs one calibration now; ``ON`` re-runs it automatically after
        every relevant setting change; ``OFF`` disables it. Only meaningful with
        the ALC off and the RF output on.
        """
        self.write(f"POW:ALC:SEAR {mode}")

    # -- attenuator --------------------------------------------------------
    def set_attenuation_auto(self, enabled: bool) -> None:
        """Let the ALC control the attenuator (``POW:ATT:AUTO``); off = attenuator hold."""
        self.write(f"POW:ATT:AUTO {c.onoff(enabled)}")

    def set_attenuation(self, attenuation: Quantity) -> None:
        """Set the step attenuator (``POW:ATT``, in dB).

        Requires attenuator hold (:meth:`set_attenuation_auto` ``False``) and
        the Option 1E1 step attenuator.
        """
        self.write(f"POW:ATT {c.db(attenuation)}")

    def get_attenuation(self) -> Quantity:
        """Read the step-attenuator setting (``POW:ATT?``) as a dB ratio."""
        return c.as_ratio(self.query("POW:ATT?"))

    # -- displayed-level offset / reference --------------------------------
    def set_offset(self, offset: Quantity) -> None:
        """Set the displayed-amplitude offset (``POW:OFFS``, in dB).

        Accounts for external gain/loss so the display shows the level at the
        DUT; the RF output level itself is unchanged.
        """
        self.write(f"POW:OFFS {c.db(offset)}")

    def set_reference(self, level: Quantity, enabled: bool = True) -> None:
        """Set the amplitude reference (``POW:REF``, in dBm) and switch it on/off.

        With the reference on, amplitudes are displayed relative to it (in dB).
        """
        ensure_power(level)
        self.write(f"POW:REF {c.dbm(level)}")
        self.write(f"POW:REF:STAT {c.onoff(enabled)}")

    def set_reference_enabled(self, enabled: bool) -> None:
        """Switch the amplitude reference on/off (``POW:REF:STAT``)."""
        self.write(f"POW:REF:STAT {c.onoff(enabled)}")
