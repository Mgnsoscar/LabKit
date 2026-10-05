"""Shared helpers for the Siglent SHA850A spectrum-analyzer menus.

Small conversion utilities that keep the menu classes readable: quantities in,
SCPI-ready numbers out; SCPI responses in, quantities/bools out — the same set
the Rohde & Schwarz package uses, plus the range checks and the firmware-version
parser the SHA850A needs.

Command spelling
----------------
Commands are sent in their short form with a leading colon (``:FREQ:CENT``),
with the optional ``[:SENSe]`` root and the other bracketed nodes left out, as
the examples in the manual do. The *SHA850A User Manual* (EN01D) §10.1 and
§10.4 allow both: a command "usually starts with ':'" and may be abbreviated to
its capital letters. Numbers are sent as plain values in the SCPI default units
(Hz, s, dB); the reference level alone carries an explicit ``DBM`` suffix (see
:meth:`~labkit.instruments.drivers.siglent.amplitude.Amplitude.set_ref_level`).

Every command is checked against the *SHA850A User Manual* (EN01D) and
cross-checked against the *SSA3000X Plus / SSA3000X-R / SVA1000X Programming
Guide* (PG0703P_E02B), the same command family. The SHA manual is known to
carry copy errors from those products, so validate against your firmware if a
command behaves unexpectedly.
"""

from __future__ import annotations

import re
from typing import Optional

from ....units import Quantity, ensure_frequency, ensure_power, ensure_time, quantity

__all__ = [
    "onoff",
    "scpi_number",
    "hz",
    "seconds",
    "dbm",
    "db",
    "check_range",
    "parse_bool",
    "parse_float",
    "parse_int",
    "parse_float_list",
    "parse_firmware",
    "as_frequency",
    "as_power",
    "as_seconds",
    "as_ratio",
]


# --- outgoing: quantity -> SCPI number --------------------------------------

def scpi_number(value: float) -> str:
    """Format a number for a SCPI command.

    The value is first rounded to 15 significant digits so that unit
    conversions do not leak binary-float artefacts into the command
    (``2.3 GHz`` -> ``2300000000.0``, not ``2300000000.0000005``); 15 digits is
    far beyond the instrument's setting resolution (1 Hz, datasheet).
    """
    return repr(float(f"{float(value):.15g}"))


def hz(q: Quantity) -> str:
    """A frequency quantity as a value in hertz."""
    return scpi_number(ensure_frequency(q).to("Hz").magnitude)


def seconds(q: Quantity) -> str:
    """A duration quantity as a value in seconds."""
    return scpi_number(ensure_time(q).to("s").magnitude)


def dbm(q: Quantity) -> str:
    """A power quantity as a value in dBm."""
    return scpi_number(ensure_power(q).to("dBm").magnitude)


def db(q: Quantity) -> str:
    """A dimensionless ratio quantity as a value in dB."""
    return scpi_number(q.to("dB").magnitude)


def onoff(state: bool) -> str:
    return "ON" if state else "OFF"


def check_range(value: float, low: float, high: float, label: str, unit: str = "") -> None:
    """Raise :class:`ValueError` unless ``low <= value <= high``.

    The values are plain numbers in `unit` (which only labels the message);
    `label` names the setting.
    """
    if not low <= value <= high:
        suffix = f" {unit}" if unit else ""
        raise ValueError(
            f"{label} {value:g}{suffix} is outside the instrument range "
            f"[{low:g}, {high:g}]{suffix}."
        )


# --- incoming: SCPI response -> Python ---------------------------------------

def parse_bool(response: str) -> bool:
    return response.strip().upper() in ("1", "ON")


def parse_float(response: str) -> float:
    return float(response.strip())


def parse_int(response: str) -> int:
    return int(round(float(response.strip())))


def parse_float_list(response: str) -> list[float]:
    """Parse a comma-separated numeric response into a list of floats.

    Empty fields (a trailing comma, say) are skipped.
    """
    return [float(v) for v in response.split(",") if v.strip()]


def as_frequency(response: str) -> Quantity:
    return quantity(parse_float(response), "Hz")


def as_power(response: str) -> Quantity:
    return quantity(parse_float(response), "dBm")


def as_seconds(response: str) -> Quantity:
    return quantity(parse_float(response), "s")


def as_ratio(response: str) -> Quantity:
    return quantity(parse_float(response), "dB")


# --- firmware versions --------------------------------------------------------

# Siglent's own scheme, "<major>.<minor>R<revision>": "1.8R4", "V1.8R10". The
# pre-1.7 firmware names ("V1.1.2.1.6R5") end in the same pattern, and the regex
# takes its last two numbers: "1.6R5" orders before every 1.7/1.8 release, which
# is all a minimum-version check needs.
_R_VERSION = re.compile(r"(\d+)\.(\d+)\s*R\s*(\d+)", re.IGNORECASE)
# The old scheme without its "R<revision>": the first SHA850A release is
# "V1.1.2.1.2" (firmware revision history). Read as (1, <last number>, 0), the
# same ordering the R form above gives the old names. Searched with digit/dot
# boundaries, so a longer dotted number does not match inside it.
_OLD_VERSION = re.compile(r"(?<![\d.])V?1\.1\.2\.1\.(\d+)(?![\d.])", re.IGNORECASE)
# A plain dotted triple, but only as the whole field ("1.8.4", "V1.8.4"), so a
# longer dotted string such as the "100.01.01.06.01" of the manual's *IDN?
# example is not misread as version 100.1.1.
_DOTTED_VERSION = re.compile(r"^V?(\d+)\.(\d+)\.(\d+)$", re.IGNORECASE)


def parse_firmware(text: str) -> Optional[tuple[int, int, int]]:
    """Parse a Siglent firmware version into ``(major, minor, revision)``.

    Accepts ``"1.8R4"``, ``"V1.8R10"``, ``"1.8.4"`` and the old names:
    ``"V1.1.2.1.6R5"`` is read as ``(1, 6, 5)`` and the first release,
    ``"V1.1.2.1.2"`` (no ``R``), as ``(1, 2, 0)``. Returns ``None`` for
    anything else. The ``R`` form and the old names are searched anywhere in
    `text`, so a longer string (a system-information line) may be passed; the
    dotted triple must be the whole of `text`.
    """
    text = text.strip()
    match = _R_VERSION.search(text)
    if match is not None:
        major, minor, revision = (int(group) for group in match.groups())
        return major, minor, revision
    old = _OLD_VERSION.search(text)
    if old is not None:
        return 1, int(old.group(1)), 0
    match = _DOTTED_VERSION.match(text)
    if match is None:
        return None
    major, minor, revision = (int(group) for group in match.groups())
    return major, minor, revision
