"""System, store/recall and status commands.

Groups the MXG housekeeping commands: preset, self-test, the SCPI error queue,
instrument-state registers, the remote display, and power-on behaviour.

The MXG implements the SCPI-99 ``:SYSTem:ERRor?`` queue and answers ``+0,"No
error"`` when it is empty (note the leading ``+``, which
:meth:`~labkit.instruments.drivers.keysight._signal_generator.AnalogSignalGenerator.check_errors`
accounts for).

Verified against the *MXG SCPI Command Reference* (N5180-90004), "System
Commands" (``:SYSTem``, ``:DISPlay``, ``:STATus``) and "IEEE 488.2 Common
Commands".
"""

from __future__ import annotations

from typing import Literal

from ...base import Menu
from . import _common as c

__all__ = ["System", "PowerOnType"]

#: Instrument state applied at power-on.
PowerOnType = Literal["PRESET", "LAST", "USER"]

_PON_SCPI = {"PRESET": "PRES", "LAST": "LAST", "USER": "USER"}


class System(Menu):
    """Preset, self-test, error queue, state registers and front-panel settings."""

    # -- preset / self-test ------------------------------------------------
    def preset(self) -> None:
        """Return the generator to its preset state (``SYST:PRES``, the front-panel Preset key)."""
        self.write("SYST:PRES")

    def self_test(self) -> bool:
        """Run the instrument self-test (``*TST?``); return ``True`` if it passes (``0``)."""
        return c.parse_int(self.query("*TST?")) == 0

    def clear_status(self) -> None:
        """Clear the status registers and the error queue (``*CLS``)."""
        self.write("*CLS")

    # -- error queue -------------------------------------------------------
    def get_error(self) -> tuple[int, str]:
        """Pop the oldest error from the queue (``SYST:ERR?``) as ``(code, message)``.

        Returns ``(0, "No error")`` when the queue is empty.
        """
        response = self.query("SYST:ERR?").strip()
        code_text, _, message = response.partition(",")
        return c.parse_int(code_text), message.strip().strip('"')

    def get_all_errors(self) -> list[tuple[int, str]]:
        """Drain the error queue, returning every ``(code, message)`` pair (oldest first)."""
        errors: list[tuple[int, str]] = []
        while True:
            code, message = self.get_error()
            if code == 0:
                return errors
            errors.append((code, message))

    # -- instrument-state registers ----------------------------------------
    def save_state(self, register: int, sequence: int = 0) -> None:
        """Save the current instrument state to a register (``*SAV <reg>,<seq>``)."""
        self.write(f"*SAV {int(register)},{int(sequence)}")

    def recall_state(self, register: int, sequence: int = 0) -> None:
        """Recall an instrument state from a register (``*RCL <reg>,<seq>``)."""
        self.write(f"*RCL {int(register)},{int(sequence)}")

    # -- front panel / power-on -------------------------------------------
    def set_remote_display_update(self, enabled: bool) -> None:
        """Keep the display updating under remote control (``DISP:REM``).

        Switching it off speeds up remote operation slightly.
        """
        self.write(f"DISP:REM {c.onoff(enabled)}")

    def set_power_on_type(self, power_on: PowerOnType) -> None:
        """Set the state restored at power-on (``SYST:PON:TYPE``): preset, last, or user preset."""
        self.write(f"SYST:PON:TYPE {_PON_SCPI[power_on]}")

    def get_operation_condition(self) -> int:
        """Read the Standard Operation Condition Register (``STAT:OPER:COND?``).

        Bit 3 (value 8) is set while a sweep is in progress; bit 5 (value 32)
        while waiting for a trigger.
        """
        return c.parse_int(self.query("STAT:OPER:COND?"))
