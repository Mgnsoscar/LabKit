"""Declarative, quantity-aware CSV writing and reading.

Describe the CSV you want as :class:`Column` and :class:`Value` objects, then
call :func:`write`::

    write(
        Value("Peak", peak_freq),                 # -> a "# Peak [MHz]: 300.0" comment
        Column("Frequency", freqs),               # a quantity column
        Column("Power", powers, unit="dBm"),      # convert + label with the unit
        filename="sweep",
        folder="results",
    )

A :class:`Column` is a full data column; a :class:`Value` is a single scalar
written as a comment line in the header (handy for recording settings alongside
the data). Columns need not be the same length — short ones are padded with
empty cells.

:func:`read` is the inverse: it parses a file written this way back into a
:class:`Table` whose columns and header values are quantities again, so data
can be post-processed long after it was measured::

    table = read("results/sweep.csv")
    freqs = table.column("Frequency")     # a MHz quantity array
    peak = table.value("Peak")            # a MHz quantity

Units
-----
When data is a LabKit quantity, the unit is handled for you, and — unlike the
earlier prototype — the header and the written values are **always in the same
unit**:

- ``unit=""`` (default): auto. A quantity column is written in its own unit and
  labelled with it (``"Frequency [MHz]"``); a plain column gets no unit suffix.
- ``unit="mW"`` (explicit): the quantity is **converted** to that unit before
  writing, and the header uses it. (The prototype labelled the new unit but
  wrote the old values — the pitfall this fixes.)
- ``unit=None``: never add a unit suffix; write the raw magnitude.

The class was misspelled ``Collumn`` in the prototype; it is :class:`Column`.
"""

from __future__ import annotations

import csv as _csv
import math
import os
import re
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import numpy as np

from ..units import is_quantity, quantity

__all__ = ["CSVObject", "Column", "Value", "Table", "write", "read"]


def _resolve(data: Any, unit: Optional[str]) -> tuple[Optional[str], Any]:
    """Return ``(unit_label, magnitudes)`` applying the unit rules above."""
    if is_quantity(data):
        if unit is None:
            return None, data.magnitude
        if unit == "":
            return f"{data.units:~}", data.magnitude
        return unit, data.to(unit).magnitude
    # plain data: an explicit unit labels it (values untouched); "" / None do not.
    if unit:
        return unit, data
    return None, data


def _labelled(label: str, unit_label: Optional[str]) -> str:
    return label if unit_label is None else f"{label} [{unit_label}]"


def _format_cell(x: Any) -> str:
    try:
        value = float(x)
    except (TypeError, ValueError):
        return str(x)
    if math.isnan(value):
        return ""
    return repr(value)


class CSVObject(ABC):
    """Base class for things that can be written to a CSV."""


@dataclass
class Column(CSVObject):
    """A named data column.

    Parameters
    ----------
    label:
        The column header (a unit is appended per the rules in the module docs).
    data:
        A sequence, numpy array, or LabKit quantity.
    unit:
        ``""`` = auto, an explicit unit string = convert-and-label, ``None`` =
        no unit suffix. See the module documentation.
    """

    label: str
    data: Any
    unit: Optional[str] = field(default="")

    def _header(self) -> str:
        unit_label, _ = _resolve(self.data, self.unit)
        return _labelled(self.label, unit_label)

    def _cells(self) -> list[str]:
        _, magnitudes = _resolve(self.data, self.unit)
        return [_format_cell(x) for x in np.atleast_1d(magnitudes)]


@dataclass
class Value(CSVObject):
    """A single labelled value, written as a ``# label: value`` header comment."""

    label: str
    data: Any
    unit: Optional[str] = field(default="")

    def _comment(self) -> str:
        unit_label, magnitude = _resolve(self.data, self.unit)
        return f"# {_labelled(self.label, unit_label)}: {magnitude}"


def write(
    *data: CSVObject,
    filename: str,
    folder: Optional[str] = None,
) -> str:
    """Write columns/values to a CSV file and return the absolute path written.

    :class:`Value` objects become ``#``-comment lines at the top of the file, in
    the order given; :class:`Column` objects become the data columns, in order.
    The `folder` is created if it does not exist; the working directory is used
    when `folder` is ``None``.
    """
    columns = [obj for obj in data if isinstance(obj, Column)]
    values = [obj for obj in data if isinstance(obj, Value)]
    if not columns:
        raise ValueError("write() needs at least one Column.")

    folder = "." if folder is None else folder
    os.makedirs(folder, exist_ok=True)
    if not filename.lower().endswith(".csv"):
        filename += ".csv"
    path = os.path.abspath(os.path.join(folder, filename))

    headers = [col._header() for col in columns]
    cells = [col._cells() for col in columns]
    height = max(len(c) for c in cells)
    # Pad short columns with empty cells and transpose into rows.
    padded = [c + [""] * (height - len(c)) for c in cells]
    rows = list(zip(*padded))

    with open(path, "w", newline="", encoding="utf-8") as handle:
        for value in values:
            handle.write(value._comment() + "\n")
        writer = _csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)

    return path


# --- reading ----------------------------------------------------------------

_LABEL_WITH_UNIT = re.compile(r"^(?P<label>.*?)\s*\[(?P<unit>[^\]]*)\]\s*$")


def _split_label(text: str) -> tuple[str, Optional[str]]:
    """``"Frequency [MHz]"`` -> ``("Frequency", "MHz")``; ``"Note"`` -> ``("Note", None)``."""
    match = _LABEL_WITH_UNIT.match(text.strip())
    if match is None:
        return text.strip(), None
    return match.group("label").strip(), match.group("unit").strip()


def _parse_scalar(text: str, unit: Optional[str]) -> Any:
    """A header value: a quantity if it has a unit, a float if numeric, else the text."""
    text = text.strip()
    try:
        number = float(text)
    except ValueError:
        return text
    return quantity(number, unit) if unit else number


def _parse_column(cells: list[str], unit: Optional[str]) -> Any:
    """A data column: a quantity/float array if numeric (blank = NaN), else strings."""
    numbers: list[float] = []
    for cell in cells:
        cell = cell.strip()
        if cell == "":
            numbers.append(math.nan)
            continue
        try:
            numbers.append(float(cell))
        except ValueError:
            return np.array([c.strip() for c in cells], dtype=object)
    magnitudes = np.array(numbers, dtype=float)
    return quantity(magnitudes, unit) if unit else magnitudes


@dataclass
class Table:
    """A CSV file read back: header values and data columns, units restored.

    Attributes
    ----------
    path:
        The file the table was read from.
    values:
        ``{label: value}`` from the ``# label [unit]: value`` header comments.
        Quantities where a unit was present, floats where numeric, else text.
    columns:
        ``{label: data}`` for each data column. A quantity array where the header
        carried a unit, a float array otherwise (blank cells become NaN), or an
        object array of strings for non-numeric columns.
    """

    path: str
    values: dict[str, Any]
    columns: dict[str, Any]

    def column(self, label: str) -> Any:
        """The column with this label (without the unit suffix)."""
        try:
            return self.columns[label]
        except KeyError:
            raise KeyError(f"No column '{label}' in {self.path}; have {list(self.columns)}.") from None

    def value(self, label: str) -> Any:
        """The header value with this label (without the unit suffix)."""
        try:
            return self.values[label]
        except KeyError:
            raise KeyError(f"No header value '{label}' in {self.path}; have {list(self.values)}.") from None

    def first_column(self, predicate: Callable[[object], bool]) -> Any:
        """The first column for which `predicate` is true (e.g. ``is_frequency``)."""
        for data in self.columns.values():
            if predicate(data):
                return data
        raise KeyError(f"No column in {self.path} matches {getattr(predicate, '__name__', predicate)}.")


def read(path: str) -> Table:
    """Read a CSV written by :func:`write` back into a :class:`Table`.

    Leading ``#`` lines are parsed as ``label [unit]: value`` header values; the
    first non-comment row is the column header; every following row is data.
    Columns whose header carries a ``[unit]`` come back as quantity arrays.
    """
    values: dict[str, Any] = {}
    data_lines: list[str] = []
    with open(path, encoding="utf-8", newline="") as handle:
        for raw in handle:
            line = raw.rstrip("\r\n")
            if not data_lines and line.startswith("#"):
                body = line[1:].strip()
                label_text, _, value_text = body.partition(":")
                if not value_text and ":" not in body:
                    continue  # a bare comment, not a value
                label, unit = _split_label(label_text)
                values[label] = _parse_scalar(value_text, unit)
                continue
            if line.strip() == "" and not data_lines:
                continue
            data_lines.append(line)

    if not data_lines:
        raise ValueError(f"{path} has no column header.")

    rows = list(_csv.reader(data_lines))
    header = rows[0]
    data_rows = [r for r in rows[1:] if any(c.strip() for c in r)]
    columns: dict[str, Any] = {}
    for index, text in enumerate(header):
        label, unit = _split_label(text)
        cells = [r[index] if index < len(r) else "" for r in data_rows]
        columns[label] = _parse_column(cells, unit)
    return Table(path=os.path.abspath(path), values=values, columns=columns)
