"""The Aim-TTi TGR6000 driver, exercised through the scriptable mock backend.

Asserts the exact SCPI-style strings the driver emits (all verified against the
TGR6000 Instruction Manual, Iss 9) and the quantity conversions/round-trips.
"""

from __future__ import annotations

import pytest

from labkit.instruments import TGR6000, mock_instrument
from labkit.instruments.drivers.aim_tti import ModulationNotSupportedError
from labkit.instruments.mock import MockBackend
from labkit.units import DimensionalityError, quantity as Q

_IDN = "THURLBY THANDAR,TGR6000,345678,1.00 1.00 1.00"


def _gen() -> tuple[TGR6000, MockBackend]:
    return mock_instrument(TGR6000, responses={"*IDN?": _IDN})


# -- identity / connection ---------------------------------------------------

def test_build_address_is_raw_socket_on_port_9221() -> None:
    gen, _ = _gen()
    assert gen._address == "TCPIP0::0.0.0.0::9221::SOCKET"


def test_id_query() -> None:
    gen, _ = _gen()
    assert gen.get_id() == _IDN


# -- frequency (FREQ, in MHz) ------------------------------------------------

def test_frequency_is_sent_in_megahertz() -> None:
    gen, be = _gen()
    gen.frequency.set_frequency(Q(915, "MHz"))
    gen.frequency.set_frequency(Q(1, "GHz"))
    gen.frequency.set_frequency(Q(10, "MHz"))  # low boundary
    gen.frequency.set_frequency(Q(6, "GHz"))  # high boundary
    assert be.writes == ["FREQ 915.0", "FREQ 1000.0", "FREQ 10.0", "FREQ 6000.0"]


def test_frequency_rejects_non_frequency_quantity() -> None:
    gen, _ = _gen()
    with pytest.raises(DimensionalityError):
        gen.frequency.set_frequency(Q(1, "dBm"))


def test_frequency_out_of_range_is_rejected() -> None:
    gen, _ = _gen()
    with pytest.raises(ValueError):
        gen.frequency.set_frequency(Q(7, "GHz"))
    with pytest.raises(ValueError):
        gen.frequency.set_frequency(Q(1, "MHz"))


# -- output level (DBMLEV / UVLEV / MVLEV / DBUVLEV) and RF enable ------------

def test_output_level_in_dbm() -> None:
    gen, be = _gen()
    gen.output.set_level(Q(-10, "dBm"))
    gen.output.set_level(Q(7, "dBm"))  # high boundary
    assert be.writes == ["DBMLEV -10.0", "DBMLEV 7.0"]


def test_output_level_accepts_any_power_unit() -> None:
    gen, be = _gen()
    gen.output.set_level(Q(1, "mW"))  # 1 mW == 0 dBm
    (written,) = be.writes
    assert written.startswith("DBMLEV ")
    assert float(written.split()[1]) == pytest.approx(0.0, abs=1e-6)


def test_output_level_rejects_non_power_quantity() -> None:
    gen, _ = _gen()
    with pytest.raises(DimensionalityError):
        gen.output.set_level(Q(1, "GHz"))


def test_output_level_out_of_range_is_rejected() -> None:
    gen, _ = _gen()
    with pytest.raises(ValueError):
        gen.output.set_level(Q(10, "dBm"))
    with pytest.raises(ValueError):
        gen.output.set_level(Q(-120, "dBm"))


def test_output_level_in_voltage_units() -> None:
    gen, be = _gen()
    gen.output.set_level_microvolts(Q(500, "uV"))
    gen.output.set_level_millivolts(Q(2, "mV"))
    gen.output.set_level_dbuv(100.0)
    assert be.writes == ["UVLEV 500.0", "MVLEV 2.0", "DBUVLEV 100.0"]


def test_voltage_level_rejects_non_voltage_quantity() -> None:
    gen, _ = _gen()
    with pytest.raises(DimensionalityError):
        gen.output.set_level_microvolts(Q(1, "dBm"))


def test_rf_enable() -> None:
    gen, be = _gen()
    gen.output.set_rf_enabled(True)
    gen.output.set_rf_enabled(False)
    gen.output.on()
    gen.output.off()
    gen.set_rf_enabled(True)  # top-level convenience
    assert be.writes == ["RFON", "RFOFF", "RFON", "RFOFF", "RFON"]


# -- modulation (unsupported on this model) ----------------------------------

def test_modulation_is_reported_unsupported() -> None:
    gen, _ = _gen()
    assert gen.modulation.is_supported() is False
    gen.modulation.disable()  # no-op; must not raise or emit anything


def test_modulation_setters_raise() -> None:
    gen, be = _gen()
    for call in (
        gen.modulation.set_am,
        gen.modulation.set_fm,
        gen.modulation.set_pm,
        gen.modulation.set_pulse,
    ):
        with pytest.raises(ModulationNotSupportedError):
            call()
    assert be.writes == []  # nothing was ever sent to the instrument


# -- step sweep --------------------------------------------------------------

def test_step_sweep_parameters() -> None:
    gen, be = _gen()
    gen.sweep.set_start_frequency(Q(1, "GHz"))
    gen.sweep.set_stop_frequency(Q(2, "GHz"))
    gen.sweep.set_start_level(Q(-30, "dBm"))
    gen.sweep.set_stop_level(Q(-10, "dBm"))
    gen.sweep.set_dwell(Q(10, "ms"))
    gen.sweep.set_points(101)
    gen.sweep.set_scale("LOG")
    assert be.writes == [
        "STARTFREQ 1000.0",
        "STOPFREQ 2000.0",
        "STARTLEV -30.0",
        "STOPLEV -10.0",
        "SWPDWELL 10.0",
        "SWPNUMPTS 101",
        "SWPSCALE LOG",
    ]


def test_general_sweep_settings() -> None:
    gen, be = _gen()
    gen.sweep.set_type("STEP")
    gen.sweep.set_parameter("ALL")
    gen.sweep.set_repeat(True)
    gen.sweep.set_direction("UP")
    gen.sweep.set_display_update(False)
    gen.sweep.set_sync_polarity("POS")
    assert be.writes == [
        "SWPTYPE STEP",
        "SWPPARAM ALL",
        "SWPREPEAT ON",
        "SWPDIRN UP",
        "SWPDISP OFF",
        "SWPSYNC POS",
    ]


def test_sweep_triggering() -> None:
    gen, be = _gen()
    gen.sweep.set_trigger_source("EXT+")
    gen.sweep.set_point_trigger_source("MAN")
    gen.sweep.set_trigger_enabled(True)
    gen.sweep.set_point_trigger_enabled(False)
    gen.sweep.set_trigger_time(Q(1.5, "s"))
    assert be.writes == [
        "SWP_TRGSRC EXT+",
        "SWPPT_TRGSRC MAN",
        "SWP_TRG_EN ON",
        "SWPPT_TRG_EN OFF",
        "SWP_TRGTIME 1.5",
    ]


def test_sweep_run_control_and_status() -> None:
    gen, be = _gen()
    be.on("SWPRUNSTAT?", "RUN").on("SWP_PT?", "5").on("SWPTRGSTAT?", "SWP_TRG?")
    gen.sweep.run()
    gen.sweep.stop()
    assert be.writes == ["SWPRUN", "SWPSTOP"]
    assert gen.sweep.get_run_status() == "RUN"
    assert gen.sweep.is_running() is True
    assert gen.sweep.get_current_point() == 5
    assert gen.sweep.get_trigger_status() == "SWP_TRG?"


# -- list sweep --------------------------------------------------------------

def test_list_sweep_point_and_download() -> None:
    gen, be = _gen()
    gen.sweep.init_list()
    gen.sweep.copy_step_to_list()
    gen.sweep.set_list_point(2, Q(1, "GHz"), Q(-10, "dBm"), Q(5, "ms"))
    gen.sweep.load_list(
        [
            (Q(1, "GHz"), Q(-10, "dBm"), Q(5, "ms")),
            (Q(2, "GHz"), Q(-20, "dBm"), Q(10, "ms")),
        ]
    )
    assert be.writes == [
        "SWPLISTINIT",
        "SWPCOPY",
        "SWPPOINTSET 2,1000.0,-10.0,5.0",
        "SWPLISTSET 2,1000.0,-10.0,5.0,2000.0,-20.0,10.0",
    ]


# -- reference ---------------------------------------------------------------

def test_reference_socket() -> None:
    gen, be = _gen()
    gen.reference.set_socket("IN")
    gen.reference.output_internal()
    gen.reference.disable()
    assert be.writes == ["REFSKT IN", "REFSKT OUT", "REFSKT OFF"]


# -- system / status ---------------------------------------------------------

def test_self_test() -> None:
    gen, be = _gen()
    be.on("*TST?", "0")
    assert gen.system.self_test() is True
    assert gen.run_self_test() is True
    be.on("*TST?", "1")
    assert gen.system.self_test() is False


def test_check_errors_uses_execution_error_register() -> None:
    gen, be = _gen()
    be.on("EER?", "0")
    gen.check_errors("after setup")  # no error -> no raise
    assert gen.system.get_execution_error() == 0
    be.on("EER?", "120")
    with pytest.raises(RuntimeError):
        gen.check_errors("after setup")


def test_system_stores_and_settings() -> None:
    gen, be = _gen()
    be.on("ADDRESS?", "5")
    gen.system.save_setup(3)
    gen.system.recall_setup(3)
    gen.system.save_list(1)
    gen.system.recall_list(1)
    gen.system.set_power_up_mode("OFF")
    gen.system.set_buzzer(True)
    gen.system.set_edit_mode("STEP")
    gen.system.go_to_local()
    assert be.writes == [
        "SAVESETUP 3",
        "RCLSETUP 3",
        "SAVELIST 1",
        "RCLLIST 1",
        "PWRUPMODE OFF",
        "BUZZ ON",
        "EDITMODE STEP",
        "LOCAL",
    ]
    assert gen.system.get_address() == 5


def test_manual_trigger() -> None:
    gen, be = _gen()
    gen.trigger()
    assert be.writes == ["*TRG"]


# -- failsafe shutdown -------------------------------------------------------

def test_shutdown_forces_rf_output_off() -> None:
    gen, be = _gen()
    gen.close()
    assert "RFOFF" in be.writes
