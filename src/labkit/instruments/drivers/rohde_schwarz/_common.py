"""Shared helpers for Rohde & Schwarz spectrum-analyzer menus.

Small conversion utilities that keep the menu classes readable: quantities in,
SCPI-ready numbers out; SCPI responses in, quantities/bools out. Every menu
here follows the R&S FSV3000 / FSW remote-command reference (the ``SENSe:``
prefix is left implicit, as the instruments accept the short form).

Because the R&S documentation site is not reachable from this build, the exact
command strings were written from the standard R&S FSV/FSW SCPI set. Anything
firmware-specific worth double-checking is flagged in a comment at its call
site.
"""

from __future__ import annotations

from ....units import Quantity, ensure_frequency, ensure_power, ensure_time, quantity

__all__ = [
    "onoff",
    "parse_bool",
    "parse_float",
    "parse_int",
    "scpi_number",
    "hz",
    "seconds",
    "dbm",
    "db",
    "as_frequency",
    "as_power",
    "as_seconds",
    "as_ratio",
]


# --- outgoing: quantity -> SCPI number --------------------------------------

def scpi_number(value: float) -> str:
    """Format a number for a SCPI command (plain decimal, full precision)."""
    return repr(float(value))


def hz(q: Quantity) -> str:
    """A frequency quantity as a value in hertz."""
    return scpi_number(ensure_frequency(q).to("Hz").magnitude)


def seconds(q: Quantity) -> str:
    """A duration quantity as a value in seconds."""
    return scpi_number(ensure_time(q).to("s").magnitude)


def dbm(q: Quantity) -> str:
    """A power quantity as a value in dBm (the default amplitude unit)."""
    return scpi_number(ensure_power(q).to("dBm").magnitude)


def db(q: Quantity) -> str:
    """A dimensionless ratio quantity as a value in dB."""
    return scpi_number(q.to("dB").magnitude)


def onoff(state: bool) -> str:
    return "ON" if state else "OFF"


# --- incoming: SCPI response -> Python ---------------------------------------

def parse_bool(response: str) -> bool:
    return response.strip().upper() in ("1", "ON")


def parse_float(response: str) -> float:
    return float(response.strip())


def parse_int(response: str) -> int:
    return int(round(float(response.strip())))


def as_frequency(response: str) -> Quantity:
    return quantity(parse_float(response), "Hz")


def as_power(response: str) -> Quantity:
    return quantity(parse_float(response), "dBm")


def as_seconds(response: str) -> Quantity:
    return quantity(parse_float(response), "s")


def as_ratio(response: str) -> Quantity:
    return quantity(parse_float(response), "dB")
