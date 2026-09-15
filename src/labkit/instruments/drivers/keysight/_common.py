"""Shared helpers for Keysight/Agilent MXG signal-generator menus.

Small conversion utilities that keep the menu classes readable: quantities in,
SCPI-ready numbers out; SCPI responses in, quantities/bools out.

The MXG is a SCPI-99 instrument. Frequencies and times are sent as plain
numbers in the SCPI default units (Hz and s). Power levels are sent with an
explicit ``DBM`` suffix, because the instrument's default amplitude unit is a
persistent setting (``:UNIT:POWer``) that a previous user may have changed to
volts; the suffix makes the command unambiguous whatever that setting is.
Angles (phase-modulation deviation) likewise carry an explicit ``RAD`` suffix,
since the command accepts radians, pi-radians or degrees.

Everything here is verified against the *Agilent N5161A/62A/81A/82A/83A MXG
Signal Generators SCPI Command Reference* (N5180-90004).
"""

from __future__ import annotations

from ....units import (
    Quantity,
    ensure_angle,
    ensure_frequency,
    ensure_power,
    ensure_time,
    quantity,
)

__all__ = [
    "onoff",
    "scpi_number",
    "hz",
    "dbm",
    "db",
    "seconds",
    "radians",
    "percent",
    "check_range",
    "parse_bool",
    "parse_int",
    "parse_float",
    "parse_word",
    "as_frequency",
    "as_power",
    "as_seconds",
    "as_radians",
    "as_ratio",
]


# --- outgoing: quantity -> SCPI argument ------------------------------------

def scpi_number(value: float) -> str:
    """Format a number for a SCPI command.

    The value is first rounded to 15 significant digits so that unit
    conversions do not leak binary-float artefacts into the command
    (``100 us`` -> ``0.0001``, not ``9.999999999999999e-05``); 15 digits is
    far beyond any instrument's setting resolution.
    """
    return repr(float(f"{float(value):.15g}"))


def hz(frequency: Quantity) -> str:
    """A frequency quantity as a value in **Hz** (the SCPI default frequency unit)."""
    return scpi_number(ensure_frequency(frequency).to("Hz").magnitude)


def dbm(level: Quantity) -> str:
    """A power quantity as a value in dBm with an explicit ``DBM`` suffix."""
    return scpi_number(ensure_power(level).to("dBm").magnitude) + "DBM"


def db(ratio: Quantity) -> str:
    """A dimensionless ratio quantity as a value in dB with a ``DB`` suffix."""
    return scpi_number(ratio.to("dB").magnitude) + "DB"


def seconds(time: Quantity) -> str:
    """A duration quantity as a value in **seconds** (the SCPI default time unit)."""
    return scpi_number(ensure_time(time).to("s").magnitude)


def radians(angle: Quantity) -> str:
    """An angle quantity as a value in radians with an explicit ``RAD`` suffix."""
    return scpi_number(ensure_angle(angle).to("rad").magnitude) + "RAD"


def percent(value: float) -> str:
    """A plain percentage as a SCPI number (the ``PCT`` unit is the default)."""
    return scpi_number(value)


def onoff(state: bool) -> str:
    """``True`` -> ``"ON"``, ``False`` -> ``"OFF"``."""
    return "ON" if state else "OFF"


def check_range(value: Quantity, low: Quantity, high: Quantity, unit: str, label: str) -> None:
    """Raise :class:`ValueError` if `value` is outside ``[low, high]``.

    All three quantities are compared in `unit` (so dBm levels and mW powers, or
    MHz and GHz frequencies, compare correctly). `label` names the quantity in
    the error message.
    """
    v = value.to(unit).magnitude
    lo = low.to(unit).magnitude
    hi = high.to(unit).magnitude
    if not lo <= v <= hi:
        raise ValueError(
            f"{label} {value} is outside the instrument range [{low}, {high}]."
        )


# --- incoming: SCPI response -> Python ---------------------------------------

def parse_bool(response: str) -> bool:
    """``"1"``/``"ON"`` -> ``True``, anything else -> ``False``."""
    return response.strip().upper() in ("1", "ON")


def parse_int(response: str) -> int:
    """Parse an integer response (also accepts ``+5`` and ``5.0`` forms)."""
    return int(round(float(response.strip())))


def parse_float(response: str) -> float:
    """Parse a numeric response such as ``+1.00000000E+009``."""
    return float(response.strip())


def parse_word(response: str) -> str:
    """Parse a mnemonic response (e.g. ``INT``/``EXT``), upper-cased and trimmed."""
    return response.strip().upper()


def as_frequency(response: str) -> Quantity:
    """A numeric response in Hz as a frequency quantity."""
    return quantity(parse_float(response), "Hz")


def as_power(response: str) -> Quantity:
    """A numeric response in dBm as a power quantity."""
    return quantity(parse_float(response), "dBm")


def as_seconds(response: str) -> Quantity:
    """A numeric response in seconds as a duration quantity."""
    return quantity(parse_float(response), "s")


def as_radians(response: str) -> Quantity:
    """A numeric response in radians as an angle quantity."""
    return quantity(parse_float(response), "rad")


def as_ratio(response: str) -> Quantity:
    """A numeric response in dB as a dimensionless ratio quantity."""
    return quantity(parse_float(response), "dB")
