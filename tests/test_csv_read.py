"""Reading CSV files written by labkit.io.csv.write back into quantities."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from labkit.io.csv import Column, Table, Value, read, write
from labkit.units import is_frequency, quantity as Q


def test_round_trip_restores_quantities_and_values(tmp_path: Any) -> None:
    path = write(
        Value("Operator", "MSO"),
        Value("Channel", 1),
        Value("Peak", Q(300, "MHz")),
        Value("Ref level", Q(-10, "dBm")),
        Column("Frequency", Q([1.0, 2.0, 3.0], "GHz")),
        Column("Power", Q([-30.0, -20.0, -10.0], "dBm")),
        Column("Index", [1, 2, 3]),
        filename="sweep", folder=str(tmp_path),
    )
    table = read(path)
    assert isinstance(table, Table)
    assert table.path == path

    assert table.value("Operator") == "MSO"
    assert table.value("Channel") == 1.0
    assert table.value("Peak") == Q(300, "MHz")
    assert table.value("Ref level") == Q(-10, "dBm")

    freqs = table.column("Frequency")
    assert str(freqs.units) == "GHz"
    np.testing.assert_allclose(freqs.magnitude, [1.0, 2.0, 3.0])
    assert str(table.column("Power").units) == "dBm"
    index = table.column("Index")
    assert isinstance(index, np.ndarray) and not hasattr(index, "units")
    np.testing.assert_allclose(index, [1.0, 2.0, 3.0])


def test_padded_short_columns_become_nan(tmp_path: Any) -> None:
    path = write(
        Column("Long", [1.0, 2.0, 3.0]),
        Column("Short", Q([1.0], "s")),
        filename="ragged", folder=str(tmp_path),
    )
    table = read(path)
    short = table.column("Short")
    assert str(short.units) == "s"
    assert short.magnitude[0] == 1.0
    assert np.isnan(short.magnitude[1:]).all()


def test_text_columns_and_bare_comments(tmp_path: Any) -> None:
    path = tmp_path / "manual.csv"
    path.write_text(
        "# just a note without a value\n"
        "# Setup: bench A\n"
        "Name,Level [dBm]\n"
        "first,-10\n"
        "second,-20\n",
        encoding="utf-8",
    )
    table = read(str(path))
    assert table.values == {"Setup": "bench A"}
    assert list(table.column("Name")) == ["first", "second"]
    np.testing.assert_allclose(table.column("Level").magnitude, [-10.0, -20.0])


def test_first_column_and_missing_names(tmp_path: Any) -> None:
    path = write(
        Column("Loss", Q([1.0, 2.0], "dB")),
        Column("Frequency", Q([1.0, 2.0], "GHz")),
        filename="table", folder=str(tmp_path),
    )
    table = read(path)
    first = table.first_column(is_frequency)
    assert str(first.units) == "GHz"
    np.testing.assert_allclose(first.magnitude, [1.0, 2.0])
    with pytest.raises(KeyError, match="No column 'Nope'"):
        table.column("Nope")
    with pytest.raises(KeyError, match="No header value"):
        table.value("Nope")
    with pytest.raises(KeyError):
        table.first_column(lambda x: False)


def test_empty_file_is_rejected(tmp_path: Any) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("# only: comments\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no column header"):
        read(str(path))
