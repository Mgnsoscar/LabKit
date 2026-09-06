"""The R&S FSV3007 driver, exercised through the scriptable mock backend."""

from __future__ import annotations

import numpy as np
import pytest

from labkit.instruments import FSV3007, mock_instrument
from labkit.instruments.mock import MockBackend
from labkit.units import DimensionalityError, quantity as Q


def _sa() -> tuple[FSV3007, MockBackend]:
    return mock_instrument(FSV3007, responses={"*IDN?": "R&S,FSV3007,1,2"})


def test_build_address() -> None:
    sa, _ = _sa()
    assert sa._address == "TCPIP::0.0.0.0::INSTR"


def test_id_query() -> None:
    sa, _ = _sa()
    assert sa.get_id() == "R&S,FSV3007,1,2"


def test_frequency_commands_convert_to_hz() -> None:
    sa, be = _sa()
    sa.frequency.set_center(Q(1, "GHz"))
    sa.frequency.set_span(Q(10, "MHz"))
    sa.frequency.set_start(Q(950, "MHz"))
    sa.frequency.set_stop(Q(1.05, "GHz"))
    assert be.writes == [
        "FREQ:CENT 1000000000.0",
        "FREQ:SPAN 10000000.0",
        "FREQ:STAR 950000000.0",
        "FREQ:STOP 1050000000.0",
    ]


def test_frequency_rejects_non_frequency_quantity() -> None:
    sa, _ = _sa()
    with pytest.raises(DimensionalityError):
        sa.frequency.set_center(Q(1, "dBm"))


def test_frequency_getter_parses_response() -> None:
    sa, be = _sa()
    be.on("FREQ:CENT?", "1.5e9")
    assert sa.frequency.get_center() == Q(1.5, "GHz")


def test_bandwidth_commands() -> None:
    sa, be = _sa()
    sa.bandwidth.set_rbw(Q(100, "kHz"))
    sa.bandwidth.set_vbw(Q(30, "kHz"))
    sa.bandwidth.set_rbw_auto(True)
    sa.bandwidth.set_filter_type("RRC")
    assert be.writes == [
        "BAND 100000.0",
        "BAND:VID 30000.0",
        "BAND:AUTO ON",
        "BAND:TYPE RRC",
    ]


def test_sweep_commands() -> None:
    sa, be = _sa()
    sa.sweep.set_points(1001)
    sa.sweep.set_count(10)
    sa.sweep.set_time(Q(50, "ms"))
    sa.sweep.set_continuous(False)
    assert be.writes == ["SWE:POIN 1001", "SWE:COUN 10", "SWE:TIME 0.05", "INIT:CONT OFF"]


def test_amplitude_commands() -> None:
    sa, be = _sa()
    sa.amplitude.set_ref_level(Q(-10, "dBm"))
    sa.amplitude.set_attenuation(Q(20, "dB"))
    sa.amplitude.set_attenuation_auto(False)
    sa.amplitude.set_unit("DBM")
    sa.amplitude.set_preamp(True)
    assert be.writes == [
        "DISP:TRAC:Y:SCAL:RLEV -10.0",
        "INP:ATT 20.0",
        "INP:ATT:AUTO OFF",
        "CALC:UNIT:POW DBM",
        "INP:GAIN:STAT ON",
    ]


def test_trace_mode_and_detector() -> None:
    sa, be = _sa()
    sa.trace.set_mode("MAXHOLD", trace=2)
    sa.trace.set_detector("RMS", trace=2)
    assert be.writes == ["DISP:TRAC2:MODE MAXH", "DET2 RMS"]


def test_trace_data_roundtrip() -> None:
    sa, be = _sa()
    be.on("FREQ:STAR?", "9.9e8").on("FREQ:STOP?", "1.01e9").on("SWE:POIN?", "3")
    be.on("TRAC:DATA? TRACE1", "-50.0,-30.0,-55.0")
    x, y = sa.trace.get_data(1)
    np.testing.assert_allclose(x.to("MHz").magnitude, [990.0, 1000.0, 1010.0])
    np.testing.assert_allclose(y.magnitude, [-50.0, -30.0, -55.0])
    assert str(y.units) == "dBm"


def test_marker_peak_and_reads() -> None:
    sa, be = _sa()
    be.on("CALC:MARK1:X?", "1.0e9").on("CALC:MARK1:Y?", "-30.0")
    marker = sa.marker(1, enable=True)
    marker.peak_search()
    assert "CALC:MARK1:STAT ON" in be.writes
    assert "CALC:MARK1:MAX" in be.writes
    assert marker.get_x() == Q(1, "GHz")
    assert marker.get_y() == Q(-30, "dBm")


def test_marker_to_center_reads_then_sets() -> None:
    sa, be = _sa()
    be.on("CALC:MARK1:X?", "2.0e9")
    sa.marker(1).to_center()
    assert "FREQ:CENT 2000000000.0" in be.writes


def test_measure_trace_runs_single_and_returns_data() -> None:
    sa, be = _sa()
    be.on("*OPC?", "1")
    be.on("FREQ:STAR?", "1e9").on("FREQ:STOP?", "1e9").on("SWE:POIN?", "1")
    be.on("TRAC:DATA? TRACE1", "-40.0")
    x, y = sa.measure_trace(1)
    assert "INIT:CONT OFF" in be.writes
    assert "INIT" in be.writes
    assert y.magnitude[0] == pytest.approx(-40.0)


def test_shutdown_restores_continuous_sweep() -> None:
    sa, be = _sa()
    sa.close()
    assert "INIT:CONT ON" in be.writes
