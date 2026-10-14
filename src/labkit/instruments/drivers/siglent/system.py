"""Reference oscillator, alignment, identity and firmware checks.

Verified against the *SHA850A User Manual* (EN01D): §7.1 "Freq Ref Input"
(``[:SENSe]:ROSCillator:SOURce:TYPE``), §8.1.1 "About"
(``:SYSTem:CONFigure:SYSTem?``), §8.2.1 "Preset", §8.3 "Alignments"
(``:CALibration``, ``:CALibration:STATe``) and §10.5 (the IEEE common commands).

Firmware
--------
Use firmware **1.8R4 or later** under remote control: the revision history lists
"SCPI freeze caused by \\*OPC? query" as solved in 1.8R4. :meth:`System.require_firmware`
checks it. The version is read from field 4 of ``*IDN?`` ("software number",
§10.5) and, failing that, from the system-information string. The manual's
``*IDN?`` example ("Siglent,SVA1015,1234567890,100.01.01.06.01") is copied from
another product, so the exact form on the SHA850A is unverified; the parser takes
``1.8R4``, ``V1.8R10``, ``1.8.4`` and the old names (``V1.1.2.1.6R5``, and the
first release ``V1.1.2.1.2`` with no ``R``).

Error queue
-----------
The SHA850A does not list ``:SYSTem:ERRor?`` (§10.6); see
:meth:`~labkit.instruments.drivers.siglent._spectrum_analyzer.SHA850A.check_errors`.
The standard event status register (``*ESR?``) is documented and readable with
:meth:`System.get_event_status`.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Literal, NamedTuple, Optional

from ....units import Quantity, quantity
from ...base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._spectrum_analyzer import SHA850A

__all__ = ["System", "ReferenceOscillator", "ReferenceSource", "Identity", "MINIMUM_FIRMWARE"]

#: The oldest firmware that does not freeze on ``*OPC?`` under SCPI.
MINIMUM_FIRMWARE: tuple[int, int, int] = (1, 8, 4)

#: Reference-oscillator source. ``AUTO`` is the manual's ``SENS`` value, read as
#: the auto selection the menu describes (priority external, GPS, internal).
ReferenceSource = Literal["INTernal", "EXTernal", "GPS", "AUTO"]

_SOURCE_SCPI = {"INTernal": "INTE", "EXTernal": "EXT", "GPS": "GPS", "AUTO": "SENS"}


class Identity(NamedTuple):
    """The fields of the ``*IDN?`` reply (empty strings for missing ones)."""

    manufacturer: str
    model: str
    serial: str
    firmware: str


class ReferenceOscillator(Menu):
    """The 10 MHz frequency reference: internal, external (BNC REF IN), GPS or auto.

    The analyzer only offers the external source while a reference is connected
    (§7.1), so read :meth:`get_source` back after selecting it — with no
    reference present the selection does not take.
    """

    def set_source(self, source: ReferenceSource) -> None:
        """Select the reference source (``:ROSC:SOUR:TYPE INTE|EXT|GPS|SENS``)."""
        self.write(f":ROSC:SOUR:TYPE {_SOURCE_SCPI[source]}")

    def get_source(self) -> str:
        """The selected source as ``"INTernal"``, ``"EXTernal"``, ``"GPS"`` or ``"AUTO"``.

        A reply the driver does not recognise is returned as sent.
        """
        response = self.query(":ROSC:SOUR:TYPE?").strip()
        word = response.upper()
        if word.startswith("INT"):
            return "INTernal"
        if word.startswith("EXT"):
            return "EXTernal"
        if word.startswith("GPS"):
            return "GPS"
        if word.startswith("SENS"):
            return "AUTO"
        return response

    def is_external(self) -> bool:
        """``True`` when the external reference is the selected source."""
        return self.get_source() == "EXTernal"


class System(Menu):
    """Identity, firmware check, alignment, preset and status registers."""

    def __init__(self, parent: "SHA850A") -> None:
        super().__init__(parent)
        self._analyzer = parent

    # -- identity -------------------------------------------------------------
    def identify(self) -> Identity:
        """Split ``*IDN?`` into manufacturer, model, serial number and firmware."""
        fields = [f.strip() for f in self.query("*IDN?").split(",")]
        fields += [""] * (4 - len(fields))
        return Identity(fields[0], fields[1], fields[2], fields[3])

    def system_info(self) -> str:
        """The system-information string (``:SYST:CONF:SYST?``): versions, options.

        The format is not documented; on the raw socket a multi-line reply would
        be read only up to its first line break.
        """
        return self.query(":SYST:CONF:SYST?").strip()

    def firmware_version(self) -> Optional[tuple[int, int, int]]:
        """The firmware version as ``(major, minor, revision)``, ``"1.8R4"`` -> ``(1, 8, 4)``.

        Read from the ``*IDN?`` firmware field, else searched for in
        :meth:`system_info`; ``None`` when neither parses.
        """
        version = c.parse_firmware(self.identify().firmware)
        if version is not None:
            return version
        try:
            return c.parse_firmware(self.system_info())
        except Exception:
            return None

    def require_firmware(
        self, minimum: tuple[int, int, int] = MINIMUM_FIRMWARE
    ) -> Optional[tuple[int, int, int]]:
        """Check the firmware is at least `minimum` and return the version found.

        Raises :class:`RuntimeError` when the version parses and is older. When it
        cannot be parsed the check cannot be made: a :class:`UserWarning` is
        issued and ``None`` returned, so an unexpected version string never stops
        a measurement on its own.
        """
        version = self.firmware_version()
        if version is None:
            warnings.warn(
                f"Could not read the analyzer's firmware version; cannot confirm it is "
                f"at least {_version_text(minimum)} (older firmware freezes on *OPC?).",
                stacklevel=2,
            )
            return None
        if version < minimum:
            raise RuntimeError(
                f"Analyzer firmware {_version_text(version)} is older than the required "
                f"{_version_text(minimum)}: update it (older firmware freezes on *OPC? under SCPI)."
            )
        return version

    # -- alignment ------------------------------------------------------------
    def align_now(self, wait: bool = True, timeout: Quantity = quantity(120, "s")) -> None:
        """Run a temperature alignment immediately (``:CAL``) and, by default, wait for it.

        Never align with a trace in ``VIEW``: firmware before 1.1.2.1.6R5 gave a
        large error then, and the design keeps the rule. The trace states are
        queried first and a :class:`RuntimeError` names a trace in view (a reply
        that cannot be read does not block the alignment). With `wait` the
        analyzer is waited for with one ``*OPC?`` of up to `timeout`.
        """
        for trace in range(1, 7):
            try:
                state = self.query(f":TRAC{trace}:DISP?").strip().upper()
            except Exception:
                # Unreadable: skip this trace (the next query resynchronises
                # the session, in case the reply comes late).
                continue
            if state.startswith("VIEW"):
                raise RuntimeError(
                    f"Trace {trace} is in VIEW; set it active (or blank) before aligning."
                )
        self.write(":CAL")
        if wait:
            self._analyzer.wait_for_instrument(timeout)

    def set_auto_alignment(self, enabled: bool) -> None:
        """Switch automatic temperature alignment on/off (``:CAL:STAT``, takes 0|1; off by default)."""
        self.write(f":CAL:STAT {int(bool(enabled))}")

    def get_auto_alignment(self) -> bool:
        return c.parse_bool(self.query(":CAL:STAT?"))

    # -- preset / status --------------------------------------------------------
    def preset(self) -> None:
        """Reset the parameters by the selected preset type (``:SYST:PRES``)."""
        self.write(":SYST:PRES")

    def clear_status(self) -> None:
        """Clear the status registers and the error queue (``*CLS``)."""
        self.write("*CLS")
        self._analyzer._probed_headers.clear()

    def get_event_status(self) -> int:
        """Read and clear the standard event status register (``*ESR?``).

        Bits per IEEE 488.2: 0 operation complete, 2 query error, 3 device error,
        4 execution error, 5 command error, 7 power on.
        """
        return c.parse_int(self.query("*ESR?"))


def _version_text(version: tuple[int, int, int]) -> str:
    major, minor, revision = version
    return f"{major}.{minor}R{revision}"
