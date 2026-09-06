"""Declarative CSV writing.

Describe the CSV you want as :class:`Column` and :class:`Value` objects, then
call :func:`write`::

    write(
        Column("Frequency [MHz]", freqs.to("MHz").magnitude),
        Column("Power [dBm]", powers.magnitude),
        filename="sweep",
        folder="results",
    )

A :class:`Column` is a full data column; a :class:`Value` is a single scalar
written as a one-row column (useful for recording settings alongside data).

Status
------
Skeleton. The classes define the public API; :func:`write` is not implemented
yet.

Note: the corresponding class in the earlier prototype was misspelled
``Collumn``; it is :class:`Column` here.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Iterable, Optional

__all__ = ["CSVObject", "Column", "Value", "write"]


class CSVObject(ABC):
    """Base class for things that can be written to a CSV."""


@dataclass
class Column(CSVObject):
    """A named column of values.

    Parameters
    ----------
    label:
        The column header.
    values:
        The column data. Pass plain magnitudes (e.g. ``q.to("MHz").magnitude``);
        the label should state the unit so the file is self-describing.
    """

    label: str
    values: Iterable[float]


@dataclass
class Value(CSVObject):
    """A single labelled scalar, written as a one-row column."""

    label: str
    value: float


def write(
    *data: CSVObject,
    filename: str,
    folder: Optional[str] = None,
) -> str:
    """Write columns/values to a CSV file and return the path written.

    Status: skeleton — not implemented yet.
    """
    if not data:
        raise ValueError("write() requires at least one Column or Value.")
    raise NotImplementedError(
        "CSV writing is not implemented yet. This is a later milestone of the "
        "LabKit rebuild."
    )
