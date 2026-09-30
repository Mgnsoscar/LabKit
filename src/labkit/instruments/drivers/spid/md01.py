"""SPID Elektronik MD-01 antenna rotator controller, Rot2Prog protocol.

The MD-01 (and the MD-02/MD-03, which speak the same protocol) drives one or
two rotator motors (azimuth, or azimuth and elevation) and takes commands on
its RS232 ports, its USB device port (a virtual COM port, 8 data bits, 1 stop
bit, no parity, baud rate from the controller's ``SET USB COM`` menu) or its
Ethernet port (TCP, port 23). The port's ``CONTROL`` must be set to the port
used and its ``PROT.`` to ``SPID ROT2``.

The protocol (SPID's Rot2Prog, documented by the community rather than by
SPID; every implementation agrees on the bytes below)
-----------------------------------------------------------------------------

Every command is 13 bytes::

    byte   0     1  2  3  4    5     6  7  8  9   10     11    12
           0x57  H1 H2 H3 H4   PH    V1 V2 V3 V4  PV     K     0x20
           'W'   azimuth       az    elevation    el     cmd   ' '
                 ASCII digits  res.  ASCII digits res.

with ``K`` = ``0x0F`` stop, ``0x1F`` status, ``0x2F`` set position, and, on the
MD-01 family only, ``0x14`` move (jog) with the direction bits in byte 1
(``0x01`` left, ``0x02`` right, ``0x04`` up, ``0x08`` down). For *set*, the
digits carry ``PH × (360 + azimuth)`` and ``PV × (360 + elevation)`` as four
ASCII digits (the 360 offset keeps the number positive), where PH/PV is the
controller's resolution in pulses per degree.

The controller answers status, stop and (the MD-01 family, unlike the original
Rot2Prog boxes) set with 12 bytes::

    byte   0     1  2  3  4    5     6  7  8  9   10     11
           0x57  H1 H2 H3 H4   PH    V1 V2 V3 V4  PV     0x20

where the H and V bytes are *binary* digits (0–9, not ASCII) of
``PH × (360 + azimuth)`` and ``PV × (360 + elevation)``; the MD-01 reports
PH = PV = 10 (0.1° resolution), so a reading of ``0 4 5 0 / 10`` is 450/10 −
360 = 85°. The driver takes the resolution from the controller's own reply and
uses it for the next *set*, so it needs no configuration for it.

Positions are :class:`~labkit.units.Quantity` angles in degrees. The
controller's own limits (its ``MIN ANGLE``/``MAX ANGLE``, default 0 to 359°
azimuth, 0 to 90° elevation) are enforced by the controller, which ignores a
target outside them; :meth:`MD01.move_to` therefore times out rather than
reporting a false arrival.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import perf_counter, sleep
from typing import TYPE_CHECKING, Any, Literal, Optional

from ....units import Quantity, ensure_time, quantity
from ...base import Backend, BaseInstrument, DummyBackend

if TYPE_CHECKING:
    from ...environment import TestEnvironment

__all__ = ["MD01", "RotorPosition", "Direction"]

Direction = Literal["left", "right", "up", "down"]

FRAME_START = 0x57
FRAME_END = 0x20
CMD_STOP = 0x0F
CMD_STATUS = 0x1F
CMD_SET = 0x2F
CMD_MOVE = 0x14
_DIRECTION_BITS: dict[str, int] = {"left": 0x01, "right": 0x02, "up": 0x04, "down": 0x08}
#: The resolution assumed until the controller has reported its own (the MD-01 reports 10).
DEFAULT_RESOLUTION = 10
_REPLY_LENGTH = 12


@dataclass(frozen=True)
class RotorPosition:
    """The controller's reported position and the resolutions (pulses per degree) it reports with."""

    azimuth: Quantity
    elevation: Quantity
    az_resolution: int
    el_resolution: int


def _degrees(value: Any) -> float:
    """A plain number of degrees from an angle quantity (or a bare number taken as degrees)."""
    if hasattr(value, "to"):
        return float(value.to("deg").magnitude)
    return float(value)


def encode_set(azimuth_deg: float, elevation_deg: float, az_resolution: int, el_resolution: int) -> bytes:
    """The 13-byte *set position* command."""
    packet = bytearray(13)
    packet[0] = FRAME_START
    for offset, angle, resolution in ((1, azimuth_deg, az_resolution), (6, elevation_deg, el_resolution)):
        pulses = int(round(resolution * (360.0 + angle)))
        if not 0 <= pulses <= 9999:
            raise ValueError(f"An angle of {angle:g}° cannot be encoded at {resolution} pulses per degree.")
        packet[offset:offset + 4] = f"{pulses:04d}".encode("ascii")
        packet[offset + 4] = resolution
    packet[11] = CMD_SET
    packet[12] = FRAME_END
    return bytes(packet)


def encode_simple(command: int, byte1: int = 0) -> bytes:
    """A 13-byte command with no position: stop, status, or move with its direction bits."""
    packet = bytearray(13)
    packet[0] = FRAME_START
    packet[1] = byte1
    packet[11] = command
    packet[12] = FRAME_END
    return bytes(packet)


def decode_reply(frame: bytes) -> RotorPosition:
    """The position in a 12-byte reply; raises :class:`ValueError` on a malformed frame."""
    if len(frame) != _REPLY_LENGTH or frame[0] != FRAME_START or frame[11] != FRAME_END:
        raise ValueError(f"Malformed reply from the rotator controller: {frame.hex(' ') if frame else 'nothing'}")
    az_res = frame[5] or DEFAULT_RESOLUTION
    el_res = frame[10] or DEFAULT_RESOLUTION
    az_pulses = frame[1] * 1000 + frame[2] * 100 + frame[3] * 10 + frame[4]
    el_pulses = frame[6] * 1000 + frame[7] * 100 + frame[8] * 10 + frame[9]
    return RotorPosition(quantity(az_pulses / az_res - 360.0, "deg"), quantity(el_pulses / el_res - 360.0, "deg"),
                         az_res, el_res)


class MD01(BaseInstrument):
    """The SPID MD-01 rotator controller (also MD-02/MD-03) on the Rot2Prog protocol.

    Parameters
    ----------
    address:
        A serial port (``"COM5"``, ``"/dev/ttyUSB0"`` or a full ``ASRL...``
        resource) for the USB or RS232 connection, or the controller's IP
        address (``"192.168.0.20"``, optionally ``"host:port"``) for the
        Ethernet port.
    baud_rate:
        For a serial connection: must match the port's ``BAUD`` in the
        controller's menu.
    timeout:
        How long a reply may take; a controller busy driving the motors still
        answers within a fraction of a second.
    """

    def __init__(
        self,
        environment: "TestEnvironment",
        name: str,
        address: str,
        baud_rate: int = 115200,
        timeout: Quantity = quantity(5, "s"),
        backend: Optional[Backend] = None,
    ) -> None:
        self._baud_rate = int(baud_rate)
        self._az_resolution = DEFAULT_RESOLUTION
        self._el_resolution = DEFAULT_RESOLUTION
        #: One command and its reply at a time (the base class's own lock guards ``close``, which calls ``stop``).
        self._io_lock = Lock()
        super().__init__(environment, name, address, timeout=timeout, backend=backend)
        self._configure_serial()

    def _build_address(self, address: str) -> str:
        address = address.strip()
        upper = address.upper()
        if upper.startswith("ASRL") or upper.startswith("TCPIP"):
            return address
        if upper.startswith("COM") and upper[3:].isdigit():
            return f"ASRL{int(upper[3:])}::INSTR"
        if address.startswith("/dev/"):
            return f"ASRL{address}::INSTR"
        host, _, port = address.partition(":")
        return f"TCPIP0::{host}::{port or 23}::SOCKET"

    def _configure_serial(self) -> None:
        """Serial parameters on a real PyVISA serial resource: the controller's fixed 8N1 and the chosen baud rate."""
        resource: Any = self._backend
        if isinstance(resource, DummyBackend) or not hasattr(resource, "baud_rate"):
            return
        try:
            from pyvisa import constants

            resource.baud_rate = self._baud_rate
            resource.data_bits = 8
            resource.parity = constants.Parity.none
            resource.stop_bits = constants.StopBits.one
        except Exception:
            pass

    # -- the protocol ------------------------------------------------------
    def _exchange(self, packet: bytes, reply: bool = True) -> Optional[RotorPosition]:
        """Send one command and read the controller's 12-byte reply (``None`` when the transport gives nothing)."""
        with self._io_lock:
            self._backend.write_raw(packet)  # type: ignore[attr-defined]
            if not reply:
                return None
            frame = self._backend.read_bytes(_REPLY_LENGTH)  # type: ignore[attr-defined]
        if not frame:
            return None
        position = decode_reply(bytes(frame))
        self._az_resolution, self._el_resolution = position.az_resolution, position.el_resolution
        return position

    def get_id(self) -> str:
        """The controller has no identification query; the driver names it."""
        return "SPID Elektronik MD-01 rotator controller (Rot2Prog protocol)"

    def get_position(self) -> RotorPosition:
        """The current azimuth and elevation (the *status* command)."""
        position = self._exchange(encode_simple(CMD_STATUS))
        if position is None:
            return RotorPosition(quantity(0.0, "deg"), quantity(0.0, "deg"), self._az_resolution, self._el_resolution)
        return position

    def get_azimuth(self) -> Quantity:
        """The current azimuth in degrees."""
        return self.get_position().azimuth

    def set_position(self, azimuth: Any, elevation: Any = None) -> Optional[RotorPosition]:
        """Start moving to `azimuth` (and `elevation`, the current one if omitted) and return at once.

        Angles are degree quantities (bare numbers are taken as degrees). The
        MD-01 answers with the position it is at when the command arrives;
        that reply is returned. Use :meth:`move_to` to wait for the arrival.
        """
        az = _degrees(azimuth)
        el = _degrees(elevation) if elevation is not None else _degrees(self.get_position().elevation)
        packet = encode_set(az, el, self._az_resolution, self._el_resolution)
        return self._exchange(packet)

    def stop(self) -> Optional[RotorPosition]:
        """Stop both motors where they are."""
        return self._exchange(encode_simple(CMD_STOP))

    def move(self, direction: Direction) -> None:
        """Jog in one direction until :meth:`stop` (an MD-01 family extension of the protocol)."""
        if direction not in _DIRECTION_BITS:
            raise ValueError(f"direction must be one of {sorted(_DIRECTION_BITS)}, not {direction!r}")
        self._exchange(encode_simple(CMD_MOVE, _DIRECTION_BITS[direction]), reply=False)

    def move_to(
        self,
        azimuth: Any,
        elevation: Any = None,
        tolerance: Quantity = quantity(0.5, "deg"),
        timeout: Quantity = quantity(180, "s"),
        settle: Quantity = quantity(0.5, "s"),
        poll: Quantity = quantity(0.5, "s"),
    ) -> RotorPosition:
        """Move to `azimuth` (and `elevation`) and wait until the rotator has arrived and come to rest.

        Arrival is the reported position within `tolerance` of the target on
        two polls `settle` apart with no movement between them. Raises
        :class:`TimeoutError`, after stopping the motors, if that does not
        happen within `timeout` (a target outside the controller's limits is
        never reached).
        """
        target_az = _degrees(azimuth)
        target_el = _degrees(elevation) if elevation is not None else None
        tol = _degrees(tolerance)
        deadline = perf_counter() + float(ensure_time(timeout).to("s").magnitude)
        self.set_position(target_az, target_el)
        wait, rest = float(ensure_time(poll).to("s").magnitude), float(ensure_time(settle).to("s").magnitude)
        last: Optional[RotorPosition] = None
        while True:
            sleep(wait)
            position = self.get_position()
            arrived = abs(_degrees(position.azimuth) - target_az) <= tol and (
                target_el is None or abs(_degrees(position.elevation) - target_el) <= tol)
            if arrived and last is not None and _degrees(position.azimuth) == _degrees(last.azimuth) \
                    and _degrees(position.elevation) == _degrees(last.elevation):
                return position
            last = position if arrived else None
            if arrived:
                sleep(rest)
            if perf_counter() > deadline:
                self.stop()
                raise TimeoutError(
                    f"'{self._name}' did not reach {target_az:g}° azimuth within {timeout:~}; it reports "
                    f"{_degrees(position.azimuth):g}° (is the target inside the controller's MIN/MAX ANGLE?)."
                )

    # -- failsafe ------------------------------------------------------------
    def _shutdown_procedure(self) -> None:
        """Stop the motors when the session closes, whatever the script was doing."""
        try:
            self.stop()
        except Exception:
            pass
