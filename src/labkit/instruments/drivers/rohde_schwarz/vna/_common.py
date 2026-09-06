"""Shared helpers for the Rohde & Schwarz VNA menus.

The VNA reuses the analyzer conversions (frequency in Hz, power in dBm, time in
seconds) from the sibling :mod:`..\\_common` module, so those are re-exported
here unchanged. On top of them this module adds the parsing the VNA needs but the
spectrum analyzer does not: comma-separated float and *complex* (real/imaginary
pair) trace arrays, ``CALCulate:PARameter:CATalog?`` trace catalogs, and quoting
for the string-valued trace names the VNA SCPI uses (e.g. ``'Trc1'``).

Every command these helpers feed is verified against the *R&S ZNL/ZNLE User
Manual* (1178.5966.02, issue 23), chapter 11.5 "VNA command reference".
"""

from __future__ import annotations

import numpy as np

# Re-export the analyzer conversions used unchanged by the VNA menus.
from .._common import (
    as_frequency,
    as_power,
    as_ratio,
    as_seconds,
    db,
    dbm,
    hz,
    onoff,
    parse_bool,
    parse_float,
    parse_int,
    scpi_number,
    seconds,
)
from .....units import Quantity, ensure_frequency, quantity

__all__ = [
    # re-exported analyzer conversions
    "scpi_number",
    "hz",
    "seconds",
    "dbm",
    "db",
    "onoff",
    "parse_bool",
    "parse_float",
    "parse_int",
    "as_frequency",
    "as_power",
    "as_seconds",
    "as_ratio",
    # VNA-specific helpers
    "quoted",
    "check_frequency_range",
    "parse_float_array",
    "parse_complex_array",
    "parse_catalog",
    "parse_name",
    "frequencies",
]


def quoted(name: str) -> str:
    """Wrap a trace/channel name as a SCPI string literal: ``Trc1`` → ``'Trc1'``."""
    return f"'{name}'"


def parse_name(response: str) -> str:
    """Strip the surrounding quotes/whitespace from a string response."""
    return response.strip().strip("'\"")


def check_frequency_range(
    frequency: Quantity, low: Quantity, high: Quantity, label: str
) -> None:
    """Raise :class:`ValueError` if `frequency` is outside ``[low, high]`` (in Hz)."""
    ensure_frequency(frequency)
    f = frequency.to("Hz").magnitude
    lo = low.to("Hz").magnitude
    hi = high.to("Hz").magnitude
    if not lo <= f <= hi:
        raise ValueError(
            f"{label} {frequency} is outside the instrument range [{low}, {high}]."
        )


def parse_float_array(response: str) -> np.ndarray:
    """Parse a comma-separated ASCII response into a float array."""
    return np.array(
        [float(v) for v in response.split(",") if v.strip()], dtype=float
    )


def parse_complex_array(response: str) -> np.ndarray:
    """Parse an ``SDATa`` response (real, imag, real, imag, …) into a complex array."""
    flat = parse_float_array(response)
    return flat[0::2] + 1j * flat[1::2]


def parse_catalog(response: str) -> list[tuple[str, str]]:
    """Parse a ``CALCulate:PARameter:CATalog?`` response.

    The instrument returns ``'Trc1,S11,Trc2,S21'`` (a single quoted string of
    ``name,parameter`` pairs). Returns ``[("Trc1", "S11"), ("Trc2", "S21")]``;
    an empty catalog (``''``) returns ``[]``.
    """
    items = [x for x in parse_name(response).split(",") if x != ""]
    return [(items[i], items[i + 1]) for i in range(0, len(items) - 1, 2)]


def frequencies(start: float, stop: float, points: int) -> Quantity:
    """Build a linear frequency axis (Hz) from start/stop/points."""
    return quantity(np.linspace(start, stop, points), "Hz")
