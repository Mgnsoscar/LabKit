"""The SPID MD-01 rotator driver against a scripted controller: the packets, the decoding, the wait for arrival."""

from __future__ import annotations

from time import perf_counter
from typing import cast

import pytest

from labkit.instruments import MD01, mock_instrument
from labkit.instruments.drivers.spid.md01 import (
    CMD_MOVE,
    CMD_SET,
    CMD_STATUS,
    CMD_STOP,
    RotorError,
    decode_reply,
    encode_set,
)
from labkit.units import quantity as Q


class Controller:
    """A scripted MD-01: answers status/stop/set with its position, moves `step` degrees per status poll."""

    def __init__(self, azimuth: float = 0.0, elevation: float = 0.0, step: float = 10.0, resolution: int = 10) -> None:
        self.azimuth, self.elevation, self.step, self.resolution = azimuth, elevation, step, resolution
        self.target = (azimuth, elevation)
        self.packets: list[bytes] = []
        #: A jog in progress (direction bits, and when it started): the rotator turns `jog_rate` degrees per
        #: second until the stop lands, at least one resolution step.
        self.jogging = 0
        self.jog_started = 0.0
        self.jog_rate = 2.0

    def _frame(self) -> bytes:
        def digits(angle: float) -> bytes:
            pulses = int(round(self.resolution * (360 + angle)))
            return bytes(int(c) for c in f"{pulses:04d}")
        return bytes([0x57]) + digits(self.azimuth) + bytes([self.resolution]) + digits(self.elevation) \
            + bytes([self.resolution, 0x20])

    def __call__(self, packet: bytes) -> bytes:
        self.packets.append(packet)
        assert len(packet) == 13 and packet[0] == 0x57 and packet[12] == 0x20
        command = packet[11]
        if command == CMD_SET:
            az = int(packet[1:5].decode()) / packet[5] - 360
            el = int(packet[6:10].decode()) / packet[10] - 360
            self.target = (az, el)
            return self._frame()                       # the MD-01 replies with where it is now
        if command == CMD_STOP:
            if self.jogging:                            # the pulse turned the rotator this far
                advance = max(0.1, round(self.jog_rate * (perf_counter() - self.jog_started), 1))
                sign = 1 if self.jogging & 0x02 else -1 if self.jogging & 0x01 else 0
                self.azimuth = round(self.azimuth + sign * advance, 1)
                up = 1 if self.jogging & 0x04 else -1 if self.jogging & 0x08 else 0
                self.elevation = round(self.elevation + up * advance, 1)
                self.jogging = 0
            self.target = (self.azimuth, self.elevation)
            return self._frame()
        if command == CMD_STATUS:
            for name, goal in (("azimuth", self.target[0]), ("elevation", self.target[1])):
                here = getattr(self, name)
                delta = max(-self.step, min(self.step, goal - here))
                setattr(self, name, round(here + delta, 1))
            return self._frame()
        if command == CMD_MOVE:
            self.jogging, self.jog_started = packet[1], perf_counter()
            return b""                                 # no reply to a jog
        raise AssertionError(f"unknown command {command:#x}")


def rotor(controller: Controller) -> MD01:
    instrument, _ = mock_instrument(MD01, raw_responses=controller, name="Rotor", address="COM7")
    return cast(MD01, instrument)


def test_addresses_cover_serial_ports_and_the_ethernet_socket() -> None:
    assert rotor(Controller())._address == "ASRL7::INSTR"
    assert mock_instrument(MD01, address="/dev/ttyUSB0")[0]._address == "ASRL/dev/ttyUSB0::INSTR"
    assert mock_instrument(MD01, address="192.168.0.20")[0]._address == "TCPIP0::192.168.0.20::23::SOCKET"
    assert mock_instrument(MD01, address="192.168.0.20:4000")[0]._address == "TCPIP0::192.168.0.20::4000::SOCKET"


def test_packets_follow_the_rot2prog_layout() -> None:
    assert encode_set(85.0, 0.0, 10, 10) == b"W4450\x0a3600\x0a\x2f "
    assert encode_set(-10.0, 45.0, 1, 1) == b"W0350\x010405\x01\x2f "
    with pytest.raises(ValueError):
        encode_set(700.0, 0.0, 10, 10)                 # 10 × 1060 does not fit four digits
    reply = bytes([0x57, 4, 4, 5, 0, 10, 3, 6, 0, 0, 10, 0x20])       # 4450/10 − 360 = 85°, 3600/10 − 360 = 0°
    p = decode_reply(reply)
    assert p.azimuth.magnitude == pytest.approx(85.0) and p.elevation.magnitude == pytest.approx(0.0)
    assert p.az_resolution == 10
    with pytest.raises(ValueError):
        decode_reply(reply[:-1])


def test_status_stop_and_set_talk_to_the_controller() -> None:
    c = Controller(azimuth=123.4, elevation=5.0)
    r = rotor(c)
    p = r.get_position()
    assert p.azimuth.magnitude == pytest.approx(123.4) and p.elevation.magnitude == pytest.approx(5.0)
    assert c.packets[-1][11] == CMD_STATUS
    r.set_position(Q(200, "deg"))                       # elevation kept: a status first, then the set
    assert [pk[11] for pk in c.packets[-2:]] == [CMD_STATUS, CMD_SET]
    assert c.target == (200.0, 5.0)
    assert c.packets[-1][5] == 10                       # the controller's own resolution, learnt from its replies
    r.stop()
    assert c.packets[-1][11] == CMD_STOP and c.target[0] == c.azimuth
    r.move("left")
    assert c.packets[-1][11] == CMD_MOVE and c.packets[-1][1] == 0x01
    with pytest.raises(ValueError):
        r.move("sideways")  # type: ignore[arg-type]


def test_move_to_waits_for_arrival_and_rest() -> None:
    c = Controller(azimuth=0.0, step=10.0)
    r = rotor(c)
    p = r.move_to(Q(45, "deg"), tolerance=Q(0.5, "deg"), poll=Q(0, "s"), settle=Q(0, "s"))
    assert p.azimuth.magnitude == pytest.approx(45.0)
    statuses = sum(1 for pk in c.packets if pk[11] == CMD_STATUS)
    assert statuses >= 6                                # 5 steps of 10° plus the confirming poll at rest
    # a target the controller never reaches (outside its limits: it does not move) times out, motors stopped
    original = c.__call__

    def ignore_set(packet: bytes) -> bytes:
        if packet[11] == CMD_SET:
            c.packets.append(packet)
            return c._frame()                           # acknowledged, but the target is not taken
        return original(packet)

    r._backend._raw_responses = ignore_set  # type: ignore[attr-defined]
    with pytest.raises(RotorError, match="MIN/MAX ANGLE"):
        r.move_to(Q(400, "deg"), timeout=Q(5, "s"), poll=Q(0, "s"), settle=Q(0, "s"))
    # a controller that stops short of the target (its dead band) with a tolerance it cannot meet
    r._backend._raw_responses = original  # type: ignore[attr-defined]
    c.step = 10.0
    stops_short = Controller(azimuth=45.0, step=10.0)
    stops_short.__class__ = type("Short", (Controller,), {})
    short = rotor(stops_short)

    def short_of_target(packet: bytes) -> bytes:
        if packet[11] == CMD_SET:
            stops_short.packets.append(packet)
            az = int(packet[1:5].decode()) / packet[5] - 360
            stops_short.target = (az - 0.3, stops_short.target[1])   # lands 0.3° early
            return stops_short._frame()
        return Controller.__call__(stops_short, packet)

    short._backend._raw_responses = short_of_target  # type: ignore[attr-defined]
    with pytest.raises(RotorError, match="stopped at 54.7° azimuth, 0.3° from the target 55°"):
        short.move_to(Q(55, "deg"), tolerance=Q(0, "deg"), poll=Q(0, "s"), settle=Q(0, "s"), nudge=False)
    assert short.move_to(Q(65, "deg"), tolerance=Q(0.5, "deg"), poll=Q(0, "s"), settle=Q(0, "s")).azimuth.magnitude == pytest.approx(64.7)
    # with nudging (the default) the driver creeps the rest of the way with jog pulses, like the buttons
    p = short.move_to(Q(75, "deg"), tolerance=Q(0, "deg"), poll=Q(0, "s"), settle=Q(0, "s"))
    assert p.azimuth.magnitude == pytest.approx(75.0, abs=0.1)
    jogs = [pk for pk in stops_short.packets if pk[11] == CMD_MOVE]
    assert jogs and all(pk[1] == 0x02 for pk in jogs)                # nudged clockwise over the last 0.3°
    assert stops_short.packets[-1][11] in (CMD_STATUS, CMD_STOP)
    # and a big overshoot on the first pulse is corrected with shorter ones the other way
    stops_short.jog_rate = 20.0
    p = short.move_to(Q(85, "deg"), tolerance=Q(0, "deg"), poll=Q(0, "s"), settle=Q(0, "s"))
    assert p.azimuth.magnitude == pytest.approx(85.0, abs=0.11)      # within one resolution step
    assert any(pk[1] == 0x01 for pk in stops_short.packets if pk[11] == CMD_MOVE)
    # a rotator still moving when the time runs out: stopped and reported
    slow = rotor(Controller(azimuth=0.0, step=0.1))
    with pytest.raises(TimeoutError, match="still moving"):
        slow.move_to(Q(300, "deg"), timeout=Q(0.05, "s"), poll=Q(0.01, "s"), settle=Q(0, "s"))
    assert slow._backend.raw_writes[-1][11] == CMD_STOP  # type: ignore[attr-defined]


def test_shutdown_stops_the_motors_and_dummy_mode_is_silent() -> None:
    c = Controller()
    r = rotor(c)
    r.close()
    assert c.packets[-1][11] == CMD_STOP
    dummy, backend = mock_instrument(MD01, name="Rotor", address="COM3")   # no responder: nothing comes back
    assert dummy.get_position().azimuth.magnitude == 0.0
    assert dummy.set_position(Q(30, "deg")) is None
    assert any(w[11] == CMD_SET for w in backend.raw_writes)
