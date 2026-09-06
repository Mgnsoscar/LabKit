"""System, store/recall and status commands.

Groups the TGR6000 housekeeping commands: self-test and error queues, setup and
sweep-list stores, front-panel behaviour, and power-up RF state. Verified
against the TGR6000 Instruction Manual (Iss 9), "Command List" → "System
Commands", "Status Commands" and "Miscellaneous Commands".

The TGR6000 does **not** implement the SCPI-99 ``SYST:ERR?`` error queue; errors
are read from the Execution Error Register with ``EER?`` (see
:meth:`~labkit.instruments.drivers.aim_tti._signal_generator.SignalGenerator.check_errors`).
"""

from __future__ import annotations

from typing import Literal

from ...base import Menu
from . import _common as c

__all__ = ["System", "PowerUpMode", "EditMode"]

#: RF-output state applied at power-up.
PowerUpMode = Literal["ON", "OFF", "LAST"]
#: Front-panel frequency/level editing mode.
EditMode = Literal["SCROLL", "STEP", "BOTH"]


class System(Menu):
    """Self-test, error queues, stores, and front-panel/power-up settings."""

    # -- self-test / status ------------------------------------------------
    def self_test(self) -> bool:
        """Run the generator self-test (``*TST?``); return ``True`` if it passes.

        ``*TST?`` returns ``0`` on success or a non-zero error code on failure.
        """
        return c.parse_int(self.query("*TST?")) == 0

    def clear_status(self) -> None:
        """Clear the status registers and error queues (``*CLS``)."""
        self.write("*CLS")

    def get_execution_error(self) -> int:
        """Read and clear the Execution Error Register (``EER?``); ``0`` means none."""
        return c.parse_int(self.query("EER?"))

    def get_query_error(self) -> int:
        """Read and clear the Query Error Register (``QER?``); ``0`` means none."""
        return c.parse_int(self.query("QER?"))

    def get_address(self) -> int:
        """Return the instrument's bus address / identifier (``ADDRESS?``)."""
        return c.parse_int(self.query("ADDRESS?"))

    # -- store / recall ----------------------------------------------------
    def save_setup(self, store: int) -> None:
        """Save the current set-up to store `store` (``SAVESETUP``)."""
        self.write(f"SAVESETUP {int(store)}")

    def recall_setup(self, store: int) -> None:
        """Recall a set-up from store `store` (``RCLSETUP``)."""
        self.write(f"RCLSETUP {int(store)}")

    def save_list(self, store: int) -> None:
        """Save the current sweep list to list store `store` (``SAVELIST``)."""
        self.write(f"SAVELIST {int(store)}")

    def recall_list(self, store: int) -> None:
        """Recall a sweep list from list store `store` (``RCLLIST``)."""
        self.write(f"RCLLIST {int(store)}")

    # -- front panel / power-up -------------------------------------------
    def go_to_local(self) -> None:
        """Return the instrument to local control and unlock the keyboard (``LOCAL``)."""
        self.write("LOCAL")

    def set_power_up_mode(self, mode: PowerUpMode) -> None:
        """Set the RF-output state applied at power-up (``PWRUPMODE``)."""
        self.write(f"PWRUPMODE {mode}")

    def set_buzzer(self, enabled: bool) -> None:
        """Switch the internal buzzer on/off (``BUZZ``)."""
        self.write(f"BUZZ {c.onoff(enabled)}")

    def set_edit_mode(self, mode: EditMode) -> None:
        """Set the front-panel edit mode (``EDITMODE`` ``SCROLL``/``STEP``/``BOTH``)."""
        self.write(f"EDITMODE {mode}")
