"""Reference-oscillator socket control (``REFSKT``).

The TGR6000 has a single rear-panel 10 MHz ``REF IN/OUT`` BNC whose function is
selected with one command, ``REFSKT <IN|OUT|OFF>``:

- ``IN``  — use an external 10 MHz reference (auto-detected when present),
- ``OUT`` — output the internal 10 MHz reference,
- ``OFF`` — disable the socket.

There is no separate internal/external *source* command and no query form; the
external reference is selected by choosing ``IN`` and is engaged automatically
when a valid signal is applied. Verified against the TGR6000 Instruction Manual
(Iss 9), "Command List" → "System Commands", and the "External Reference In/Out"
specification.
"""

from __future__ import annotations

from typing import Literal

from ...base import Menu

__all__ = ["Reference", "ReferenceSocket"]

#: Function of the 10 MHz reference socket.
ReferenceSocket = Literal["IN", "OUT", "OFF"]


class Reference(Menu):
    """The 10 MHz reference-oscillator socket."""

    def set_socket(self, mode: ReferenceSocket) -> None:
        """Set the reference-socket function (``REFSKT`` ``IN``/``OUT``/``OFF``)."""
        self.write(f"REFSKT {mode}")

    def use_external_input(self) -> None:
        """Select an external 10 MHz reference input (``REFSKT IN``)."""
        self.write("REFSKT IN")

    def output_internal(self) -> None:
        """Output the internal 10 MHz reference (``REFSKT OUT``)."""
        self.write("REFSKT OUT")

    def disable(self) -> None:
        """Disable the reference socket (``REFSKT OFF``)."""
        self.write("REFSKT OFF")
