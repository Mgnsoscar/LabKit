"""Signal paths: loss tables with interpolation, components, and reference-plane moves."""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pytest

from labkit.io.csv import Column, write
from labkit.signal_path import Component, LossTable, SignalPath
from labkit.units import DimensionalityError, quantity as Q


def _table() -> LossTable:
    # deliberately unsorted: 1 GHz -> 1 dB, 2 GHz -> 2 dB, 3 GHz -> 4 dB
    return LossTable(Q([3.0, 1.0, 2.0], "GHz"), Q([4.0, 1.0, 2.0], "dB"))


def test_decibel_predicate_recognises_db_but_not_dbm() -> None:
    from labkit.units import is_dimensionless_decibel

    assert is_dimensionless_decibel(Q(3, "dB"))
    assert is_dimensionless_decibel(Q([1.0, 2.0], "dB"))
    assert not is_dimensionless_decibel(Q(3, "dBm"))
    assert not is_dimensionless_decibel(Q(3, "GHz"))
    assert not is_dimensionless_decibel(3.0)


# --- LossTable --------------------------------------------------------------

def test_loss_table_sorts_and_reports_range() -> None:
    table = _table()
    assert len(table) == 3
    np.testing.assert_allclose(table.frequencies.to("GHz").magnitude, [1.0, 2.0, 3.0])
    np.testing.assert_allclose(table.losses.magnitude, [1.0, 2.0, 4.0])
    lo, hi = table.frequency_range
    assert lo == Q(1, "GHz") and hi == Q(3, "GHz")


def test_loss_table_interpolates_linearly_in_db() -> None:
    table = _table()
    assert table.loss_at(Q(1, "GHz")) == Q(1, "dB")  # exact point
    assert table.loss_at(Q(1500, "MHz")).magnitude == pytest.approx(1.5)  # any unit
    assert table.loss_at(Q(2.5, "GHz")).magnitude == pytest.approx(3.0)
    array: Any = table.loss_at(Q([1.0, 2.5, 3.0], "GHz"))
    assert str(array.units) == "dB"
    np.testing.assert_allclose(array.magnitude, [1.0, 3.0, 4.0])


def test_loss_table_refuses_extrapolation_unless_asked() -> None:
    table = _table()
    with pytest.raises(ValueError, match="outside the characterized range"):
        table.loss_at(Q(500, "MHz"))
    with pytest.raises(ValueError):
        table.loss_at(Q([1.0, 4.0], "GHz"))
    assert table.loss_at(Q(500, "MHz"), extrapolate=True) == Q(1, "dB")
    assert table.loss_at(Q(4, "GHz"), extrapolate=True) == Q(4, "dB")


def test_loss_table_validates_inputs() -> None:
    with pytest.raises(DimensionalityError):
        LossTable(Q([1.0, 2.0], "dBm"), Q([1.0, 2.0], "dB"))
    with pytest.raises(TypeError):
        LossTable(Q([1.0, 2.0], "GHz"), Q([1.0, 2.0], "dBm"))
    with pytest.raises(ValueError):
        LossTable(Q([1.0, 2.0], "GHz"), Q([1.0], "dB"))
    with pytest.raises(DimensionalityError):
        _table().loss_at(Q(1, "dBm"))


def test_loss_table_round_trips_through_csv(tmp_path: Any) -> None:
    path = write(
        Column("Frequency", Q([1.0, 2.0, 3.0], "GHz")),
        Column("Loss", Q([1.0, 2.0, 4.0], "dB")),
        filename="cable", folder=str(tmp_path),
    )
    table = LossTable.from_csv(path)
    assert len(table) == 3
    assert table.loss_at(Q(2.5, "GHz")).magnitude == pytest.approx(3.0)
    # explicit column names also work
    table = LossTable.from_csv(path, frequency_column="Frequency", loss_column="Loss")
    assert table.loss_at(Q(1, "GHz")) == Q(1, "dB")


# --- Component ---------------------------------------------------------------

def test_flat_component_broadcasts_and_describes() -> None:
    pad = Component("10 dB pad SN1", Q(10.2, "dB"), date(2026, 8, 20))
    assert pad.loss_at(Q(1, "GHz")) == Q(10.2, "dB")
    array: Any = pad.loss_at(Q([1.0, 2.0], "GHz"))
    np.testing.assert_allclose(array.magnitude, [10.2, 10.2])
    assert pad.describe() == "10 dB pad SN1 (2026-08-20)"
    assert Component("bare", Q(0, "dB")).describe() == "bare"


def test_table_component_interpolates() -> None:
    cable = Component("cable", _table(), date(2026, 9, 1))
    assert cable.loss_at(Q(1.5, "GHz")).magnitude == pytest.approx(1.5)


def test_component_rejects_non_db_loss() -> None:
    with pytest.raises(TypeError):
        Component("bad", Q(1, "dBm"))
    with pytest.raises(TypeError):
        Component("bad", Q(1, "GHz"))


# --- SignalPath ---------------------------------------------------------------

def test_path_sums_losses_and_describes() -> None:
    path = SignalPath(
        Component("cable", _table(), date(2026, 9, 1)),
        Component("pad", Q(10, "dB"), date(2026, 8, 20)),
    )
    assert len(path) == 2
    assert path.loss_at(Q(2, "GHz")).magnitude == pytest.approx(12.0)
    array: Any = path.loss_at(Q([1.0, 3.0], "GHz"))
    np.testing.assert_allclose(array.magnitude, [11.0, 14.0])
    assert path.describe() == "cable (2026-09-01), pad (2026-08-20)"
    assert "cable (2026-09-01)" in repr(path)


def test_direct_path_has_no_loss() -> None:
    direct = SignalPath()
    assert len(direct) == 0
    assert direct.loss_at(Q(1, "GHz")) == Q(0, "dB")
    assert direct.describe() == "direct"
    assert direct.after(Q(-10, "dBm"), Q(1, "GHz")) == Q(-10, "dBm")


def test_after_and_before_move_the_reference_plane() -> None:
    path = SignalPath(Component("pad", Q(3, "dB")))
    f = Q(1, "GHz")
    # input path: generator sets -10 dBm, DUT sees -13 dBm
    assert path.after(Q(-10, "dBm"), f).magnitude == pytest.approx(-13.0)
    # output path: analyzer reads -20 dBm, DUT delivered -17 dBm
    assert path.before(Q(-20, "dBm"), f).magnitude == pytest.approx(-17.0)
    # arrays, with one frequency per element
    levels = Q([0.0, 10.0], "dBm")
    corrected: Any = path.before(levels, Q([1.0, 2.0], "GHz"))
    np.testing.assert_allclose(corrected.magnitude, [3.0, 13.0])
    # linear powers work too: 1 mW through 3 dB -> ~0.5 mW
    assert path.after(Q(1, "mW"), f).to("mW").magnitude == pytest.approx(10 ** -0.3)


def test_paths_concatenate_and_reject_non_components() -> None:
    a = SignalPath(Component("a", Q(1, "dB")))
    b = SignalPath(Component("b", Q(2, "dB")))
    assert (a + b).loss_at(Q(1, "GHz")) == Q(3, "dB")
    assert [c.name for c in a + b] == ["a", "b"]
    with pytest.raises(TypeError):
        SignalPath("not a component")  # type: ignore[arg-type]
