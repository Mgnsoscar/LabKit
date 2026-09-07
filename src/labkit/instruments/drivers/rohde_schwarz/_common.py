"""Shared helpers for Rohde & Schwarz spectrum-analyzer menus.

Small conversion utilities that keep the menu classes readable: quantities in,
SCPI-ready numbers out; SCPI responses in, quantities/bools out. Every menu
here follows the R&S FSV3000 / FSW remote-command reference (the ``SENSe:``
prefix is left implicit, as the instruments accept the short form).

Command strings are verified against the R&S FSVA3000/FSV3000 User Manual
(1178.8520.02, issue 16); validate against your firmware version if a command
behaves unexpectedly.
"""

from __future__ import annotations

from ....units import Quantity, ensure_frequency, ensure_power, ensure_time, quantity

__all__ = [
    "onoff",
    "parse_bool",
    "parse_float",
    "parse_int",
    "parse_float_list",
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


def parse_float_list(response: str) -> list[float]:
    """Parse a comma-separated numeric response into a list of floats."""
    return [float(v) for v in response.split(",") if v.strip()]


def as_frequency(response: str) -> Quantity:
    return quantity(parse_float(response), "Hz")


def as_power(response: str) -> Quantity:
    return quantity(parse_float(response), "dBm")


def as_seconds(response: str) -> Quantity:
    return quantity(parse_float(response), "s")


def as_ratio(response: str) -> Quantity:
    return quantity(parse_float(response), "dB")
