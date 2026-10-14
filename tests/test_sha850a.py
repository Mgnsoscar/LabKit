"""The Siglent SHA850A driver (SHA851A / SHA852A), exercised through the mock backend.

Asserts the exact SCPI strings the driver emits (verified against the SHA850A
User Manual, EN01D), the range checks, and the robust sequences the calibration
runner relies on: the single sweep with its ``*OPC?`` fallback, the cached CW
reading, and channel power with its two read forms.
"""

from __future__ import annotations

import inspect
import math
import typing
from typing import Any, Callable, Optional

import numpy as np
import pytest

from labkit.instruments import SHA851A, SHA852A, mock_instrument
from labkit.instruments.drivers import siglent
from labkit.instruments.drivers.siglent import SHA850A, dbm_per_hz
from labkit.instruments.drivers.siglent._common import parse_firmware
from labkit.instruments.mock import MockBackend, MockEnvironment
from labkit.units import DimensionalityError, quantity as Q

_IDN = "Siglent Technologies,SHA852A,SHA85XCX123456,1.8R10"
#: What a clean analyzer answers to the one-time setup's checks of measure_cw.
_SWEPT_SA = {":INST?": "SA", ":INST:MEAS?": "SA", ":DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS?": "0"}


def _sa(
    responses: Optional[dict[str, str]] = None, cls: type[SHA850A] = SHA852A, **kwargs: Any
) -> tuple[SHA850A, MockBackend]:
    table = {"*IDN?": _IDN, "*OPC?": "1", ":SWE:TIME?": "0.02", **_SWEPT_SA}
    table.update(responses or {})
    sa, be = mock_instrument(cls, responses=table, **kwargs)
    return sa, be


class _Sleeps:
    """A stand-in for time.sleep that records what it was asked to sleep."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


# -- identity / connection ----------------------------------------------------

def test_models_share_the_base_as_siblings() -> None:
    assert issubclass(SHA851A, SHA850A) and issubclass(SHA852A, SHA850A)
    assert not issubclass(SHA851A, SHA852A) and not issubclass(SHA852A, SHA851A)
    assert SHA851A.max_frequency == Q(3.6, "GHz")
    assert SHA852A.max_frequency == Q(7.5, "GHz")


def test_bare_ip_becomes_a_raw_socket_on_port_5025() -> None:
    sa, _ = mock_instrument(SHA852A, address="192.168.1.50")
    assert sa._address == "TCPIP::192.168.1.50::5025::SOCKET"


@pytest.mark.parametrize(
    "resource",
    [
        "TCPIP0::192.168.1.50::5025::SOCKET",
        "TCPIP::192.168.1.50::INSTR",
        "USB0::0xF4EC::0x1300::SHA85XCX123456::INSTR",
    ],
)
def test_full_visa_resource_is_used_verbatim(resource: str) -> None:
    sa, _ = mock_instrument(SHA852A, address=resource)
    assert sa._address == resource


def test_id_and_identify() -> None:
    sa, _ = _sa()
    assert sa.get_id() == _IDN
    ident = sa.system.identify()
    assert ident.manufacturer == "Siglent Technologies"
    assert ident.model == "SHA852A"
    assert ident.serial == "SHA85XCX123456"
    assert ident.firmware == "1.8R10"


def test_shutdown_returns_to_continuous_sweep() -> None:
    sa, be = _sa()
    sa.close()
    assert be.writes[-1] == ":INIT:CONT ON"
    assert be.log[-1] == "CLOSE"


# -- frequency ------------------------------------------------------------------

def test_frequency_commands_convert_to_hz() -> None:
    sa, be = _sa()
    sa.frequency.set_center(Q(1575.42, "MHz"))
    sa.frequency.set_span(Q(5, "kHz"))
    sa.frequency.set_start(Q(1, "GHz"))
    sa.frequency.set_stop(Q(1.8, "GHz"))
    sa.frequency.set_span(Q(0, "Hz"))
    assert be.writes == [
        ":FREQ:CENT 1575420000.0",
        ":FREQ:SPAN 5000.0",
        ":FREQ:STAR 1000000000.0",
        ":FREQ:STOP 1800000000.0",
        ":FREQ:SPAN 0.0",
    ]


def test_frequency_is_checked_against_the_model() -> None:
    small, _ = _sa(cls=SHA851A)
    with pytest.raises(ValueError):
        small.frequency.set_center(Q(4, "GHz"))
    big, be = _sa()
    big.frequency.set_center(Q(4, "GHz"))
    assert be.writes == [":FREQ:CENT 4000000000.0"]
    with pytest.raises(ValueError):
        big.frequency.set_stop(Q(8, "GHz"))
    with pytest.raises(ValueError):
        big.frequency.set_span(Q(50, "Hz"))  # non-zero spans start at 100 Hz
    with pytest.raises(DimensionalityError):
        big.frequency.set_center(Q(1, "dBm"))


def test_frequency_getters_parse_hz() -> None:
    sa, _ = _sa({":FREQ:CENT?": "1.57542e+09", ":FREQ:SPAN?": "5000"})
    assert sa.frequency.get_center().to("Hz").magnitude == pytest.approx(1.57542e9)
    assert sa.frequency.get_span() == Q(5, "kHz")


# -- bandwidth -------------------------------------------------------------------

def test_bandwidth_commands() -> None:
    sa, be = _sa()
    sa.bandwidth.set_rbw(Q(1, "kHz"))
    sa.bandwidth.set_rbw_auto(False)
    sa.bandwidth.set_vbw(Q(3, "kHz"))
    sa.bandwidth.set_vbw_auto(True)
    sa.bandwidth.set_vbw_rbw_ratio(3)
    assert be.writes == [
        ":BWID 1000.0",
        ":BWID:AUTO OFF",
        ":BWID:VID 3000.0",
        ":BWID:VID:AUTO ON",
        ":BWID:VID:RAT 3.0",
    ]


def test_rbw_limit_is_the_one_both_documents_promise() -> None:
    sa, be = _sa()
    sa.bandwidth.set_rbw(Q(3, "MHz"))
    with pytest.raises(ValueError):
        sa.bandwidth.set_rbw(Q(10, "MHz"))  # manual lists it, datasheet stops at 3 MHz
    sa.bandwidth.set_vbw(Q(10, "MHz"))
    with pytest.raises(ValueError):
        sa.bandwidth.set_vbw_rbw_ratio(2.0)
    assert be.writes == [":BWID 3000000.0", ":BWID:VID 10000000.0"]


def test_bandwidth_getters() -> None:
    sa, _ = _sa({":BWID?": "1000", ":BWID:VID?": "3000", ":BWID:AUTO?": "0"})
    assert sa.bandwidth.get_rbw() == Q(1, "kHz")
    assert sa.bandwidth.get_vbw() == Q(3, "kHz")
    assert sa.bandwidth.is_rbw_auto() is False


# -- sweep -------------------------------------------------------------------------

def test_sweep_commands() -> None:
    sa, be = _sa()
    sa.sweep.set_continuous(False)
    sa.sweep.set_time(Q(50, "ms"))
    sa.sweep.set_time_auto(True)
    sa.sweep.set_points(1001)
    sa.sweep.set_speed("ACCUracy")
    sa.sweep.set_mode("FFT")
    sa.sweep.set_mode_auto(True)
    assert be.writes == [
        ":INIT:CONT OFF",
        ":SWE:TIME 0.05",
        ":SWE:TIME:AUTO ON",
        ":SWE:POIN 1001",
        ":SWE:SPE ACCUracy",
        ":SWE:MODE FFT",
        ":SWE:MODE:AUTO ON",
    ]
    assert sa.sweep.get_time() == Q(20, "ms")


@pytest.mark.parametrize("points", [200, 10002])
def test_sweep_points_are_range_checked(points: int) -> None:
    sa, be = _sa()
    with pytest.raises(ValueError):
        sa.sweep.set_points(points)
    assert be.writes == []


# -- amplitude ---------------------------------------------------------------------

def test_amplitude_commands() -> None:
    sa, be = _sa()
    sa.amplitude.set_ref_level(Q(-40, "dBm"))
    sa.amplitude.set_attenuation(Q(20, "dB"))
    sa.amplitude.set_attenuation_auto(False)
    sa.amplitude.set_preamp(True)
    sa.amplitude.set_unit("DBM")
    sa.amplitude.set_ref_level_offset(Q(10, "dB"))
    assert be.writes == [
        ":DISP:WIND:TRAC:Y:RLEV -40.0 DBM",
        ":POW:ATT 20",
        ":POW:ATT:AUTO OFF",
        ":POW:GAIN ON",
        ":UNIT:POW DBM",
        ":DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS 10.0",
    ]


@pytest.mark.parametrize("value", [0, 2, 20, 48, 50])
def test_even_attenuation_is_accepted(value: int) -> None:
    sa, be = _sa()
    sa.amplitude.set_attenuation(Q(value, "dB"))
    assert be.writes == [f":POW:ATT {value}"]


@pytest.mark.parametrize("value", [1, 19, 20.5, 52, -2])
def test_odd_or_out_of_range_attenuation_is_refused(value: float) -> None:
    sa, be = _sa()
    with pytest.raises(ValueError):
        sa.amplitude.set_attenuation(Q(value, "dB"))
    assert be.writes == []


def test_attenuation_must_be_a_db_ratio() -> None:
    sa, _ = _sa()
    with pytest.raises(DimensionalityError):
        sa.amplitude.set_attenuation(Q(20, "dBm"))


def test_ref_level_range_is_the_one_both_documents_promise() -> None:
    sa, _ = _sa()
    sa.amplitude.set_ref_level(Q(23, "dBm"))
    sa.amplitude.set_ref_level(Q(-170, "dBm"))
    with pytest.raises(ValueError):
        sa.amplitude.set_ref_level(Q(30, "dBm"))  # datasheet: up to +30, manual: +23
    with pytest.raises(DimensionalityError):
        sa.amplitude.set_ref_level(Q(10, "MHz"))


def test_amplitude_getters() -> None:
    sa, _ = _sa({":DISP:WIND:TRAC:Y:RLEV?": "-40", ":POW:ATT?": "20", ":POW:GAIN?": "0"})
    assert sa.amplitude.get_ref_level() == Q(-40, "dBm")
    assert sa.amplitude.get_attenuation() == Q(20, "dB")
    assert sa.amplitude.get_preamp() is False


# -- trace -------------------------------------------------------------------------

def test_trace_commands() -> None:
    sa, be = _sa()
    sa.trace.set_detector("AVERage")
    sa.trace.set_detector("POSitive", trace=2)
    sa.trace.set_average_type("POWer")
    sa.trace.set_type(1, "AVERage")
    sa.trace.set_average_count(16, trace=1)
    sa.trace.set_display_state("ACTIve", 3)
    sa.trace.clear_average(1)
    assert be.writes == [
        ":DET:TRAC1 AVERage",
        ":DET:TRAC2 POSitive",
        ":AVER:TYPE POWer",
        ":TRAC1:TYPE AVERage",
        ":AVER:TRAC1:COUN 16",
        ":TRAC3:DISP ACTIve",
        ":AVER:TRAC1:CLE",
    ]
    assert sa.trace.sweeps_per_acquisition() == 16
    assert sa.trace.averaging_traces() == [1]


def test_trace_and_count_are_range_checked() -> None:
    sa, be = _sa()
    with pytest.raises(ValueError):
        sa.trace.set_type(7, "WRITe")
    with pytest.raises(ValueError):
        sa.trace.set_average_count(1000)
    assert be.writes == []


def test_trace_data_is_ascii_and_sized_from_the_returned_values() -> None:
    # 1001 sweep points set, but FFT mode returned only five (and a trailing comma).
    sa, be = _sa(
        {
            ":SWE:POIN?": "1001",
            ":TRAC1:DATA?": "-80.5,-60.25,-20.0,-61.0,-79.75,",
            ":FREQ:STAR?": "1575418000",
            ":FREQ:STOP?": "1575422000",
        }
    )
    freqs, levels = sa.trace.get_data(1)
    assert be.writes == [":FORM ASC"]
    assert be.queries == [":TRAC1:DATA?", ":FREQ:STAR?", ":FREQ:STOP?"]
    np.testing.assert_allclose(freqs.to("Hz").magnitude, [1575418000, 1575419000, 1575420000, 1575421000, 1575422000])
    np.testing.assert_allclose(levels.to("dBm").magnitude, [-80.5, -60.25, -20.0, -61.0, -79.75])
    assert str(levels.units) == "dBm"


def test_empty_trace_data_raises() -> None:
    sa, _ = _sa()
    with pytest.raises(RuntimeError):
        sa.trace.get_data(1)


def test_get_x_takes_a_trace_like_the_rs_analyzers() -> None:
    # get_x(1) is "the axis of trace 1" (the R&S signature), never a one-point axis.
    sa, be = _sa(
        {
            ":TRAC1:DATA?": "-80.5,-60.25,-20.0,-61.0,-79.75",
            ":FREQ:STAR?": "1575418000",
            ":FREQ:STOP?": "1575422000",
        }
    )
    freqs = sa.trace.get_x(1)
    assert len(freqs.magnitude) == 5
    assert be.queries == [":TRAC1:DATA?", ":FREQ:STAR?", ":FREQ:STOP?"]
    be.queries.clear()
    assert len(sa.trace.get_x(points=3).magnitude) == 3  # sized by the caller: no trace read
    assert be.queries == [":FREQ:STAR?", ":FREQ:STOP?"]
    with pytest.raises(TypeError):
        sa.trace.get_x(1, 5)  # type: ignore[call-arg]  # points is keyword-only
    with pytest.raises(ValueError):
        sa.trace.get_x(7, points=5)


# -- marker -------------------------------------------------------------------------

def test_marker_commands_and_reads() -> None:
    sa, be = _sa({":CALC:MARK2:X?": "1.57542e9", ":CALC:MARK2:Y?": "-31.25"})
    marker = sa.marker(2, enable=True)
    marker.peak_search()
    marker.set_mode("POSition")
    marker.set_function("OFF")
    assert be.writes == [
        ":CALC:MARK2:STAT ON",
        ":CALC:MARK2:MAX",
        ":CALC:MARK2:MODE POSition",
        ":CALC:MARK2:FUNC OFF",
    ]
    assert marker.get_x().to("Hz").magnitude == pytest.approx(1.57542e9)
    assert marker.get_y() == Q(-31.25, "dBm")


def test_marker_to_center_reads_then_sets() -> None:
    sa, be = _sa({":CALC:MARK1:X?": "1.2276e9"})
    sa.marker(1).to_center()
    assert be.queries[-1] == ":CALC:MARK1:X?"
    assert be.writes == [":FREQ:CENT 1227600000.0"]


def test_marker_number_is_checked() -> None:
    sa, _ = _sa()
    with pytest.raises(ValueError):
        sa.marker(9)


# -- reference / alignment ----------------------------------------------------------

def test_reference_source_commands() -> None:
    sa, be = _sa()
    sa.reference.set_source("EXTernal")
    sa.reference.set_source("INTernal")
    sa.reference.set_source("AUTO")
    assert be.writes == [":ROSC:SOUR:TYPE EXT", ":ROSC:SOUR:TYPE INTE", ":ROSC:SOUR:TYPE SENS"]


@pytest.mark.parametrize(
    "reply, expected",
    [("EXT", "EXTernal"), ("INTE", "INTernal"), ("INTernal", "INTernal"), ("GPS", "GPS"), ("SENS", "AUTO"), ("ODD", "ODD")],
)
def test_reference_source_reply_is_normalised(reply: str, expected: str) -> None:
    sa, _ = _sa({":ROSC:SOUR:TYPE?": reply})
    assert sa.reference.get_source() == expected
    assert sa.reference.is_external() is (expected == "EXTernal")


def test_align_now_checks_traces_then_aligns_and_waits() -> None:
    sa, be = _sa({f":TRAC{n}:DISP?": "ACTI" for n in range(1, 7)})
    sa.system.align_now()
    assert be.writes == [":CAL"]
    assert be.queries == [f":TRAC{n}:DISP?" for n in range(1, 7)] + ["*OPC?"]


def test_align_now_refuses_a_trace_in_view() -> None:
    sa, be = _sa({":TRAC3:DISP?": "VIEW"})
    with pytest.raises(RuntimeError, match="Trace 3"):
        sa.system.align_now()
    assert ":CAL" not in be.writes


def test_auto_alignment_takes_0_or_1() -> None:
    sa, be = _sa({":CAL:STAT?": "1"})
    sa.system.set_auto_alignment(True)
    sa.system.set_auto_alignment(False)
    assert be.writes == [":CAL:STAT 1", ":CAL:STAT 0"]
    assert sa.system.get_auto_alignment() is True


# -- firmware ------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("1.8R4", (1, 8, 4)),
        ("1.8R10", (1, 8, 10)),
        ("V1.8R10", (1, 8, 10)),
        ("v1.8r5", (1, 8, 5)),
        ("1.8.4", (1, 8, 4)),
        ("V1.8.4", (1, 8, 4)),
        ("V1.1.2.1.6R5", (1, 6, 5)),
        ("V1.1.2.1.5R0", (1, 5, 0)),
        ("V1.1.2.1.2", (1, 2, 0)),  # the first release: no "R" (revision history)
        ("Software Version V1.1.2.1.2, FPGA 2.0", (1, 2, 0)),
        ("Software Version: 1.8R10, FPGA: 2.0.1", (1, 8, 10)),
        ("100.01.01.06.01", None),
        ("", None),
        ("unknown", None),
    ],
)
def test_firmware_parsing(text: str, expected: Optional[tuple[int, int, int]]) -> None:
    assert parse_firmware(text) == expected


def test_firmware_from_idn() -> None:
    sa, _ = _sa({"*IDN?": "Siglent Technologies,SHA852A,SN1,V1.8R4"})
    assert sa.system.firmware_version() == (1, 8, 4)


def test_firmware_falls_back_to_the_system_information() -> None:
    sa, be = _sa(
        {
            "*IDN?": "Siglent,SHA852A,SN1,100.01.01.06.01",
            ":SYST:CONF:SYST?": "SHA852A; Software Version 1.8R5; FPGA 3.2",
        }
    )
    assert sa.system.firmware_version() == (1, 8, 5)
    assert be.queries == ["*IDN?", ":SYST:CONF:SYST?"]


def test_require_firmware_passes_returns_and_refuses() -> None:
    sa, _ = _sa()
    assert sa.system.require_firmware() == (1, 8, 10)
    assert sa.system.require_firmware((1, 8, 10)) == (1, 8, 10)
    old, _ = _sa({"*IDN?": "Siglent,SHA852A,SN1,1.8R3"})
    with pytest.raises(RuntimeError, match="1.8R3"):
        old.system.require_firmware((1, 8, 4))


def test_require_firmware_refuses_the_first_release() -> None:
    sa, _ = _sa({"*IDN?": "Siglent,SHA852A,SN1,V1.1.2.1.2"})
    with pytest.raises(RuntimeError, match="1.2R0"):
        sa.system.require_firmware()


def test_require_firmware_warns_when_the_version_cannot_be_read() -> None:
    sa, _ = _sa({"*IDN?": "Siglent,SHA852A,SN1,100.01.01.06.01"})
    with pytest.warns(UserWarning, match="firmware"):
        assert sa.system.require_firmware() is None


# -- error queue -----------------------------------------------------------------------

@pytest.mark.parametrize("reply", ["", "0", '0,"No error"', '+0,"No error"'])
def test_check_errors_tolerates_no_queue(reply: str) -> None:
    sa, be = _sa({":SYST:ERR?": reply})
    sa.check_errors("after setup")
    assert be.queries == [":SYST:ERR?"]


def _error_queue(*entries: str) -> Callable[[str], str]:
    """A responder whose :SYST:ERR? pops `entries` like a real queue, then answers "0"."""
    queue = list(entries)

    def responder(command: str) -> str:
        if command == ":SYST:ERR?":
            return queue.pop(0) if queue else '0,"No error"'
        return {"*OPC?": "1", ":SWE:TIME?": "0.02", "*IDN?": _IDN, **_SWEPT_SA}.get(command, "")

    return responder


@pytest.mark.parametrize(
    "entry",
    ['-113,"Undefined header;:CHP:FREQ:SPAN 3069000.0"', '-113,"Undefined header"', "Undefined header"],
)
def test_check_errors_reports_an_undefined_header(entry: str) -> None:
    # A -113 names an earlier command the analyzer did not know (it cannot be
    # about :SYST:ERR? itself: an unknown query gets no reply at all).
    sa, _ = mock_instrument(SHA852A, responses=_error_queue(entry))
    with pytest.raises(RuntimeError, match="-113|Undefined header"):
        sa.check_errors("after channel power")


def test_check_errors_reads_the_whole_queue() -> None:
    sa, be = mock_instrument(
        SHA852A,
        responses=_error_queue('-113,"Undefined header;:CHP:FREQ:SPAN 3069000.0"', '-222,"Data out of range"'),
    )
    with pytest.raises(RuntimeError) as raised:
        sa.check_errors("after channel power")
    assert "CHP:FREQ:SPAN" in str(raised.value) and "-222" in str(raised.value)
    assert be.queries == [":SYST:ERR?"] * 3  # two entries, then "0"
    sa.check_errors("again")  # the queue is empty now


def test_check_errors_skips_the_drivers_own_probe() -> None:
    # channel_power tries the SHA read form first; an analyzer that only knows
    # the SSA form leaves a -113 for it, which is expected.
    queue: list[str] = []

    def responder(command: str) -> str:
        if command == ":CHP:MEAS:CHP?":
            queue.append('-113,"Undefined header;:CHP:MEAS:CHP?"')
            raise TimeoutError("VI_ERROR_TMO")
        if command == ":SYST:ERR?":
            return queue.pop(0) if queue else "0"
        return {"*OPC?": "1", ":SWE:TIME?": "0.1", ":MEAS:CHP?": "-29.0,-92.0"}.get(command, "")

    sa, _ = mock_instrument(SHA852A, responses=responder)
    sa.measurement.channel_power(Q(1575.42, "MHz"), Q(2.046, "MHz"))
    sa.check_errors("after channel power")
    # Only once: the same -113 again, with no probe to explain it, is reported.
    queue.append('-113,"Undefined header;:CHP:MEAS:CHP?"')
    with pytest.raises(RuntimeError, match="-113"):
        sa.check_errors("later")


def test_a_bare_undefined_header_is_skipped_only_while_a_probe_explains_it() -> None:
    sa, _ = mock_instrument(SHA852A, responses=_error_queue('-113,"Undefined header"'))
    sa._note_probe(":CHP:MEAS:CHP?")
    sa.check_errors("after channel power")  # the probe explains it
    bare, _ = mock_instrument(SHA852A, responses=_error_queue('-113,"Undefined header"'))
    with pytest.raises(RuntimeError, match="-113"):
        bare.check_errors("no probe")  # nothing explains it
    cleared, _ = mock_instrument(SHA852A, responses=_error_queue('-113,"Undefined header"'))
    cleared._note_probe(":CHP:MEAS:CHP?")
    cleared.system.clear_status()  # *CLS empties the queue, and the probe with it
    with pytest.raises(RuntimeError, match="-113"):
        cleared.check_errors("a later error")


def test_check_errors_tolerates_no_reply_at_all() -> None:
    def responder(command: str) -> str:
        if command == ":SYST:ERR?":
            raise TimeoutError("VI_ERROR_TMO")
        return ""

    sa, be = mock_instrument(SHA852A, responses=responder)
    sa.check_errors("after setup")
    assert be.queries == [":SYST:ERR?"]


def test_check_errors_raises_a_real_error() -> None:
    sa, _ = _sa({":SYST:ERR?": '-222,"Data out of range"'})
    with pytest.raises(RuntimeError, match="-222"):
        sa.check_errors("Setting the span")


# -- single sweep -------------------------------------------------------------------------

def test_single_sweep_sequence() -> None:
    sleeps = _Sleeps()
    sa, be = _sa(sleep=sleeps)
    sa.single_sweep()
    assert be.writes == [":INIT:CONT OFF", ":INIT:IMM"]
    assert be.queries == [":SWE:TIME?", "*OPC?"]
    assert sleeps.calls == []


def test_single_sweep_sleeps_when_opc_returns_nothing() -> None:
    sleeps = _Sleeps()
    sa, be = _sa({"*OPC?": "", ":SWE:TIME?": "0.4"}, sleep=sleeps)
    sa.single_sweep()
    assert be.writes == [":INIT:CONT OFF", ":INIT:IMM"]
    assert sleeps.calls == [pytest.approx((0.4 * 1.25 + 0.2) + 0.5)]


def test_single_sweep_sleeps_when_opc_raises() -> None:
    sleeps = _Sleeps()

    def responder(command: str) -> str:
        if command == "*OPC?":
            raise TimeoutError("VI_ERROR_TMO")
        return {":SWE:TIME?": "0.2"}.get(command, "")

    sa, _ = mock_instrument(SHA852A, responses=responder, sleep=sleeps)
    sa.single_sweep()
    assert sleeps.calls == [pytest.approx((0.2 * 1.25 + 0.2) + 0.5)]


def test_single_sweep_restarts_and_waits_for_every_average() -> None:
    sleeps = _Sleeps()
    sa, be = _sa({"*OPC?": "", ":SWE:TIME?": "0.1"}, sleep=sleeps)
    sa.trace.set_type(1, "AVERage")
    sa.trace.set_average_count(8)
    be.writes.clear()
    sa.single_sweep()
    assert be.writes == [":INIT:CONT OFF", ":AVER:TRAC1:CLE", ":INIT:IMM"]
    assert sleeps.calls == [pytest.approx(8 * (0.1 * 1.25 + 0.2) + 0.5)]


class _TimedBackend:
    """A backend that records the I/O timeout each query was made with (like a VISA resource)."""

    def __init__(self, replies: dict[str, Any], stale: Optional[list[str]] = None) -> None:
        self.timeout = 10000.0
        self.replies = replies
        self.stale = list(stale or [])
        self.queries: list[tuple[str, float]] = []
        self.writes: list[str] = []
        self.reads = 0

    def query(self, command: str) -> str:
        self.queries.append((command, self.timeout))
        reply = self.replies.get(command, "")
        if isinstance(reply, BaseException):
            raise reply
        return str(reply)

    def write(self, command: str) -> None:
        self.writes.append(command)

    def read(self) -> str:
        self.reads += 1
        if self.stale:
            return self.stale.pop(0)
        raise TimeoutError("VI_ERROR_TMO")

    def close(self) -> None:
        pass


def _timed(backend: _TimedBackend, sleep: Callable[[float], None] = _Sleeps()) -> SHA852A:
    sa = SHA852A(MockEnvironment(), "sa", "10.0.0.2", backend=backend, sleep=sleep)
    sa.set_timeout(Q(10, "s"))
    return sa


def test_opc_timeout_covers_the_sweeps_and_is_restored() -> None:
    backend = _TimedBackend({":SWE:TIME?": "2.0", "*OPC?": "1"})
    sa = _timed(backend)
    sa.single_sweep(sweeps=4)
    opc = [t for q, t in backend.queries if q == "*OPC?"]
    # Each sweep: :SWE:TIME? (the sampling time only, §3.3.3) x 1.25 + 0.2 s of overhead.
    assert opc == [pytest.approx((4 * (2.0 * 1.25 + 0.2) + 3.0) * 1000)]
    assert backend.timeout == pytest.approx(10000.0)


def test_a_backends_own_timeout_is_restored() -> None:
    backend = _TimedBackend({":SWE:TIME?": "2.0", "*OPC?": "1"})
    backend.timeout = 5000.0
    sa = SHA852A(MockEnvironment(), "sa", "10.0.0.2", backend=backend)
    sa.single_sweep()
    sa.single_sweep()
    assert backend.timeout == pytest.approx(5000.0)


def test_explicit_single_sweep_timeout_is_used() -> None:
    backend = _TimedBackend({":SWE:TIME?": "2.0", "*OPC?": "1"})
    sa = _timed(backend)
    sa.single_sweep(timeout=Q(90, "s"))
    assert [t for q, t in backend.queries if q == "*OPC?"] == [pytest.approx(90000.0)]


def test_a_timed_out_opc_is_resynchronised_not_slept_over() -> None:
    # The late "1" and then the identity come back: the sweep is over, no sleep.
    sleeps = _Sleeps()
    backend = _TimedBackend({":SWE:TIME?": "0.2", "*OPC?": TimeoutError("VI_ERROR_TMO")}, stale=["1", _IDN])
    sa = _timed(backend, sleep=sleeps)
    sa.single_sweep()
    assert backend.writes[-1] == "*IDN?"
    assert backend.reads == 2
    assert sleeps.calls == []
    assert backend.timeout == pytest.approx(10000.0)


def test_an_opc_that_never_answers_sleeps_once_the_session_is_in_step() -> None:
    # The SSA3015X Plus quirk: no "1" at all, but the analyzer answers the
    # identity — in step, so the expected sweep time is slept instead.
    sleeps = _Sleeps()
    backend = _TimedBackend({":SWE:TIME?": "0.2", "*OPC?": TimeoutError("VI_ERROR_TMO")}, stale=[_IDN])
    sa = _timed(backend, sleep=sleeps)
    sa.single_sweep()
    assert sleeps.calls == [pytest.approx((0.2 * 1.25 + 0.2) + 0.5)]


def test_a_session_that_cannot_be_resynchronised_raises() -> None:
    sleeps = _Sleeps()
    backend = _TimedBackend({":SWE:TIME?": "0.2", "*OPC?": TimeoutError("VI_ERROR_TMO")})
    sa = _timed(backend, sleep=sleeps)
    with pytest.raises(TimeoutError, match="resynchronise"):
        sa.single_sweep()
    assert sleeps.calls == []  # never fall through to reading a marker
    assert backend.writes.count("*IDN?") == 1
    with pytest.raises(TimeoutError):
        sa.query(":CALC:MARK1:Y?")  # still out of step: no query goes out
    assert backend.writes.count("*IDN?") == 1  # the owed identity is waited for, not asked again
    assert [q for q, _ in backend.queries].count(":CALC:MARK1:Y?") == 0
    backend.stale = ["1", _IDN]  # it finally arrives
    backend.replies[":CALC:MARK1:Y?"] = "-30.5"
    assert sa.query(":CALC:MARK1:Y?") == "-30.5"


def test_an_interrupted_query_marks_the_session_out_of_step() -> None:
    # Its reply may still come; the next query resynchronises before it asks.
    backend = _TimedBackend({":SWE:TIME?": KeyboardInterrupt()}, stale=[_IDN])
    sa = _timed(backend)
    with pytest.raises(KeyboardInterrupt):
        sa.sweep_seconds()
    backend.replies[":SWE:TIME?"] = "0.5"
    assert sa.sweep_seconds() == 0.5
    assert backend.writes == ["*IDN?"] and backend.reads == 1


def test_wait_for_instrument_is_one_opc_query() -> None:
    sa, be = _sa({"*OPC?": ""})
    with pytest.raises(TimeoutError):
        sa.wait_for_instrument(Q(5, "s"))
    assert be.queries == ["*OPC?"]


# -- measure_cw ----------------------------------------------------------------------------

_CW_SETUP = [
    ":UNIT:POW DBM",
    ":CALC:MARK:PEAK:THR:STAT OFF",
    ":CALC:MARK:PEAK:EXC:STAT OFF",
    *[f":CORR:CSET{n} 0" for n in range(1, 9)],
    ":BWID:AUTO OFF",
    ":BWID:VID:AUTO OFF",
    ":TRAC1:DISP ACTIve",
    ":CALC:MARK1:STAT ON",
    ":CALC:MARK1:MODE POSition",
    ":CALC:MARK1:TRAC 1",
    ":CALC:MARK1:FUNC OFF",
]
_SWEEP = [":INIT:CONT OFF", ":INIT:IMM", ":CALC:MARK1:MAX"]
#: The one-time setup's checks: the active measurement, then the reference level offset.
_CW_SETUP_QUERIES = [":INST?", ":INST:MEAS?", ":DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS?"]


def test_measure_cw_first_call_sends_everything() -> None:
    sa, be = _sa({":CALC:MARK1:Y?": "-30.5"})
    level = sa.measure_cw(Q(1575.42, "MHz"))
    assert level == Q(-30.5, "dBm")
    assert be.writes == _CW_SETUP + [
        ":FREQ:CENT 1575420000.0",
        ":FREQ:SPAN 5000.0",
        ":BWID 1000.0",
        ":BWID:VID 1000.0",
        ":TRAC1:TYPE WRITe",
    ] + _SWEEP
    assert be.queries == _CW_SETUP_QUERIES + [":SWE:TIME?", "*OPC?", ":CALC:MARK1:Y?"]


def test_measure_cw_sends_only_what_changed() -> None:
    sa, be = _sa({":CALC:MARK1:Y?": "-30.5"})
    sa.measure_cw(Q(1575.42, "MHz"))
    be.writes.clear()
    be.queries.clear()

    sa.measure_cw(Q(1575.42, "MHz"))  # nothing changed: just a sweep and a read
    assert be.writes == _SWEEP
    assert be.queries == ["*OPC?", ":CALC:MARK1:Y?"]  # sweep time reused

    be.writes.clear()
    be.queries.clear()
    sa.measure_cw(Q(1227.6, "MHz"))  # a new frequency: one command, sweep time re-read
    assert be.writes == [":FREQ:CENT 1227600000.0"] + _SWEEP
    assert be.queries == [":SWE:TIME?", "*OPC?", ":CALC:MARK1:Y?"]

    be.writes.clear()
    sa.measure_cw(Q(1227.6, "MHz"), span=Q(20, "kHz"), vbw=Q(3, "kHz"))
    assert be.writes == [":FREQ:SPAN 20000.0", ":BWID:VID 3000.0"] + _SWEEP


def test_measure_cw_averages_on_trace_one() -> None:
    sa, be = _sa({":CALC:MARK1:Y?": "-30.5"})
    sa.measure_cw(Q(1575.42, "MHz"))
    be.writes.clear()
    sa.measure_cw(Q(1575.42, "MHz"), averages=4)
    assert be.writes == [
        ":TRAC1:TYPE AVERage",
        ":AVER:TRAC1:COUN 4",
        ":INIT:CONT OFF",
        ":AVER:TRAC1:CLE",
        ":INIT:IMM",
        ":CALC:MARK1:MAX",
    ]
    be.writes.clear()
    sa.measure_cw(Q(1575.42, "MHz"), averages=1)
    assert be.writes == [":TRAC1:TYPE WRITe"] + _SWEEP


def test_any_other_write_makes_measure_cw_send_everything_again() -> None:
    sa, be = _sa({":CALC:MARK1:Y?": "-30.5"})
    sa.measure_cw(Q(1575.42, "MHz"))
    sa.amplitude.set_attenuation(Q(20, "dB"))  # a menu write in between
    be.writes.clear()
    sa.measure_cw(Q(1575.42, "MHz"))
    assert be.writes[: len(_CW_SETUP)] == _CW_SETUP
    assert ":FREQ:CENT 1575420000.0" in be.writes
    sa.forget_cw_settings()
    be.writes.clear()
    sa.measure_cw(Q(1575.42, "MHz"))
    assert be.writes[: len(_CW_SETUP)] == _CW_SETUP


def test_measure_cw_validates_before_sweeping() -> None:
    sa, be = _sa()
    with pytest.raises(ValueError):
        sa.measure_cw(Q(1575.42, "MHz"), averages=0)
    with pytest.raises(ValueError):
        sa.measure_cw(Q(1575.42, "MHz"), rbw=Q(10, "MHz"))
    assert ":INIT:IMM" not in be.writes


# -- channel power ---------------------------------------------------------------------------

_CHP_SETUP = [
    ":INST:MEAS CHPower",
    ":UNIT:CHP:POW:PSD DBMHZ",
    ":FREQ:CENT 1575420000.0",
    ":CHP:BWID:INT 2046000.0",
    ":CHP:FREQ:SPAN 3069000.0",
]


def test_channel_power_with_the_sha_read_form() -> None:
    sa, be = _sa({":CHP:MEAS:CHP?": "-30.0,-93.1"})
    power, density = sa.measurement.channel_power(Q(1575.42, "MHz"), Q(2.046, "MHz"))
    assert be.writes == _CHP_SETUP + [":INIT:CONT OFF", ":INIT:IMM", ":INST:MEAS SA"]
    assert be.queries == [":SWE:TIME?", "*OPC?", ":CHP:MEAS:CHP?"]
    assert power == Q(-30.0, "dBm")
    assert dbm_per_hz(density) == pytest.approx(-93.1)


def test_channel_power_falls_back_to_the_ssa_read_form() -> None:
    sa, be = _sa({":MEAS:CHP?": "-31.5"})  # the SHA form answers nothing
    power, density = sa.measurement.channel_power(Q(1575.42, "MHz"), Q(2.046, "MHz"))
    assert be.queries[-2:] == [":CHP:MEAS:CHP?", ":MEAS:CHP?"]
    assert power == Q(-31.5, "dBm")
    assert dbm_per_hz(density) == pytest.approx(-31.5 - 10 * math.log10(2.046e6))
    assert be.writes[-1] == ":INST:MEAS SA"


def test_channel_power_falls_back_when_the_sha_form_raises() -> None:
    def responder(command: str) -> str:
        if command == ":CHP:MEAS:CHP?":
            raise TimeoutError("VI_ERROR_TMO")
        return {"*OPC?": "1", ":SWE:TIME?": "0.1", ":MEAS:CHP?": "-29.0,-92.0"}.get(command, "")

    sa, be = mock_instrument(SHA852A, responses=responder)
    power, density = sa.measurement.channel_power(Q(1575.42, "MHz"), Q(2.046, "MHz"))
    assert power == Q(-29.0, "dBm")
    assert dbm_per_hz(density) == pytest.approx(-92.0)


def test_channel_power_skips_a_non_numeric_reply() -> None:
    sa, be = _sa({":CHP:MEAS:CHP?": "--", ":MEAS:CHP?": "-31.5,-94.6"})
    power, _ = sa.measurement.channel_power(Q(1575.42, "MHz"), Q(2.046, "MHz"))
    assert power == Q(-31.5, "dBm")


def test_channel_power_restores_sa_when_nothing_answers() -> None:
    sa, be = _sa()
    with pytest.raises(RuntimeError, match="channel-power"):
        sa.measurement.channel_power(Q(1575.42, "MHz"), Q(2.046, "MHz"))
    assert be.writes[-1] == ":INST:MEAS SA"


def test_channel_power_restores_sa_when_the_sweep_fails() -> None:
    def responder(command: str) -> str:
        if command == ":SWE:TIME?":
            raise ConnectionError("socket closed")
        return ""

    sa, be = mock_instrument(SHA852A, responses=responder)
    with pytest.raises(ConnectionError):
        sa.measurement.channel_power(Q(1575.42, "MHz"), Q(2.046, "MHz"))
    assert be.writes[-1] == ":INST:MEAS SA"


def test_channel_power_span_rbw_and_averages() -> None:
    sa, be = _sa({":CHP:MEAS:CHP?": "-30.0,-93.1"})
    sa.measurement.channel_power(
        Q(1575.42, "MHz"), Q(2.046, "MHz"), span=Q(4, "MHz"), averages=10, rbw=Q(10, "kHz")
    )
    assert be.writes == [
        ":INST:MEAS CHPower",
        ":UNIT:CHP:POW:PSD DBMHZ",
        ":FREQ:CENT 1575420000.0",
        ":CHP:BWID:INT 2046000.0",
        ":CHP:FREQ:SPAN 4000000.0",
        ":CHP:BAND 10000.0",
        ":CHP:AVER:TCON REPE",
        ":TRAC1:TYPE AVERage",
        ":AVER:TRAC1:COUN 10",
        ":INIT:CONT OFF",
        ":AVER:TRAC1:CLE",
        ":INIT:IMM",
        ":INST:MEAS SA",
    ]


def test_channel_power_refuses_a_span_below_the_bandwidth() -> None:
    sa, be = _sa()
    with pytest.raises(ValueError):
        sa.measurement.channel_power(Q(1575.42, "MHz"), Q(2.046, "MHz"), span=Q(1, "MHz"))
    with pytest.raises(ValueError):
        sa.measurement.channel_power(Q(1575.42, "MHz"), Q(0, "Hz"))
    assert be.writes == []


def test_measurement_select() -> None:
    sa, be = _sa({":INST:MEAS?": "CHP"})
    sa.measurement.select("CHPower")
    sa.measurement.select("SA")
    sa.measurement.set_mode("SA")
    assert be.writes == [":INST:MEAS CHPower", ":INST:MEAS SA", ":INST SA"]
    assert sa.measurement.get_selected() == "CHP"


# -- typing ----------------------------------------------------------------------------------

def test_public_api_type_hints_resolve() -> None:
    # Every public method and function of the package has annotations that
    # resolve at runtime (constructors take TYPE_CHECKING-only names and are
    # left to mypy).
    checked = 0
    for export in siglent.__all__:
        obj = getattr(siglent, export)
        functions: list[Callable[..., Any]] = []
        if inspect.isclass(obj):
            functions = [
                member
                for name, member in inspect.getmembers(obj, inspect.isfunction)
                if not name.startswith("_") and member.__module__.startswith(siglent.__name__)
            ]
        elif inspect.isfunction(obj):
            functions = [obj]
        for function in functions:
            hints = typing.get_type_hints(function)
            assert "return" in hints, f"{export}.{function.__name__} has no return annotation"
            checked += 1
    assert checked > 50
