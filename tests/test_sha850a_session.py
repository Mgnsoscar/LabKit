"""The SHA850A driver's session handling, against instrument models that keep state.

Two models here, beyond the scripted mock of ``test_sha850a.py``:

- :class:`_Socket` plays the raw SCPI socket on a virtual clock, in order as the
  SHA850A manual (EN01D) §10.5 says: ``*OPC?`` holds every later command until
  the operation is over, then answers ``1``; a reply that comes after the read
  timeout is still read by the next read. It pins the resynchronisation that
  keeps a late reply from being taken for the next one (a late ``*OPC?`` ``1``
  used to be read as the marker level, +1.00 dBm, for every later reading).
- :class:`_Stateful` keeps the settings the writes make (measurement, reference
  level and offset, a write that fails), so the CW reading's one-time setup and
  its memory of what it configured can be checked against what the analyzer has.
"""

from __future__ import annotations

from typing import Any, Optional

import pytest

from labkit.instruments import SHA852A, mock_instrument
from labkit.instruments.drivers.siglent import SHA850A
from labkit.instruments.mock import MockBackend, MockEnvironment
from labkit.units import quantity as Q

_IDN = "Siglent Technologies,SHA852A,SHA85XCX123456,1.8R10"
_FREQ = Q(1575.42, "MHz")


def _level(acquisition: int) -> float:
    """The level the model's marker reads after `acquisition` acquisitions (all distinct)."""
    return -30.0 - 0.25 * acquisition


class _Socket:
    """A raw-socket SHA850A on a virtual clock (see the module note).

    `acquisitions` are the durations of the successive ``:INIT:IMM`` acquisitions
    in seconds (0.05 s once the list runs out). `inject` is a stale line queued,
    ready to read, when the first acquisition starts — a reply to some earlier
    query that came late. `silent` queries get no reply (an unknown command);
    `late` ones answer that many seconds after they are processed.
    """

    def __init__(
        self,
        acquisitions: Optional[list[float]] = None,
        *,
        swe_time: str = "0.02",
        inject: Optional[str] = None,
        silent: tuple[str, ...] = (),
        late: Optional[dict[str, float]] = None,
        replies: Optional[dict[str, str]] = None,
    ) -> None:
        self.now = 0.0
        self.timeout = 10000.0  # ms; the driver sets it like on a VISA resource
        self.acquisitions = list(acquisitions or [])
        self.swe_time = swe_time
        self.inject = inject
        self.silent = set(silent)
        self.late = dict(late or {})
        self.replies = {":INST?": "SA", ":INST:MEAS?": "SA", ":DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS?": "0"}
        self.replies.update(replies or {})
        self.ready = 0.0  # when the instrument takes the next command
        self.ends: list[float] = []  # when each acquisition ends
        self.out: list[tuple[float, str]] = []  # (readable from, line)
        self.commands: list[str] = []

    # -- what the driver calls ------------------------------------------------
    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def write(self, command: str) -> None:
        self.commands.append(command)
        at = max(self.now, self.ready)
        if command == ":INIT:IMM":
            duration = self.acquisitions.pop(0) if self.acquisitions else 0.05
            self.ends.append(at + duration)
            if self.inject is not None:
                self.out.append((at, self.inject))
                self.inject = None
        elif command == "*OPC?":
            at = max([at] + self.ends)  # held until the operation is over (§10.5)
            self.out.append((at, "1"))
        elif command.endswith("?") and command not in self.silent:
            self.out.append((at + self.late.get(command, 0.0), self._answer(command, at)))
        self.ready = at

    def read(self) -> str:
        wait_s = self.timeout / 1000.0
        if not self.out or self.out[0][0] > self.now + wait_s:
            self.now += wait_s
            raise TimeoutError("VI_ERROR_TMO")
        at, line = self.out.pop(0)
        self.now = max(self.now, at)
        return line

    def query(self, command: str) -> str:
        self.write(command)
        return self.read()

    def close(self) -> None:
        pass

    # -- the instrument -------------------------------------------------------
    def _answer(self, command: str, at: float) -> str:
        if command == "*IDN?":
            return _IDN
        if command == ":SWE:TIME?":
            return self.swe_time
        if command == ":CALC:MARK1:Y?":
            done = sum(1 for end in self.ends if end <= at)
            return f"{_level(done):.2f}"
        return self.replies.get(command, "0")


def _on_socket(socket: _Socket) -> SHA850A:
    sa = SHA852A(MockEnvironment(), "sa", "10.0.0.2", backend=socket, sleep=socket.sleep)
    sa.set_timeout(Q(10, "s"))
    return sa


def _readings(sa: SHA850A, count: int, **kwargs: Any) -> list[float]:
    return [sa.measure_cw(_FREQ, **kwargs).to("dBm").magnitude for _ in range(count)]


# -- a late *OPC? reply ---------------------------------------------------------------

def test_a_late_opc_reply_is_read_by_the_resync_not_by_the_next_query() -> None:
    # The first acquisition outlasts the *OPC? timeout (0.225 s expected + 3 s)
    # and its "1" comes long after the old 0.25 s drain window.
    socket = _Socket([3.6])
    sa = _on_socket(socket)
    assert _readings(sa, 4) == [_level(1), _level(2), _level(3), _level(4)]
    assert socket.commands.count("*IDN?") == 1  # one resynchronisation, after the first sweep


def test_a_stale_reply_in_front_of_the_opc_is_discarded() -> None:
    socket = _Socket(inject="-99.00")
    sa = _on_socket(socket)
    assert _readings(sa, 4) == [_level(1), _level(2), _level(3), _level(4)]


def test_averaged_acquisitions_are_given_their_scheduling_time() -> None:
    # 50 averages, :SWE:TIME? 0.02 s but 0.1 s per sweep in reality (the
    # reported time leaves out the scheduling time, §3.3.3): 5 s per reading.
    socket = _Socket([5.0] * 3)
    sa = _on_socket(socket)
    assert _readings(sa, 3, averages=50) == [_level(1), _level(2), _level(3)]
    assert "*IDN?" not in socket.commands  # the *OPC? timeout covered it


def test_an_acquisition_longer_than_any_estimate_is_still_read_in_step() -> None:
    socket = _Socket([20.0] * 3)
    sa = _on_socket(socket)
    assert _readings(sa, 3, averages=50) == [_level(1), _level(2), _level(3)]


def test_a_stall_beyond_the_resync_budget_raises_and_the_session_recovers() -> None:
    # 3.225 s of *OPC? plus 33.225 s of resynchronisation, and the "1" is not back.
    socket = _Socket([40.0])
    sa = _on_socket(socket)
    with pytest.raises(TimeoutError):
        sa.measure_cw(_FREQ)
    assert socket.commands.count(":CALC:MARK1:Y?") == 0  # no marker read out of step
    assert _readings(sa, 2) == [_level(2), _level(3)]
    assert socket.commands.count("*IDN?") == 1  # the owed identity was waited for, not asked again


def test_a_stale_one_taken_for_the_opc_reply_is_caught_at_the_marker() -> None:
    # A stray "1" in front of the *OPC? is indistinguishable from its reply;
    # the real "1" then reaches the marker read, which resynchronises and reads again.
    socket = _Socket([3.6], inject="1")
    sa = _on_socket(socket)
    assert _readings(sa, 3) == [_level(1), _level(2), _level(3)]


def test_channel_power_after_a_late_reply_reads_its_own_result() -> None:
    socket = _Socket([3.6], replies={":CHP:MEAS:CHP?": "-31.5,-94.6"})
    sa = _on_socket(socket)
    power, _ = sa.measurement.channel_power(_FREQ, Q(2.046, "MHz"))
    assert power == Q(-31.5, "dBm")
    assert sa.measure_cw(_FREQ).to("dBm").magnitude == _level(2)


def test_wait_for_instrument_reads_a_late_one() -> None:
    socket = _Socket([90.0])
    sa = _on_socket(socket)
    socket.write(":INIT:IMM")
    sa.wait_for_instrument(Q(60, "s"))  # the "1" at 90 s is read by the resync (60 + 30 s)
    assert sa.query("*IDN?") == _IDN


# -- other queries that time out ----------------------------------------------------

def test_an_unanswered_error_query_does_not_shift_later_replies() -> None:
    socket = _Socket(silent=(":SYST:ERR?",))
    sa = _on_socket(socket)
    sa.check_errors("after setup")  # no queue: nothing raised
    assert _readings(sa, 2) == [_level(1), _level(2)]


def test_a_late_error_reply_is_discarded() -> None:
    socket = _Socket(late={":SYST:ERR?": 3.0})
    sa = _on_socket(socket)
    sa.check_errors("after setup")
    assert _readings(sa, 2) == [_level(1), _level(2)]
    assert socket.commands.count("*IDN?") == 1


def test_align_now_skips_a_trace_it_cannot_read() -> None:
    socket = _Socket(silent=(":TRAC5:DISP?",), replies={f":TRAC{n}:DISP?": "ACTI" for n in range(1, 7)})
    sa = _on_socket(socket)
    sa.system.align_now()
    assert ":CAL" in socket.commands
    assert sa.query("*IDN?") == _IDN


def test_align_now_skips_an_unanswered_trace_on_the_mock_too() -> None:
    def responder(command: str) -> str:
        if command == ":TRAC5:DISP?":
            raise TimeoutError("VI_ERROR_TMO")
        return {"*OPC?": "1"}.get(command, "ACTI")

    sa, be = mock_instrument(SHA852A, responses=responder)
    sa.system.align_now()
    assert be.writes == [":CAL"]


# -- measure_cw's memory of what it configured ------------------------------------------

class _Stateful(MockBackend):
    """A mock that keeps what the writes set: the measurement, the reference level and its offset.

    The displayed reference level is the analyzer's own plus the offset
    (§3.4.4). `fail` maps a command prefix to an exception raised once when a
    write starts with it; `refuse_sa` makes ``:INST:MEAS SA`` not take.
    """

    def __init__(
        self,
        *,
        mode: str = "SA",
        measurement: str = "SA",
        offset_db: float = 0.0,
        ref_dbm: float = 0.0,
        refuse_sa: bool = False,
        extra: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(self._answer)
        self.mode = mode
        self.measurement = measurement
        self.offset_db = offset_db
        self.hardware_ref_dbm = ref_dbm - offset_db
        self.refuse_sa = refuse_sa
        self.fail: dict[str, BaseException] = {}
        self.extra = {"*OPC?": "1", ":SWE:TIME?": "0.02", ":CALC:MARK1:Y?": "-30.5", "*IDN?": _IDN}
        self.extra.update(extra or {})
        self.state: dict[str, str] = {}

    def write(self, command: str) -> Any:
        for prefix, exc in list(self.fail.items()):
            if command.startswith(prefix):
                del self.fail[prefix]
                raise exc
        super().write(command)
        header, _, value = command.partition(" ")
        if header == ":INST":
            self.mode = value
        elif header == ":INST:MEAS" and not (self.refuse_sa and value == "SA"):
            self.measurement = "CHP" if value.upper().startswith("CHP") else value
        elif header == ":DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS":
            self.offset_db = float(value)
        elif header == ":DISP:WIND:TRAC:Y:RLEV":
            self.hardware_ref_dbm = float(value.split()[0]) - self.offset_db
        else:
            self.state[header] = value

    def _answer(self, command: str) -> str:
        if command == ":INST?":
            return self.mode
        if command == ":INST:MEAS?":
            return self.measurement
        if command == ":DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS?":
            return repr(self.offset_db)
        if command == ":DISP:WIND:TRAC:Y:RLEV?":
            return repr(self.hardware_ref_dbm + self.offset_db)
        return self.extra.get(command, "")


def _stateful(**kwargs: Any) -> tuple[SHA850A, _Stateful]:
    backend = _Stateful(**kwargs)
    return SHA852A(MockEnvironment(), "sa", "10.0.0.2", backend=backend), backend


def _resends_everything(be: _Stateful, sa: SHA850A) -> None:
    """A measure_cw that sends the one-time setup and every setting again."""
    be.writes.clear()
    sa.measure_cw(_FREQ)
    assert ":UNIT:POW DBM" in be.writes
    assert ":FREQ:CENT 1575420000.0" in be.writes and ":FREQ:SPAN 5000.0" in be.writes
    assert ":BWID 1000.0" in be.writes and ":BWID:VID 1000.0" in be.writes


@pytest.mark.parametrize(
    "bad",
    [
        {"rbw": Q(5, "MHz")},
        {"vbw": Q(20, "MHz")},
        {"span": Q(50, "Hz")},
        {"span": Q(8, "GHz")},
    ],
)
def test_a_refused_setting_writes_nothing(bad: dict[str, Any]) -> None:
    sa, be = _stateful()
    sa.measure_cw(_FREQ)
    be.writes.clear()
    with pytest.raises(ValueError):
        sa.measure_cw(Q(1227.6, "MHz"), **bad)
    assert be.writes == []  # the center was not sent ahead of the refusal
    sa.measure_cw(_FREQ)
    assert be.writes == [":INIT:CONT OFF", ":INIT:IMM", ":CALC:MARK1:MAX"]  # and the memory is true


@pytest.mark.parametrize("exc", [OSError("VI_ERROR_IO"), KeyboardInterrupt()])
def test_a_write_that_fails_part_way_makes_the_next_call_send_everything(exc: BaseException) -> None:
    sa, be = _stateful()
    sa.measure_cw(_FREQ)
    be.fail[":FREQ:SPAN"] = exc
    with pytest.raises(type(exc)):
        sa.measure_cw(Q(1227.6, "MHz"), span=Q(20, "kHz"))
    assert be.writes[-1] == ":FREQ:CENT 1227600000.0"  # the analyzer moved; the call did not finish
    _resends_everything(be, sa)


def test_a_sweep_time_that_cannot_be_read_is_read_again() -> None:
    sa, be = _stateful()
    sa.measure_cw(_FREQ)
    be.extra[":SWE:TIME?"] = "4.0"
    real_query = be.query
    calls = {"n": 0}

    def flaky(command: str) -> str:
        if command == ":SWE:TIME?" and calls["n"] == 0:
            calls["n"] += 1
            raise TimeoutError("VI_ERROR_TMO")
        return real_query(command)

    be.query = flaky  # type: ignore[method-assign]
    with pytest.raises(TimeoutError):
        sa.measure_cw(_FREQ, rbw=Q(10, "Hz"))
    be.queries.clear()
    sa.measure_cw(_FREQ, rbw=Q(10, "Hz"))
    assert ":SWE:TIME?" in be.queries
    assert sa._cw_sweep_s == pytest.approx(4.0)


# -- the Swept SA measurement --------------------------------------------------------------

def test_measure_cw_selects_swept_sa_when_channel_power_was_left_on() -> None:
    sa, be = _stateful(measurement="CHP")
    sa.measure_cw(_FREQ)
    assert be.writes[:1] == [":INST:MEAS SA"]
    assert be.measurement == "SA"
    assert be.queries[:5] == [":INST?", ":INST:MEAS?", "*OPC?", ":INST?", ":INST:MEAS?"]
    assert be.writes.index(":INST:MEAS SA") < be.writes.index(":FREQ:CENT 1575420000.0")


def test_ensure_swept_sa_switches_the_mode_first() -> None:
    sa, be = _stateful(mode="MA", measurement="DMA")
    sa.ensure_swept_sa()
    assert be.writes == [":INST SA", ":INST:MEAS SA"]
    assert (be.mode, be.measurement) == ("SA", "SA")


def test_ensure_swept_sa_sends_nothing_when_it_is_active() -> None:
    sa, be = _stateful()
    sa.ensure_swept_sa()
    assert be.writes == []
    assert be.queries == [":INST?", ":INST:MEAS?"]


def test_a_switch_that_does_not_take_raises_and_is_tried_again() -> None:
    sa, be = _stateful(measurement="CHP", refuse_sa=True)
    with pytest.raises(RuntimeError, match="Swept SA"):
        sa.measure_cw(_FREQ)
    assert not any(command.startswith(":FREQ") for command in be.writes)  # nothing configured
    be.refuse_sa = False
    be.writes.clear()
    assert sa.measure_cw(_FREQ) == Q(-30.5, "dBm")
    assert be.writes[0] == ":INST:MEAS SA"


def test_a_failed_return_from_channel_power_is_caught_by_the_next_reading() -> None:
    sa, be = _stateful(extra={":CHP:MEAS:CHP?": "-31.5,-94.6"})
    sa.measure_cw(_FREQ)
    be.refuse_sa = True  # channel_power's own return to SA does not take
    sa.measurement.channel_power(_FREQ, Q(2.046, "MHz"))
    assert be.measurement == "CHP"
    with pytest.raises(RuntimeError, match="Swept SA"):
        sa.measure_cw(_FREQ)


# -- front-panel settings that shift the reading --------------------------------------------

def test_a_reference_level_offset_is_cleared_keeping_the_reference_level() -> None:
    # 10 dB left on at the front panel: every marker would read 10 dB high.
    sa, be = _stateful(offset_db=10.0, ref_dbm=0.0)  # displayed 0 dBm, the analyzer's own -10 dBm
    sa.measure_cw(_FREQ)
    assert be.offset_db == 0.0
    assert be.hardware_ref_dbm == 0.0  # the reference level the caller set, now for real
    offset = be.writes.index(":DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS 0.0")
    assert be.writes[offset + 1] == ":DISP:WIND:TRAC:Y:RLEV 0.0 DBM"
    assert be.writes.index(":UNIT:POW DBM") < offset  # the reference level was read in dBm


def test_no_offset_no_reference_level_write() -> None:
    sa, be = _stateful(ref_dbm=-40.0)
    sa.measure_cw(_FREQ)
    assert not any(command.startswith(":DISP:WIND:TRAC:Y") for command in be.writes)
    assert ":DISP:WIND:TRAC:Y:RLEV?" not in be.queries


def test_an_offset_that_cannot_be_cleared_safely_raises_before_writing() -> None:
    sa, be = _stateful(offset_db=10.0, ref_dbm=30.0)  # +30 dBm displayed: beyond the +23 dBm limit
    with pytest.raises(ValueError, match="Reference level"):
        sa.measure_cw(_FREQ)
    assert be.offset_db == 10.0


def test_corrections_and_peak_criteria_are_switched_off() -> None:
    sa, be = _stateful()
    sa.measure_cw(_FREQ)
    for n in range(1, 9):
        assert be.state[f":CORR:CSET{n}"] == "0"
    assert be.state[":CALC:MARK:PEAK:THR:STAT"] == "OFF"
    assert be.state[":CALC:MARK:PEAK:EXC:STAT"] == "OFF"


def test_correction_menu() -> None:
    sa, be = mock_instrument(SHA852A, responses={":CORR:CSET3?": "1"})
    sa.amplitude.set_correction(3, True)
    sa.amplitude.set_correction(8, False)
    assert be.writes == [":CORR:CSET3 1", ":CORR:CSET8 0"]
    assert sa.amplitude.get_correction(3) is True
    with pytest.raises(ValueError):
        sa.amplitude.set_correction(9, False)


def test_a_marker_reading_of_one_on_a_synchronous_backend_is_a_level() -> None:
    # A mock cannot fall out of step: "1" is +1 dBm there, not an *OPC? reply.
    sa, _ = _stateful(extra={":CALC:MARK1:Y?": "1"})
    assert sa.measure_cw(_FREQ) == Q(1, "dBm")




def test_a_late_identity_reply_is_not_taken_for_the_resync() -> None:
    # The caller's own *IDN? times out: its late reply looks exactly like a
    # sentinel's, so it is counted as one owed — and serves as the sentinel,
    # rather than a second *IDN? whose reply would be left in flight.
    socket = _Socket(late={"*IDN?": 12.0})
    sa = _on_socket(socket)
    with pytest.raises(TimeoutError):
        sa.get_id()
    assert _readings(sa, 2) == [_level(1), _level(2)]
    assert socket.commands.count("*IDN?") == 1
    socket.late.clear()
    assert sa.get_id() == _IDN
