"""The R&S ZNLE18 VNA driver, exercised through the scriptable mock backend.

Asserts the exact SCPI strings the driver emits (all verified against the R&S
ZNL/ZNLE User Manual, 1178.5966.02 issue 23) and the quantity conversions,
catalog parsing, and formatted/complex/stimulus data round-trips.
"""

from __future__ import annotations

import numpy as np
import pytest

from labkit.instruments import ZNLE18, mock_instrument
from labkit.instruments.mock import MockBackend
from labkit.units import DimensionalityError, quantity as Q

_IDN = "Rohde-Schwarz,ZNLE18-2Port,1323.0012K70/100123,1.80"


def _vna() -> tuple[ZNLE18, MockBackend]:
    return mock_instrument(ZNLE18, responses={"*IDN?": _IDN})


# -- identity / connection ---------------------------------------------------

def test_build_address_is_visa_instr() -> None:
    vna, _ = _vna()
    assert vna._address == "TCPIP::0.0.0.0::INSTR"


def test_id_query() -> None:
    vna, _ = _vna()
    assert vna.get_id() == _IDN


def test_model_identity() -> None:
    vna, _ = _vna()
    assert vna.frequency_range == (Q(1, "MHz"), Q(18, "GHz"))
    assert vna.port_count == 2


# -- frequency ---------------------------------------------------------------

def test_frequency_commands_convert_to_hz() -> None:
    vna, be = _vna()
    vna.frequency.set_start(Q(1, "GHz"))
    vna.frequency.set_stop(Q(18, "GHz"))
    vna.frequency.set_center(Q(9, "GHz"))
    vna.frequency.set_span(Q(2, "GHz"))
    vna.frequency.set_cw(Q(2.4, "GHz"))
    assert be.writes == [
        "SENS1:FREQ:STAR 1000000000.0",
        "SENS1:FREQ:STOP 18000000000.0",
        "SENS1:FREQ:CENT 9000000000.0",
        "SENS1:FREQ:SPAN 2000000000.0",
        "SENS1:FREQ:CW 2400000000.0",
    ]


def test_frequency_getter_parses_response() -> None:
    vna, be = _vna()
    be.on("SENS1:FREQ:STAR?", "1.5e9")
    assert vna.frequency.get_start() == Q(1.5, "GHz")


def test_frequency_rejects_non_frequency() -> None:
    vna, _ = _vna()
    with pytest.raises(DimensionalityError):
        vna.frequency.set_start(Q(1, "dBm"))


def test_frequency_out_of_range_rejected() -> None:
    vna, _ = _vna()
    with pytest.raises(ValueError):
        vna.frequency.set_stop(Q(20, "GHz"))
    with pytest.raises(ValueError):
        vna.frequency.set_start(Q(100, "kHz"))  # below 1 MHz


def test_frequency_channel_suffix() -> None:
    vna, be = _vna()
    vna.frequency.set_start(Q(1, "GHz"), channel=2)
    assert be.writes == ["SENS2:FREQ:STAR 1000000000.0"]


# -- channel -----------------------------------------------------------------

def test_channel_commands() -> None:
    vna, be = _vna()
    vna.channel.create(2)
    vna.channel.set_name(2, "Amp")
    vna.channel.delete(3)
    assert be.writes == ["CONF:CHAN2 ON", "CONF:CHAN2:NAME 'Amp'", "CONF:CHAN3 OFF"]


def test_channel_catalog_parses() -> None:
    vna, be = _vna()
    be.on("CONF:CHAN:CAT?", "'1,Ch1,2,Amp'")
    assert vna.channel.catalog() == [("1", "Ch1"), ("2", "Amp")]


# -- trace -------------------------------------------------------------------

def test_trace_create_and_select() -> None:
    vna, be = _vna()
    vna.trace.create("Trc1", "S21")
    vna.trace.select("Trc1")
    vna.trace.set_measured_parameter("Trc1", "S11")
    vna.trace.delete("Trc1")
    vna.trace.delete_all()
    assert be.writes == [
        "CALC1:PAR:SDEF 'Trc1','S21'",
        "CALC1:PAR:SEL 'Trc1'",
        "CALC1:PAR:MEAS 'Trc1','S11'",
        "CALC1:PAR:DEL 'Trc1'",
        "CALC:PAR:DEL:ALL",
    ]


def test_trace_catalog_parses() -> None:
    vna, be = _vna()
    be.on("CALC1:PAR:CAT?", "'Trc1,S11,Trc2,S21'")
    assert vna.trace.catalog() == [("Trc1", "S11"), ("Trc2", "S21")]


def test_trace_format() -> None:
    vna, be = _vna()
    vna.trace.set_format("MLOG")
    vna.trace.set_format("PHASE")
    vna.trace.set_format("SMITH")
    assert be.writes == ["CALC1:FORM MLOG", "CALC1:FORM PHAS", "CALC1:FORM SMIT"]


def test_trace_stimulus_roundtrip() -> None:
    vna, be = _vna()
    be.on("CALC1:DATA:STIM?", "1e9,2e9,3e9")
    stim = vna.trace.get_stimulus()
    np.testing.assert_allclose(stim.to("GHz").magnitude, [1.0, 2.0, 3.0])
    assert "FORM ASC" in be.writes


def test_trace_formatted_data_roundtrip() -> None:
    vna, be = _vna()
    be.on("CALC1:DATA:STIM?", "1e9,2e9,3e9").on("CALC1:DATA? FDAT", "-3.0,-3.1,-3.2")
    freqs, values = vna.trace.get_formatted_data()
    np.testing.assert_allclose(freqs.to("GHz").magnitude, [1.0, 2.0, 3.0])
    np.testing.assert_allclose(values, [-3.0, -3.1, -3.2])


def test_trace_complex_data_roundtrip() -> None:
    vna, be = _vna()
    be.on("CALC1:DATA:STIM?", "1e9,2e9").on("CALC1:DATA? SDAT", "1.0,0.5,2.0,-0.5")
    freqs, values = vna.trace.get_complex_data()
    np.testing.assert_allclose(freqs.to("GHz").magnitude, [1.0, 2.0])
    np.testing.assert_allclose(values, [1.0 + 0.5j, 2.0 - 0.5j])


# -- sweep -------------------------------------------------------------------

def test_sweep_commands() -> None:
    vna, be = _vna()
    vna.sweep.set_points(1001)
    vna.sweep.set_type("LINEAR")
    vna.sweep.set_type("LOGARITHMIC")
    vna.sweep.set_time(Q(50, "ms"))
    vna.sweep.set_time_auto(True)
    vna.sweep.set_count(4)
    vna.sweep.set_dwell(Q(1, "ms"))
    vna.sweep.set_continuous(False)
    vna.sweep.set_trigger_source("EXTERNAL")
    assert be.writes == [
        "SENS1:SWE:POIN 1001",
        "SENS1:SWE:TYPE LIN",
        "SENS1:SWE:TYPE LOG",
        "SENS1:SWE:TIME 0.05",
        "SENS1:SWE:TIME:AUTO ON",
        "SENS1:SWE:COUN 4",
        "SENS1:SWE:DWEL 0.001",
        "INIT1:CONT OFF",
        "TRIG1:SEQ:SOUR EXT",
    ]


def test_sweep_getters() -> None:
    vna, be = _vna()
    be.on("SENS1:SWE:POIN?", "1001").on("INIT1:CONT?", "0")
    assert vna.sweep.get_points() == 1001
    assert vna.sweep.is_continuous() is False


# -- bandwidth ---------------------------------------------------------------

def test_if_bandwidth() -> None:
    vna, be = _vna()
    vna.bandwidth.set_if_bandwidth(Q(10, "kHz"))
    be.on("SENS1:BAND:RES?", "1500")
    assert be.writes == ["SENS1:BAND:RES 10000.0"]
    assert vna.bandwidth.get_if_bandwidth() == Q(1.5, "kHz")


# -- power -------------------------------------------------------------------

def test_power_commands() -> None:
    vna, be = _vna()
    vna.power.set_power(Q(-10, "dBm"))
    vna.power.set_power_start(Q(-20, "dBm"))
    vna.power.set_power_stop(Q(0, "dBm"))
    vna.power.set_output(True)
    vna.power.set_output(False)
    assert be.writes == [
        "SOUR1:POW -10.0",
        "SOUR1:POW:STAR -20.0",
        "SOUR1:POW:STOP 0.0",
        "OUTP ON",
        "OUTP OFF",
    ]


def test_power_accepts_linear_units() -> None:
    vna, be = _vna()
    vna.power.set_power(Q(1, "mW"))  # 0 dBm
    (written,) = be.writes
    assert float(written.split()[1]) == pytest.approx(0.0, abs=1e-6)


# -- average -----------------------------------------------------------------

def test_average_commands() -> None:
    vna, be = _vna()
    vna.average.set_state(True)
    vna.average.set_count(16)
    vna.average.set_mode("FLATTEN")
    vna.average.clear()
    assert be.writes == [
        "SENS1:AVER ON",
        "SENS1:AVER:COUN 16",
        "SENS1:AVER:MODE FLAT",
        "SENS1:AVER:CLE",
    ]


# -- markers -----------------------------------------------------------------

def test_marker_create_and_search() -> None:
    vna, be = _vna()
    be.on("CALC1:MARK1:X?", "2.0e9").on("CALC1:MARK1:Y?", "-3.5")
    marker = vna.marker(1, enable=True)
    marker.set_x(Q(2, "GHz"))
    marker.search("MAX")
    marker.min_search()
    marker.set_mode("FIXED")
    marker.all_off()
    assert "CALC1:MARK1:STAT ON" in be.writes
    assert "CALC1:MARK1:X 2000000000.0" in be.writes
    assert "CALC1:MARK1:FUNC:EXEC MAX" in be.writes
    assert "CALC1:MARK1:FUNC:EXEC MIN" in be.writes
    assert "CALC1:MARK1:TYPE FIX" in be.writes
    assert "CALC1:MARK:AOFF" in be.writes
    assert marker.get_x() == Q(2, "GHz")
    assert marker.get_y() == pytest.approx(-3.5)


def test_marker_search_result() -> None:
    vna, be = _vna()
    be.on("CALC1:MARK1:FUNC:RES?", "-3.5,2.0e9")
    response, stimulus = vna.marker(1).get_search_result()
    assert response == pytest.approx(-3.5)
    assert stimulus == pytest.approx(2.0e9)


# -- calibration -------------------------------------------------------------

def test_calibration_commands() -> None:
    vna, be = _vna()
    vna.calibration.set_correction_enabled(True)
    vna.calibration.save(1, "Calgroup1.cal")
    vna.calibration.load(2, "Calgroup1.cal")
    be.on("SENS1:CORR:STAT?", "1")
    assert be.writes == [
        "SENS1:CORR:STAT ON",
        "MMEM:STOR:CORR 1,'Calgroup1.cal'",
        "MMEM:LOAD:CORR 2,'Calgroup1.cal'",
    ]
    assert vna.calibration.is_correction_enabled() is True


# -- display -----------------------------------------------------------------

def test_display_commands() -> None:
    vna, be = _vna()
    vna.display.set_window_state(1, True)
    vna.display.feed_trace(1, 1, "Trc1")
    vna.display.autoscale(1, 1)
    vna.display.set_reference_level(1, -20.0)
    vna.display.set_update(True)
    assert be.writes == [
        "DISP:WIND1:STAT ON",
        "DISP:WIND1:TRAC1:FEED 'Trc1'",
        "DISP:WIND1:TRAC1:Y:SCAL:AUTO ONCE",
        "DISP:WIND1:TRAC1:Y:SCAL:RLEV -20.0",
        "SYST:DISP:UPD ON",
    ]


# -- measurement control -----------------------------------------------------

def test_trigger_and_stop() -> None:
    vna, be = _vna()
    vna.trigger()
    vna.stop_sweep()
    assert be.writes == ["INIT1:IMM", "INIT1:STOP"]


def test_measure_runs_single_and_returns_complex() -> None:
    vna, be = _vna()
    be.on("*OPC?", "1")
    be.on("CALC1:DATA:STIM?", "1e9,2e9").on("CALC1:DATA? SDAT", "1.0,0.0,0.0,1.0")
    freqs, values = vna.measure()
    assert "INIT1:CONT OFF" in be.writes
    assert "INIT1:IMM" in be.writes
    np.testing.assert_allclose(freqs.to("GHz").magnitude, [1.0, 2.0])
    np.testing.assert_allclose(values, [1.0 + 0j, 0.0 + 1j])


# -- failsafe shutdown -------------------------------------------------------

def test_shutdown_switches_rf_output_off() -> None:
    vna, be = _vna()
    vna.close()
    assert "OUTP OFF" in be.writes
