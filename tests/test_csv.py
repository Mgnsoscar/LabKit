"""The declarative, quantity-aware CSV writer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from labkit.io import Column, Value, write
from labkit.units import quantity as Q


def _read(path: str) -> list[str]:
    return Path(path).read_text(encoding="utf-8").splitlines()


def test_returns_path_and_writes_file(tmp_path: Path) -> None:
    path = write(Column("a", [1, 2, 3]), filename="out", folder=str(tmp_path))
    assert path == str((tmp_path / "out.csv").resolve())
    assert Path(path).is_file()


def test_filename_gets_csv_suffix(tmp_path: Path) -> None:
    path = write(Column("a", [1]), filename="nofx", folder=str(tmp_path))
    assert path.endswith("nofx.csv")


def test_quantity_auto_unit_in_header(tmp_path: Path) -> None:
    path = write(Column("Freq", Q(np.array([1, 2]), "MHz")), filename="f", folder=str(tmp_path))
    lines = _read(path)
    assert lines[0] == "Freq [MHz]"
    assert lines[1:] == ["1.0", "2.0"]


def test_explicit_unit_converts_values(tmp_path: Path) -> None:
    # The headline fix: label and written values must agree.
    path = write(
        Column("Freq", Q(np.array([1, 2, 3]), "GHz"), unit="MHz"),
        filename="c",
        folder=str(tmp_path),
    )
    lines = _read(path)
    assert lines[0] == "Freq [MHz]"
    assert lines[1:] == ["1000.0", "2000.0", "3000.0"]


def test_plain_column_has_no_unit_suffix(tmp_path: Path) -> None:
    path = write(Column("Index", [1, 2, 3]), filename="p", folder=str(tmp_path))
    assert _read(path)[0] == "Index"  # not "Index []"


def test_none_unit_suppresses_suffix(tmp_path: Path) -> None:
    path = write(
        Column("Freq", Q(np.array([1, 2]), "MHz"), unit=None),
        filename="n",
        folder=str(tmp_path),
    )
    assert _read(path)[0] == "Freq"


def test_dbm_column_writes_db_values(tmp_path: Path) -> None:
    path = write(
        Column("Power", Q(np.array([0.0, 3.0]), "dBm")), filename="d", folder=str(tmp_path)
    )
    lines = _read(path)
    assert lines[0] == "Power [dBm]"
    assert lines[1:] == ["0.0", "3.0"]


def test_values_become_comment_lines(tmp_path: Path) -> None:
    path = write(
        Value("Operator", "MSO"),
        Value("Peak", Q(1.5, "GHz")),
        Column("a", [1]),
        filename="v",
        folder=str(tmp_path),
    )
    lines = _read(path)
    assert lines[0] == "# Operator: MSO"
    assert lines[1] == "# Peak [GHz]: 1.5"
    assert lines[2] == "a"


def test_ragged_columns_are_padded(tmp_path: Path) -> None:
    path = write(
        Column("long", [1, 2, 3]),
        Column("short", [9]),
        filename="r",
        folder=str(tmp_path),
    )
    lines = _read(path)
    assert lines[0] == "long,short"
    assert lines[1:] == ["1.0,9.0", "2.0,", "3.0,"]


def test_requires_at_least_one_column(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write(Value("only", 1), filename="x", folder=str(tmp_path))


def test_creates_missing_folder(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir"
    path = write(Column("a", [1]), filename="f", folder=str(target))
    assert Path(path).is_file()
