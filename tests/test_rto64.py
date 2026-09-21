"""The R&S RTO64 oscilloscope driver, exercised through the scriptable mock backend.

Asserts the exact SCPI strings the driver emits (verified against the R&S RTO6
User Manual, 1801.6687.02, chapter 24) and the quantity conversions, the
waveform header/data round trip, and the measurement result units.
"""

from __future__ import annotations

import numpy as np
import pytest

from labkit.instruments import RTO64, mock_instrument
from labkit.instruments.drivers.rohde_schwarz.oscilloscope import WaveformHeader
from labkit.instruments.mock import MockBackend
from labkit.units import DimensionalityError, quantity as Q

_IDN = "Rohde&Schwarz,RTO,1801.6687k64/123456,5.20.1.0"


def _scope() -> tuple[RTO64, MockBackend]:
    return mock_instrument(RTO64, responses={"*IDN?": _IDN, "*OPC?": "1"})


# -- identity / connection -----------------------------------------------------

def test_build_address_and_identity() -> None:
    scope, _ = _scope()
    assert scope._address == "TCPIP::0.0.0.0::INSTR"
    assert scope.get_id() == _IDN
    assert scope.channel_count == 4 and len(scope.channels) == 4
    assert scope.bandwidth == Q(600, "MHz") and scope.max_sample_rate == Q(20, "GHz")


def test_channel_numbers_are_checked() -> None:
    scope, _ = _scope()
    with pytest.raises(ValueError):
        scope.channel(5)
    with pytest.raises(ValueError):
        scope.waveform.get_data(0)
    with pytest.raises(ValueError):
        scope.math.enable(9)


# -- channel ----------------------------------------------------------------------

def test_channel_vertical_and_input_commands() -> None:
    scope, be = _scope()
    ch = scope.channel(2)
    ch.enable(True)
    ch.set_scale(Q(100, "mV"))
    ch.set_range(Q(1, "V"))
    ch.set_offset(Q(-250, "mV"))
    ch.set_position(1.5)
    ch.set_coupling("DC_1M")
    ch.set_bandwidth_limit("20MHz")
    ch.set_invert(True)
    ch.set_impedance(50)
    ch.set_probe_attenuation(10)
    ch.set_arithmetics("AVERAGE")
    assert be.writes == [
        "CHAN2:STAT ON",
        "CHAN2:SCAL 0.1",
        "CHAN2:RANG 1.0",
        "CHAN2:OFFS -0.25",
        "CHAN2:POS 1.5",
        "CHAN2:COUP DCL",
        "CHAN2:BAND B20",
        "CHAN2:INV ON",
        "CHAN2:IMP 50.0",
        "PROB2:SET:ATT:MODE MAN",
        "PROB2:SET:ATT:MAN 10.0",
        "CHAN2:WAV1:ARIT AVER",
    ]
    assert ch.source == "C2W1"


def test_channel_getters_and_checks() -> None:
    scope, be = _scope()
    ch = scope.channel(1)
    be.on("CHAN1:SCAL?", "0.05").on("CHAN1:COUP?", "DCL").on("CHAN1:OVER?", "1").on("CHAN1:STAT?", "ON")
    assert ch.get_scale() == Q(0.05, "V")
    assert ch.get_coupling() == "DC_1M"
    assert ch.is_overloaded() is True
    assert ch.is_enabled() is True
    with pytest.raises(ValueError):
        ch.set_position(6)
    with pytest.raises(DimensionalityError):
        ch.set_scale(Q(1, "Hz"))


# -- timebase / acquisition ------------------------------------------------------

def test_timebase_commands_convert_to_seconds() -> None:
    scope, be = _scope()
    scope.timebase.set_scale(Q(20, "ns"))
    scope.timebase.set_range(Q(1, "us"))
    scope.timebase.set_position(Q(-50, "ns"))
    scope.timebase.set_reference(10)
    assert be.writes == ["TIM:SCAL 2e-08", "TIM:RANG 1e-06", "TIM:HOR:POS -5e-08", "TIM:REF 10.0"]
    be.on("TIM:SCAL?", "1e-9").on("TIM:DIV?", "10")
    assert scope.timebase.get_scale().to("ns").magnitude == pytest.approx(1.0)
    assert scope.timebase.get_divisions() == 10
    with pytest.raises(ValueError):
        scope.timebase.set_reference(120)


def test_acquisition_commands() -> None:
    scope, be = _scope()
    scope.acquisition.set_sample_rate(Q(10, "GHz"))
    scope.acquisition.set_record_length(10_000)
    scope.acquisition.set_resolution(Q(100, "ps"))
    scope.acquisition.set_points_mode("RECORD_LENGTH")
    scope.acquisition.set_count(64)
    scope.acquisition.set_interpolation("SINX")
    assert be.writes == [
        "ACQ:SRAT 10000000000.0",
        "ACQ:POIN 10000",
        "ACQ:RES 1e-10",
        "ACQ:POIN:AUTO RECL",
        "ACQ:COUN 64",
        "ACQ:INT SINX",
    ]
    be.on("ACQ:SRAT?", "2e9")
    assert scope.acquisition.get_sample_rate() == Q(2, "GHz")
    assert scope.acquisition.sample_interval().to("ns").magnitude == pytest.approx(0.5)
    with pytest.raises(ValueError):
        scope.acquisition.set_count(0)


# -- trigger ----------------------------------------------------------------------

def test_edge_trigger_setup_in_one_call() -> None:
    scope, be = _scope()
    scope.trigger.edge("CH3", Q(250, "mV"), slope="NEGATIVE", mode="NORMAL")
    assert be.writes == [
        "TRIG1:SOUR CHAN3",
        "TRIG1:TYPE EDGE",
        "TRIG1:EDGE:SLOP NEG",
        "TRIG1:LEV3 0.25",
        "TRIG1:MODE NORM",
    ]


def test_trigger_external_level_index_holdoff_and_checks() -> None:
    scope, be = _scope()
    scope.trigger.set_source("EXT")
    scope.trigger.set_level(Q(10, "mV"), "EXT")
    scope.trigger.set_holdoff("TIME", time=Q(1, "ms"))
    scope.trigger.find_level()
    scope.trigger.force()
    scope.trigger.set_mode("FREERUN", event=2)
    assert be.writes == [
        "TRIG1:SOUR EXT",
        "TRIG1:LEV5 0.01",
        "TRIG:HOLD:MODE TIME",
        "TRIG:HOLD:TIME 0.001",
        "TRIG1:FIND",
        "TRIG1:FORC",
        "TRIG2:MODE FRE",
    ]
    be.on("TRIG1:LEV2?", "0.5")
    assert scope.trigger.get_level("CH2") == Q(0.5, "V")
    with pytest.raises(ValueError):
        scope.trigger.set_source("CH7")
    with pytest.raises(ValueError):
        scope.trigger.set_mode("AUTO", event=4)


# -- run control and waveform transfer ---------------------------------------------

def test_acquire_reads_header_and_data_into_quantities() -> None:
    scope, be = _scope()
    be.on("CHAN1:WAV1:DATA:HEAD?", "-5e-08,5e-08,5,1")
    be.on("CHAN1:WAV1:DATA?", "0.0,0.5,1.0,0.5,0.0")
    t, v = scope.acquire(1)
    assert be.writes[:1] == ["RUNS"]
    assert "*OPC?" in be.queries
    assert "FORM ASC" in be.writes and "EXP:WAV:INCX OFF" in be.writes
    np.testing.assert_allclose(t.to("ns").magnitude, [-50, -25, 0, 25, 50])
    np.testing.assert_allclose(v.to("V").magnitude, [0.0, 0.5, 1.0, 0.5, 0.0])


def test_envelope_records_come_back_as_min_max_pairs() -> None:
    scope, be = _scope()
    be.on("CHAN2:WAV1:DATA:HEAD?", "0,1e-9,3,2")
    be.on("CHAN2:WAV1:DATA?", "-1,1,-2,2,-3,3")
    t, v = scope.waveform.get_data(2)
    assert v.magnitude.shape == (3, 2)
    np.testing.assert_allclose(v.magnitude[:, 1], [1, 2, 3])
    assert len(t) == 3


def test_length_mismatch_is_an_error() -> None:
    scope, be = _scope()
    be.on("CHAN1:WAV1:DATA:HEAD?", "0,1e-9,4,1")
    be.on("CHAN1:WAV1:DATA?", "1,2,3")
    with pytest.raises(ValueError, match="announced 4 points"):
        scope.waveform.get_data(1)


def test_run_stop_and_shutdown() -> None:
    scope, be = _scope()
    scope.run()
    scope.stop()
    scope.run_single(wait_for_completion=False)
    scope.close()
    assert be.writes == ["RUN", "STOP", "RUNS", "SYST:DISP:UPD ON", "RUN"]


def test_waveform_header_axis() -> None:
    header = WaveformHeader(0.0, 1.0, 5, 1)
    np.testing.assert_allclose(header.x_axis(), [0, 0.25, 0.5, 0.75, 1.0])
    assert WaveformHeader(2.0, 2.0, 1, 1).x_axis().tolist() == [2.0]


# -- measurements ---------------------------------------------------------------------

def test_measure_configures_the_group_and_returns_a_quantity() -> None:
    scope, be = _scope()
    be.on("MEAS1:RES:ACT? FREQ", "600000000.0")
    f = scope.measurement.measure("FREQUENCY", "CH1")
    assert f == Q(600, "MHz")
    assert be.writes == ["MEAS1:ENAB ON", "MEAS1:CAT AMPT", "MEAS1:SOUR C1W1", "MEAS1:MAIN FREQ"]


def test_measurement_units_sources_and_statistics() -> None:
    scope, be = _scope()
    scope.measurement.set_source(2, "CH1", "CH2")
    scope.measurement.set_main(2, "DELAY")
    scope.measurement.add(2, "PHASE")
    scope.measurement.set_statistics(2, True)
    scope.measurement.reset_statistics(2)
    assert be.writes == [
        "MEAS2:SOUR C1W1,C2W1", "MEAS2:MAIN DEL", "MEAS2:ADD PHAS,ON", "MEAS2:STAT ON", "MEAS2:STAT:RES",
    ]
    be.on("MEAS2:RES:AVG? DEL", "2.5e-9").on("MEAS2:RES:ACT? PHAS", "45").on("MEAS2:RES:ACT?", "7")
    be.on("MEAS2:RES:ACT? PULC", "12").on("MEAS2:RES:WFMC?", "100")
    assert scope.measurement.get_average(2, "DELAY").to("ns").magnitude == pytest.approx(2.5)
    assert scope.measurement.get_result(2, "PHASE") == Q(45, "deg")
    assert scope.measurement.get_result(2) == 7.0            # main result, unit unknown -> number
    assert scope.measurement.get_result(2, "PULSE_COUNT") == 12.0
    assert scope.measurement.get_waveform_count(2) == 100
    with pytest.raises(ValueError):
        scope.measurement.enable(11)
    with pytest.raises(ValueError):
        scope.measurement.set_main(1, "NOT_A_MEASUREMENT")  # type: ignore[arg-type]


# -- math / FFT -----------------------------------------------------------------------

def test_fft_setup_and_spectrum_readout() -> None:
    scope, be = _scope()
    scope.math.fft("CH1", center=Q(600, "MHz"), span=Q(100, "MHz"), rbw=Q(100, "kHz"), window="FLATTOP")
    assert be.writes == [
        "CALC:MATH1 'FFTmag(Ch1Wfm1)'",
        "CALC:MATH1:STAT ON",
        "CALC:MATH1:FFT:CFR 600000000.0",
        "CALC:MATH1:FFT:SPAN 100000000.0",
        "CALC:MATH1:FFT:BAND:AUTO OFF",
        "CALC:MATH1:FFT:BAND 100000.0",
        "CALC:MATH1:FFT:WIND:TYPE FLATTOP2",
    ]
    be.on("CALC:MATH1:DATA:HEAD?", "550000000.0,650000000.0,3,1")
    be.on("CALC:MATH1:DATA?", "-60,-10,-60")
    f, s = scope.waveform.get_math_data(1, x_unit="Hz", y_unit="dBm")
    np.testing.assert_allclose(f.to("MHz").magnitude, [550, 600, 650])
    assert s.units == Q(1, "dBm").units
    scope.math.set_fft_rbw(1, None)
    assert be.writes[-1] == "CALC:MATH1:FFT:BAND:AUTO ON"
    be.on("CALC:MATH1:FFT:BAND:ADJ?", "97656.25")
    assert scope.math.get_fft_rbw(1) == Q(97656.25, "Hz")


# -- system -----------------------------------------------------------------------------

def test_system_commands_and_error_queue() -> None:
    scope, be = _scope()
    scope.system.set_display_update(False)
    scope.system.set_reference_source("EXTERNAL")
    scope.system.set_external_reference_frequency(Q(10, "MHz"))
    assert be.writes == ["SYST:DISP:UPD OFF", "SENS:ROSC:SOUR EXT", "SENS:ROSC:EXT:FREQ 10000000.0"]
    be.on("SYST:ERR:ALL?", '0,"No error"')
    assert scope.system.get_all_errors() == []
    be.on("SYST:ERR:ALL?", '-222,"Data out of range",-100,"Command error"')
    assert len(scope.system.get_all_errors()) == 2
