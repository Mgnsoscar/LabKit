"""The Keysight/Agilent N5183A MXG driver, exercised through the mock backend.

Asserts the exact SCPI strings the driver emits (verified against the MXG SCPI
Command Reference, N5180-90004) and the quantity conversions/round-trips.
"""

from __future__ import annotations

import pytest

from labkit.instruments import N5183A, mock_instrument
from labkit.instruments.mock import MockBackend
from labkit.units import DimensionalityError, quantity as Q

_IDN = "Agilent Technologies, N5183A, MY12345678, A.01.80"


def _gen() -> tuple[N5183A, MockBackend]:
    return mock_instrument(N5183A, responses={"*IDN?": _IDN})


# -- identity / connection ---------------------------------------------------

def test_build_address_is_vxi11_instr() -> None:
    gen, _ = _gen()
    assert gen._address == "TCPIP::0.0.0.0::INSTR"


def test_id_query() -> None:
    gen, _ = _gen()
    assert gen.get_id() == _IDN


# -- frequency ---------------------------------------------------------------

def test_frequency_is_sent_in_hertz() -> None:
    gen, be = _gen()
    gen.frequency.set_frequency(Q(915, "MHz"))
    gen.frequency.set_frequency(Q(2.45, "GHz"))
    gen.frequency.set_frequency(Q(100, "kHz"))  # low boundary
    gen.frequency.set_frequency(Q(20, "GHz"))  # high boundary
    assert be.writes == [
        "FREQ:CW 915000000.0",
        "FREQ:CW 2450000000.0",
        "FREQ:CW 100000.0",
        "FREQ:CW 20000000000.0",
    ]


def test_frequency_rejects_non_frequency_quantity() -> None:
    gen, _ = _gen()
    with pytest.raises(DimensionalityError):
        gen.frequency.set_frequency(Q(1, "dBm"))


def test_frequency_out_of_range_is_rejected() -> None:
    gen, _ = _gen()
    with pytest.raises(ValueError):
        gen.frequency.set_frequency(Q(21, "GHz"))
    with pytest.raises(ValueError):
        gen.frequency.set_frequency(Q(50, "kHz"))


def test_frequency_readback_and_mode() -> None:
    gen, be = _gen()
    be.on("FREQ:CW?", "+1.00000000000E+009").on("FREQ:MODE?", "CW").on("FREQ:MULT?", "+2")
    assert gen.frequency.get_frequency() == Q(1, "GHz")
    gen.frequency.set_mode("LIST")
    gen.frequency.set_mode("FIXED")
    assert gen.frequency.get_mode() == "CW"
    assert gen.frequency.get_multiplier() == 2
    assert be.writes == ["FREQ:MODE LIST", "FREQ:MODE FIX"]


def test_frequency_offset_reference_and_phase() -> None:
    gen, be = _gen()
    be.on("FREQ:OFFS?", "1000000").on("PHAS?", "0.5")
    gen.frequency.set_offset(Q(1, "MHz"))
    gen.frequency.set_multiplier(2)
    gen.frequency.set_reference(Q(1, "GHz"))
    gen.frequency.set_reference_to_current()
    gen.frequency.set_reference_enabled(False)
    gen.frequency.set_phase_adjust(Q(90, "deg"))
    gen.frequency.set_phase_reference()
    assert be.writes[:5] == [
        "FREQ:OFFS 1000000.0",
        "FREQ:OFFS:STAT ON",
        "FREQ:MULT 2",
        "FREQ:REF 1000000000.0",
        "FREQ:REF:STAT ON",
    ]
    assert be.writes[5:7] == ["FREQ:REF:SET", "FREQ:REF:STAT OFF"]
    phase_cmd = be.writes[7]
    assert phase_cmd.startswith("PHAS ") and phase_cmd.endswith("RAD")
    assert float(phase_cmd[5:-3]) == pytest.approx(1.5707963, abs=1e-6)
    assert be.writes[8] == "PHAS:REF"
    assert gen.frequency.get_offset() == Q(1, "MHz")
    assert gen.frequency.get_phase_adjust() == Q(0.5, "rad")


# -- power / output ----------------------------------------------------------

def test_level_is_sent_in_dbm_with_suffix() -> None:
    gen, be = _gen()
    gen.power.set_level(Q(-10, "dBm"))
    gen.power.set_level(Q(30, "dBm"))  # high boundary
    gen.power.set_level(Q(-130, "dBm"))  # low boundary
    assert be.writes == ["POW -10.0DBM", "POW 30.0DBM", "POW -130.0DBM"]


def test_level_accepts_any_power_unit() -> None:
    gen, be = _gen()
    gen.power.set_level(Q(1, "mW"))  # 1 mW == 0 dBm
    (written,) = be.writes
    assert written.startswith("POW ") and written.endswith("DBM")
    assert float(written[4:-3]) == pytest.approx(0.0, abs=1e-6)


def test_level_rejects_non_power_and_out_of_range() -> None:
    gen, _ = _gen()
    with pytest.raises(DimensionalityError):
        gen.power.set_level(Q(1, "GHz"))
    with pytest.raises(ValueError):
        gen.power.set_level(Q(31, "dBm"))
    with pytest.raises(ValueError):
        gen.power.set_level(Q(-131, "dBm"))


def test_level_readback() -> None:
    gen, be = _gen()
    be.on("POW?", "-1.00000000E+001")
    assert gen.power.get_level() == Q(-10, "dBm")


def test_rf_and_modulation_enable() -> None:
    gen, be = _gen()
    be.on("OUTP?", "1").on("OUTP:MOD?", "0")
    gen.power.set_rf_enabled(True)
    gen.power.off()
    gen.power.on()
    gen.set_rf_enabled(False)  # top-level convenience
    gen.power.set_modulation_enabled(True)
    assert be.writes == ["OUTP ON", "OUTP OFF", "OUTP ON", "OUTP OFF", "OUTP:MOD ON"]
    assert gen.power.get_rf_enabled() is True
    assert gen.power.get_modulation_enabled() is False


def test_power_mode_unit_alc_and_attenuator() -> None:
    gen, be = _gen()
    be.on("POW:MODE?", "FIX").on("POW:ALC?", "0").on("POW:ATT?", "+2.00000000E+001")
    gen.power.set_mode("LIST")
    gen.power.set_unit("DBM")
    gen.power.set_alc_enabled(False)
    gen.power.set_alc_source("DIODE")
    gen.power.set_alc_bandwidth_auto(False)
    gen.power.set_alc_bandwidth(Q(1, "kHz"))
    gen.power.power_search()
    gen.power.set_attenuation_auto(False)
    gen.power.set_attenuation(Q(20, "dB"))
    assert be.writes == [
        "POW:MODE LIST",
        "UNIT:POW DBM",
        "POW:ALC OFF",
        "POW:ALC:SOUR DIOD",
        "POW:ALC:BAND:AUTO OFF",
        "POW:ALC:BAND 1000.0",
        "POW:ALC:SEAR ONCE",
        "POW:ATT:AUTO OFF",
        "POW:ATT 20.0DB",
    ]
    assert gen.power.get_mode() == "FIX"
    assert gen.power.get_alc_enabled() is False
    assert gen.power.get_attenuation() == Q(20, "dB")


def test_power_offset_and_reference() -> None:
    gen, be = _gen()
    gen.power.set_offset(Q(3, "dB"))
    gen.power.set_reference(Q(0, "dBm"))
    gen.power.set_reference_enabled(False)
    assert be.writes == [
        "POW:OFFS 3.0DB",
        "POW:REF 0.0DBM",
        "POW:REF:STAT ON",
        "POW:REF:STAT OFF",
    ]


def test_set_cw_convenience_stops_sweeps_first() -> None:
    gen, be = _gen()
    gen.set_cw(Q(1, "GHz"), Q(-20, "dBm"))
    assert be.writes == [
        "FREQ:MODE CW",
        "POW:MODE FIX",
        "FREQ:CW 1000000000.0",
        "POW -20.0DBM",
        "OUTP ON",
    ]


# -- modulation --------------------------------------------------------------

def test_modulation_is_supported() -> None:
    gen, be = _gen()
    assert gen.modulation.is_supported() is True
    gen.modulation.disable()
    assert be.writes == ["AM:STAT OFF", "FM:STAT OFF", "PM:STAT OFF", "PULM:STAT OFF"]


def test_amplitude_modulation() -> None:
    gen, be = _gen()
    be.on("AM:STAT?", "1").on("AM:DEPT?", "+3.00000000E+001").on("AM:INT:FREQ?", "1000")
    gen.modulation.am.set_source("INTERNAL")
    gen.modulation.am.set_rate(Q(1, "kHz"))
    gen.modulation.am.set_depth(30.0)
    gen.modulation.am.set_type("EXPONENTIAL")
    gen.modulation.am.set_depth_exponential(6.0)
    gen.modulation.am.set_mode("NORMAL")
    gen.modulation.am.set_external_coupling("DC")
    gen.modulation.am.enable(True)
    assert be.writes == [
        "AM:SOUR INT",
        "AM:INT:FREQ 1000.0",
        "AM:DEPT 30.0",
        "AM:TYPE EXP",
        "AM:DEPT:EXP 6.0",
        "AM:MODE NORM",
        "AM:EXT:COUP DC",
        "AM:STAT ON",
    ]
    assert gen.modulation.am.get_enabled() is True
    assert gen.modulation.am.get_depth() == pytest.approx(30.0)
    assert gen.modulation.am.get_rate() == Q(1, "kHz")


def test_frequency_modulation() -> None:
    gen, be = _gen()
    be.on("FM:DEV?", "+1.00000000E+005")
    gen.modulation.fm.set_source("EXTERNAL")
    gen.modulation.fm.set_deviation(Q(100, "kHz"))
    gen.modulation.fm.enable(True)
    assert be.writes == ["FM:SOUR EXT", "FM:DEV 100000.0", "FM:STAT ON"]
    assert gen.modulation.fm.get_deviation() == Q(100, "kHz")
    with pytest.raises(DimensionalityError):
        gen.modulation.fm.set_deviation(Q(1, "dBm"))


def test_phase_modulation_deviation_in_radians() -> None:
    gen, be = _gen()
    be.on("PM:DEV?", "+1.00000000E+000")
    gen.modulation.pm.set_deviation(Q(1, "rad"))
    gen.modulation.pm.set_deviation(Q(180, "deg"))
    gen.modulation.pm.set_bandwidth("HIGH")
    gen.modulation.pm.enable(False)
    assert be.writes[0] == "PM:DEV 1.0RAD"
    assert be.writes[1].startswith("PM:DEV ") and be.writes[1].endswith("RAD")
    assert float(be.writes[1][7:-3]) == pytest.approx(3.14159265, abs=1e-6)
    assert be.writes[2:] == ["PM:BAND HIGH", "PM:STAT OFF"]
    assert gen.modulation.pm.get_deviation() == Q(1, "rad")
    with pytest.raises(DimensionalityError):
        gen.modulation.pm.set_deviation(Q(1, "Hz"))


def test_pulse_modulation() -> None:
    gen, be = _gen()
    be.on("PULM:STAT?", "1").on("PULM:INT:PER?", "1e-4").on("PULM:INT:PWID?", "1e-5")
    gen.modulation.pulse.set_source("FREE_RUN")
    gen.modulation.pulse.set_period(Q(100, "us"))
    gen.modulation.pulse.set_width(Q(10, "us"))
    gen.modulation.pulse.set_delay(Q(1, "us"))
    gen.modulation.pulse.set_rate(Q(10, "kHz"))
    gen.modulation.pulse.set_source("EXTERNAL")
    gen.modulation.pulse.set_external_polarity("INVERTED")
    gen.modulation.pulse.enable(True)
    assert be.writes == [
        "PULM:SOUR INT",
        "PULM:SOUR:INT FRUN",
        "PULM:INT:PER 0.0001",
        "PULM:INT:PWID 1e-05",
        "PULM:INT:DEL 1e-06",
        "PULM:INT:FREQ 10000.0",
        "PULM:SOUR EXT",
        "PULM:EXT:POL INV",
        "PULM:STAT ON",
    ]
    assert gen.modulation.pulse.get_enabled() is True
    assert gen.modulation.pulse.get_period() == Q(100, "us")
    assert gen.modulation.pulse.get_width() == Q(10, "us")
    with pytest.raises(DimensionalityError):
        gen.modulation.pulse.set_width(Q(1, "Hz"))


# -- sweep -------------------------------------------------------------------

def test_step_sweep_configuration() -> None:
    gen, be = _gen()
    be.on("SWE:POIN?", "+101").on("SWE:DWEL?", "+1.00000000E-002")
    gen.sweep.set_type("STEP")
    gen.sweep.set_start_frequency(Q(1, "GHz"))
    gen.sweep.set_stop_frequency(Q(2, "GHz"))
    gen.sweep.set_center_frequency(Q(1.5, "GHz"))
    gen.sweep.set_span(Q(1, "GHz"))
    gen.sweep.set_start_level(Q(-30, "dBm"))
    gen.sweep.set_stop_level(Q(-10, "dBm"))
    gen.sweep.set_points(101)
    gen.sweep.set_dwell(Q(10, "ms"))
    gen.sweep.set_spacing("LOGARITHMIC")
    gen.sweep.set_frequency_swept(True)
    gen.sweep.set_power_swept(False)
    assert be.writes == [
        "LIST:TYPE STEP",
        "FREQ:STAR 1000000000.0",
        "FREQ:STOP 2000000000.0",
        "FREQ:CENT 1500000000.0",
        "FREQ:SPAN 1000000000.0",
        "POW:STAR -30.0DBM",
        "POW:STOP -10.0DBM",
        "SWE:POIN 101",
        "SWE:DWEL 0.01",
        "SWE:SPAC LOG",
        "FREQ:MODE LIST",
        "POW:MODE FIX",
    ]
    assert gen.sweep.get_points() == 101
    assert gen.sweep.get_dwell() == Q(10, "ms")


def test_step_sweep_rejects_out_of_range_endpoints() -> None:
    gen, _ = _gen()
    with pytest.raises(ValueError):
        gen.sweep.set_stop_frequency(Q(25, "GHz"))
    with pytest.raises(ValueError):
        gen.sweep.set_start_level(Q(40, "dBm"))


def test_list_sweep_download() -> None:
    gen, be = _gen()
    be.on("LIST:FREQ:POIN?", "3")
    gen.sweep.set_type("LIST")
    gen.sweep.set_list_frequencies([Q(1, "GHz"), Q(1.5, "GHz"), Q(2, "GHz")])
    gen.sweep.set_list_levels([Q(-10, "dBm"), Q(-5, "dBm"), Q(0, "dBm")])
    gen.sweep.set_list_dwells([Q(1, "ms"), Q(2, "ms"), Q(5, "ms")])
    gen.sweep.use_step_dwell_for_list()
    assert be.writes == [
        "LIST:TYPE LIST",
        "LIST:FREQ 1000000000.0,1500000000.0,2000000000.0",
        "LIST:POW -10.0DBM,-5.0DBM,0.0DBM",
        "LIST:DWEL 0.001,0.002,0.005",
        "LIST:DWEL:TYPE LIST",
        "LIST:DWEL:TYPE STEP",
    ]
    assert gen.sweep.get_list_length() == 3


def test_sweep_direction_retrace_and_manual_stepping() -> None:
    gen, be = _gen()
    be.on("SWE:CPO?", "+7")
    gen.sweep.set_direction("DOWN")
    gen.sweep.set_retrace(False)
    gen.sweep.set_manual_mode(True)
    gen.sweep.set_manual_point(7)
    gen.sweep.set_manual_mode(False)
    assert be.writes == [
        "LIST:DIR DOWN",
        "LIST:RETR OFF",
        "LIST:MODE MAN",
        "LIST:MAN 7",
        "LIST:MODE AUTO",
    ]
    assert gen.sweep.get_current_point() == 7


def test_sweep_triggering_and_run_control() -> None:
    gen, be = _gen()
    be.on("STAT:OPER:COND?", "+8")
    gen.sweep.set_trigger_source("BUS")
    gen.sweep.set_point_trigger_source("MANUAL")
    gen.sweep.set_trigger_timer(Q(1.5, "s"))
    gen.sweep.set_trigger_slope("NEGATIVE")
    gen.sweep.set_continuous(False)
    gen.sweep.initiate()
    gen.trigger()
    gen.sweep.trigger_now()
    gen.sweep.single()
    gen.sweep.abort()
    assert be.writes == [
        "TRIG:SOUR BUS",
        "LIST:TRIG:SOUR MAN",
        "TRIG:TIM 1.5",
        "TRIG:SLOP NEG",
        "INIT:CONT OFF",
        "INIT",
        "*TRG",
        "TRIG",
        "TSW",
        "ABOR",
    ]
    assert gen.sweep.is_sweeping() is True
    be.on("STAT:OPER:COND?", "+32")  # only "waiting for trigger"
    assert gen.sweep.is_sweeping() is False


# -- reference ---------------------------------------------------------------

def test_reference_oscillator() -> None:
    gen, be = _gen()
    be.on("ROSC:SOUR?", "EXT").on("ROSC:SOUR:AUTO?", "1")
    assert gen.reference.get_source() == "EXT"
    assert gen.reference.is_external() is True
    assert gen.reference.get_auto_select() is True
    gen.reference.set_auto_select(False)
    assert be.writes == ["ROSC:SOUR:AUTO OFF"]


# -- system / status ---------------------------------------------------------

def test_preset_self_test_and_registers() -> None:
    gen, be = _gen()
    be.on("*TST?", "+0")
    gen.system.preset()
    gen.system.clear_status()
    gen.system.save_state(3)
    gen.system.recall_state(3, 1)
    gen.system.set_remote_display_update(False)
    gen.system.set_power_on_type("LAST")
    assert be.writes == [
        "SYST:PRES",
        "*CLS",
        "*SAV 3,0",
        "*RCL 3,1",
        "DISP:REM OFF",
        "SYST:PON:TYPE LAST",
    ]
    assert gen.system.self_test() is True
    assert gen.run_self_test() is True
    be.on("*TST?", "+1")
    assert gen.system.self_test() is False


def test_check_errors_accepts_plus_zero_no_error() -> None:
    gen, be = _gen()
    be.on("SYST:ERR?", '+0,"No error"')
    gen.check_errors("after setup")  # must not raise
    assert gen.system.get_error() == (0, "No error")
    be.on("SYST:ERR?", '-222,"Data out of range"')
    with pytest.raises(RuntimeError, match="Data out of range"):
        gen.check_errors("after setup")


def test_get_all_errors_drains_the_queue() -> None:
    gen, be = _gen()
    responses = iter(['-222,"Data out of range"', '-113,"Undefined header"', '+0,"No error"'])
    be._responses = lambda q: next(responses) if q == "SYST:ERR?" else ""
    assert gen.system.get_all_errors() == [
        (-222, "Data out of range"),
        (-113, "Undefined header"),
    ]


def test_operation_condition_register() -> None:
    gen, be = _gen()
    be.on("STAT:OPER:COND?", "+40")
    assert gen.system.get_operation_condition() == 40


# -- failsafe shutdown -------------------------------------------------------

def test_shutdown_forces_rf_output_off() -> None:
    gen, be = _gen()
    gen.close()
    assert "OUTP OFF" in be.writes
