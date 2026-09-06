"""Declarative, quantity-aware CSV writing.

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
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from ..units import is_quantity

__all__ = ["CSVObject", "Column", "Value", "write"]


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
