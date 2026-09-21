"""System-level settings: display update, presets, key lock, reference clock, errors.

Verified against the *R&S RTO6 User Manual*, chapters 24.6 "General remote
settings", 24.7 "Instrument setup" and 24.8.14 "Reference clock":
``SYSTem:DISPlay:UPDate``, ``SYSTem:PRESet``, ``SYSTem:KLOCk``,
``SYSTem:DEVice:ID?``, ``SENSe[:ROSCillator]:SOURce``,
``SENSe[:ROSCillator]:EXTernal:FREQuency`` and ``SYSTem:ERRor:ALL?``.
"""

from __future__ import annotations

from typing import Literal

from .....units import Quantity, ensure_frequency
from ....base import Menu
from . import _common as c

__all__ = ["System"]

ReferenceSource = Literal["INTERNAL", "EXTERNAL"]


class System(Menu):
    """Instrument-wide settings."""

    def set_display_update(self, enabled: bool) -> None:
        """Keep the screen updating during remote control (``SYST:DISP:UPD``).

        Off makes measurements faster; the screen then shows a static image
        until it is switched back on.
        """
        self.write(f"SYST:DISP:UPD {c.onoff(enabled)}")

    def preset(self) -> None:
        """Reset to factory defaults (``SYST:PRES``)."""
        self.write("SYST:PRES")

    def lock_keys(self, locked: bool) -> None:
        """Lock or unlock the front panel and keyboard (``SYST:KLOC``)."""
        self.write(f"SYST:KLOC {c.onoff(locked)}")

    def get_device_id(self) -> str:
        """Part number and serial number (``SYST:DEV:ID?``)."""
        return c.parse_name(self.query("SYST:DEV:ID?"))

    def set_reference_source(self, source: ReferenceSource) -> None:
        """Use the internal OCXO or an external reference (``SENS:ROSC:SOUR``)."""
        self.write(f"SENS:ROSC:SOUR {'INT' if source == 'INTERNAL' else 'EXT'}")

    def set_external_reference_frequency(self, frequency: Quantity) -> None:
        """Set the frequency of the external reference input (``SENS:ROSC:EXT:FREQ``)."""
        ensure_frequency(frequency)
        self.write(f"SENS:ROSC:EXT:FREQ {c.hz(frequency)}")

    def get_all_errors(self) -> list[str]:
        """Read and clear the whole error queue (``SYST:ERR:ALL?``); empty if none."""
        response = self.query("SYST:ERR:ALL?").strip()
        if not response or response.startswith("0,"):
            return []
        return [item.strip() for item in response.split('",') if item.strip()]
