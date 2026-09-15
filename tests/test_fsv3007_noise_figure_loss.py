"""K30 additional-loss commands on the FSV noise-figure menu (mock backend)."""

from __future__ import annotations

from datetime import date

import pytest

from labkit.instruments import FSV3007, mock_instrument
from labkit.instruments.mock import MockBackend
from labkit.signal_path import Component, LossTable, SignalPath
from labkit.units import DimensionalityError, quantity as Q


def _sa() -> tuple[FSV3007, MockBackend]:
    return mock_instrument(FSV3007, responses={"*IDN?": "R&S,FSV3007,1,2"})


def test_constant_loss_selects_spot_mode() -> None:
    sa, be = _sa()
    sa.noise_figure.set_input_loss(Q(0.8, "dB"))
    sa.noise_figure.set_output_loss(Q(1.5, "dB"))
    sa.noise_figure.set_loss("CALIBRATION", Q(0.3, "dB"))
    assert be.writes == [
        "CORR:LOSS:INP:MODE SPOT", "CORR:LOSS:INP:SPOT 0.8",
        "CORR:LOSS:OUTP:MODE SPOT", "CORR:LOSS:OUTP:SPOT 1.5",
        "CORR:LOSS:CAL:MODE SPOT", "CORR:LOSS:CAL:SPOT 0.3",
    ]


def test_loss_table_is_selected_loaded_and_enabled() -> None:
    sa, be = _sa()
    sa.noise_figure.set_loss_table(
        "INPUT", Q([1.0, 2.0], "GHz"), Q([1.0, 1.5], "dB"), name="CableA"
    )
    assert be.writes == [
        "CORR:LOSS:INP:TABL:SEL 'CableA'",
        "CORR:LOSS:INP:TABL 1000000000.0,1.0,2000000000.0,1.5",
        "CORR:LOSS:INP:MODE TABL",
    ]


def test_loss_table_validation() -> None:
    sa, _ = _sa()
    with pytest.raises(ValueError, match="same length"):
        sa.noise_figure.set_loss_table("OUTPUT", Q([1.0, 2.0], "GHz"), Q([1.0], "dB"))
    with pytest.raises(DimensionalityError):
        sa.noise_figure.set_loss_table("OUTPUT", Q([1.0, 2.0], "dBm"), Q([1.0, 2.0], "dB"))
    with pytest.raises(ValueError, match="1 to 10001"):
        sa.noise_figure.set_loss_table("OUTPUT", Q([], "GHz"), Q([], "dB"))


def test_loss_from_signal_path_is_evaluated_at_the_measurement_frequencies() -> None:
    sa, be = _sa()
    path = SignalPath(
        Component("cable", LossTable(Q([1.0, 3.0], "GHz"), Q([1.0, 3.0], "dB")), date(2026, 9, 1)),
        Component("pad", Q(10, "dB")),
    )
    sa.noise_figure.set_loss_from_path("OUTPUT", path, Q([1.0, 2.0, 3.0], "GHz"))
    assert be.writes[0] == "CORR:LOSS:OUTP:TABL:SEL 'LabKit'"
    assert be.writes[1] == (
        "CORR:LOSS:OUTP:TABL 1000000000.0,11.0,2000000000.0,12.0,3000000000.0,13.0"
    )
    assert be.writes[2] == "CORR:LOSS:OUTP:MODE TABL"


def test_temperature_list_and_delete() -> None:
    sa, be = _sa()
    be.on("CORR:LOSS:INP:TABL:LIST?", "'CableA,CableB'")
    sa.noise_figure.set_loss_temperature("INPUT", Q(296.5, "K"))
    assert sa.noise_figure.list_loss_tables("INPUT") == ["CableA", "CableB"]
    sa.noise_figure.delete_loss_table("INPUT", "CableB")
    assert be.writes == ["CORR:LOSS:INP:TEMP 296.5", "CORR:LOSS:INP:TABL:DEL 'CableB'"]
