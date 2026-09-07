"""FSV3007 measurement functions and the Noise Figure (K30) application.

Asserts the exact SCPI strings emitted by the ``measurement`` and ``noise_figure``
menus and the ``INSTrument`` channel controls, all verified against the R&S
FSVA3000/FSV3000 User Manual (1178.8520.02) and the R&S FSV3-K30 Noise Figure
User Manual (1178.9432.02). Same mock-backend style as test_fsv3007.py.
"""

from __future__ import annotations

import pytest

from labkit.instruments import FSV3007, mock_instrument
from labkit.instruments.mock import MockBackend
from labkit.units import quantity as Q


def _sa() -> tuple[FSV3007, MockBackend]:
    return mock_instrument(FSV3007, responses={"*IDN?": "R&S,FSV3007,1,2"})


# -- measurement mode (SEM / spurious / normal) ------------------------------

def test_measurement_mode() -> None:
    sa, be = _sa()
    sa.measurement.set_mode("SPECTRUM")
    sa.measurement.set_mode("SEM")
    sa.measurement.set_mode("SPURIOUS")
    assert be.writes == ["SWE:MODE AUTO", "SWE:MODE ESP", "SWE:MODE LIST"]


# -- channel power / ACLR / OBW ----------------------------------------------

def test_power_measurement_selection() -> None:
    sa, be = _sa()
    sa.measurement.channel_power()
    sa.measurement.aclr()
    sa.measurement.multicarrier_aclr()
    sa.measurement.occupied_bandwidth()
    sa.measurement.power_off()
    assert be.writes == [
        "CALC:MARK:FUNC:POW:SEL CPOW",
        "CALC:MARK:FUNC:POW:SEL ACP",
        "CALC:MARK:FUNC:POW:SEL MCAC",
        "CALC:MARK:FUNC:POW:SEL OBW",
        "CALC:MARK:FUNC:POW OFF",
    ]


def test_power_preset_and_result() -> None:
    sa, be = _sa()
    sa.measurement.preset_power("ACLR")
    be.on("CALC:MARK:FUNC:POW:RES? ACP", "-10.0,-45.2,-44.8")
    assert be.writes == ["POW:ACH:PRES ACP"]
    assert sa.measurement.get_power_result("ACLR") == [-10.0, -45.2, -44.8]


def test_aclr_channel_config() -> None:
    sa, be = _sa()
    sa.measurement.set_channel_pairs(2)
    sa.measurement.set_tx_channel_bandwidth(Q(3.84, "MHz"))
    sa.measurement.set_adjacent_channel_bandwidth(Q(3.84, "MHz"))
    sa.measurement.set_channel_spacing(Q(5, "MHz"))
    assert be.writes == [
        "POW:ACH:ACP 2",
        "POW:ACH:BWID:CHAN 3840000.0",
        "POW:ACH:BWID:ACH 3840000.0",
        "POW:ACH:SPAC:ACH 5000000.0",
    ]


# -- time-domain power -------------------------------------------------------

def test_time_domain_power() -> None:
    sa, be = _sa()
    sa.measurement.enable_time_domain_power(rms=True, mean=True)
    sa.measurement.set_time_domain_mode("RELATIVE")
    be.on("CALC:MARK:FUNC:SUMM:RMS:RES?", "-12.3")
    assert be.writes == [
        "CALC:MARK:FUNC:SUMM:RMS ON",
        "CALC:MARK:FUNC:SUMM:MEAN ON",
        "CALC:MARK:FUNC:SUMM:PPE OFF",
        "CALC:MARK:FUNC:SUMM:SDEV OFF",
        "CALC:MARK:FUNC:SUMM:MODE REL",
    ]
    assert sa.measurement.get_time_domain_power("RMS") == pytest.approx(-12.3)


# -- harmonic distortion -----------------------------------------------------

def test_harmonics() -> None:
    sa, be = _sa()
    sa.measurement.enable_harmonics(True)
    sa.measurement.set_harmonic_count(5)
    sa.measurement.preset_harmonics()
    be.on("CALC:MARK:FUNC:HARM:DIST? TOT", "0.5,-46.0")
    be.on("CALC:MARK:FUNC:HARM:LIST?", "-3.0,-40.0,-55.0")
    assert be.writes == [
        "CALC:MARK:FUNC:HARM ON",
        "CALC:MARK:FUNC:HARM:NHAR 5",
        "CALC:MARK:FUNC:HARM:PRES",
    ]
    assert sa.measurement.get_thd() == (0.5, -46.0)
    assert sa.measurement.get_harmonics() == [-3.0, -40.0, -55.0]


# -- third-order intercept / AM depth ----------------------------------------

def test_toi() -> None:
    sa, be = _sa()
    sa.measurement.enable_toi(True)
    be.on("CALC:MARK:FUNC:TOI:RES?", "12.5")
    assert be.writes == ["CALC:MARK:FUNC:TOI ON"]
    assert sa.measurement.get_toi() == pytest.approx(12.5)


def test_am_modulation_depth() -> None:
    sa, be = _sa()
    sa.measurement.enable_am_depth(True)
    sa.measurement.search_am_signal()
    be.on("CALC:MARK:FUNC:MDEP:RES?", "80.0")
    assert be.writes == ["CALC:MARK:FUNC:MDEP ON", "CALC:MARK:FUNC:MDEP:SEAR ONCE"]
    assert sa.measurement.get_am_depth() == pytest.approx(80.0)


# -- measurement channels / applications -------------------------------------

def test_channel_management() -> None:
    sa, be = _sa()
    sa.create_channel("IQ", "IQ Analyzer")
    sa.select_channel("Spectrum")
    sa.delete_channel("IQ Analyzer")
    assert be.writes == [
        "INST:CRE IQ,'IQ Analyzer'",
        "INST:SEL 'Spectrum'",
        "INST:DEL 'IQ Analyzer'",
    ]


def test_list_channels_parses() -> None:
    sa, be = _sa()
    be.on("INST:LIST?", "'ADEM','Analog Demod','NOISe','Noise'")
    assert sa.list_channels() == [("ADEM", "Analog Demod"), ("NOISe", "Noise")]


# -- noise figure application (K30) ------------------------------------------

def test_noise_figure_channel_and_enr() -> None:
    sa, be = _sa()
    sa.noise_figure.create("Noise")
    sa.noise_figure.select("Noise")
    sa.noise_figure.set_enr_mode("CONSTANT")
    sa.noise_figure.set_enr(15.2)
    sa.noise_figure.set_noise_source_type("DIODE")
    assert be.writes == [
        "INST:CRE NOISe,'Noise'",
        "INST:SEL 'Noise'",
        "CORR:ENR:MODE SPOT",
        "CORR:ENR:SPOT 15.2",
        "CORR:ENR:TYPE DIOD",
    ]


def test_noise_figure_frequency_config() -> None:
    sa, be = _sa()
    sa.noise_figure.set_points(101)
    sa.noise_figure.set_start(Q(10, "MHz"))
    sa.noise_figure.set_stop(Q(3, "GHz"))
    sa.noise_figure.set_single_frequency(Q(1, "GHz"))
    sa.noise_figure.use_frequency_list(continuous=False)
    sa.noise_figure.use_single_frequency(continuous=True)
    assert be.writes == [
        "FREQ:POIN 101",
        "FREQ:STAR 10000000.0",
        "FREQ:STOP 3000000000.0",
        "FREQ:SING 1000000000.0",
        "CONF:LIST:SING",
        "CONF:FREQ:CONT",
    ]


def test_noise_figure_calibration_and_results() -> None:
    sa, be = _sa()
    sa.noise_figure.set_second_stage_correction(True)
    sa.noise_figure.configure_calibration()
    be.on("TRAC1:DATA? TRACE1,NOIS", "3.1,3.2,3.0")
    be.on("TRAC1:DATA? TRACE1,GAIN", "20.1,20.0,19.9")
    be.on("TRAC1:DATA? TRACE1,TEMP", "290.0,291.0")
    be.on("TRAC1:DATA? TRACE1,YFAC", "5.0,5.1")
    assert be.writes == ["CORR ON", "CONF:CORR"]
    assert sa.noise_figure.get_noise_figure() == [3.1, 3.2, 3.0]
    assert sa.noise_figure.get_gain() == [20.1, 20.0, 19.9]
    assert sa.noise_figure.get_temperature() == [290.0, 291.0]
    assert sa.noise_figure.get_y_factor() == [5.0, 5.1]
