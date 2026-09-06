"""Shared helpers for Aim-TTi signal-generator menus.

Small conversion utilities that keep the menu classes readable: quantities in,
SCPI-ready numbers out; SCPI responses in, quantities/ints out.

Unlike the SCPI-99 analyzers, the Aim-TTi TGR remote language is a flat set of
mnemonic commands with **unit-bearing arguments** — ``FREQ`` takes a value in
**MHz** (not Hz), ``SWPDWELL`` takes **milliseconds**, ``SWP_TRGTIME`` takes
**seconds**, and levels come in dedicated commands per unit (``DBMLEV`` for dBm,
``UVLEV``/``MVLEV`` for microvolts/millivolts, ``DBUVLEV`` for dBµV). These
helpers pin each conversion to the unit the command expects, so a caller can
pass any equivalent quantity (``quantity(2.45, "GHz")`` → ``2450.0`` for
``FREQ``) and the right number is emitted.

Everything here is verified against the TGR6000 Instruction Manual (Iss 9),
"Remote Commands" / "Command List".
"""

from __future__ import annotations

from typing import cast

from ....units import (
    DimensionalityError,
    Quantity,
    ensure_frequency,
    ensure_power,
    ensure_time,
    is_quantity,
    quantity,
    ureg,
)

__all__ = [
    "onoff",
    "scpi_number",
    "megahertz",
    "dbm",
    "microvolts",
    "millivolts",
    "milliseconds",
    "seconds",
    "check_range",
    "parse_int",
    "parse_float",
    "parse_word",
]


# --- outgoing: quantity -> SCPI number --------------------------------------

def scpi_number(value: float) -> str:
    """Format a number for a TGR command (plain decimal, full precision)."""
    return repr(float(value))


def megahertz(frequency: Quantity) -> str:
    """A frequency quantity as a value in **MHz** (the unit ``FREQ`` expects)."""
    return scpi_number(ensure_frequency(frequency).to("MHz").magnitude)


def dbm(level: Quantity) -> str:
    """A power quantity as a value in **dBm** (the unit ``DBMLEV`` expects)."""
    return scpi_number(ensure_power(level).to("dBm").magnitude)


def milliseconds(time: Quantity) -> str:
    """A duration quantity as a value in **milliseconds** (e.g. for ``SWPDWELL``)."""
    return scpi_number(ensure_time(time).to("ms").magnitude)


def seconds(time: Quantity) -> str:
    """A duration quantity as a value in **seconds** (e.g. for ``SWP_TRGTIME``)."""
    return scpi_number(ensure_time(time).to("s").magnitude)


def _ensure_voltage(value: object) -> Quantity:
    """Return `value` if it is a voltage, else raise :class:`DimensionalityError`.

    Voltage has no dedicated ``ensure_*`` guard in :mod:`labkit.units` (it is
    only needed here, for the ``UVLEV``/``MVLEV`` level commands), so the check
    lives locally but raises the same error type as the shared guards.
    """
    volt_dim = ureg.Quantity(1, "V").dimensionality
    if is_quantity(value) and cast(Quantity, value).dimensionality == volt_dim:
        return cast(Quantity, value)
    got = getattr(value, "units", type(value).__name__)
    raise DimensionalityError(
        f"Expected a voltage quantity (e.g. uV, mV, V). Got '{got}'."
    )


def microvolts(level: Quantity) -> str:
    """A voltage quantity as a value in **microvolts** (the unit ``UVLEV`` expects)."""
    return scpi_number(_ensure_voltage(level).to("uV").magnitude)


def millivolts(level: Quantity) -> str:
    """A voltage quantity as a value in **millivolts** (the unit ``MVLEV`` expects)."""
    return scpi_number(_ensure_voltage(level).to("mV").magnitude)


def onoff(state: bool) -> str:
    """``True`` -> ``"ON"``, ``False`` -> ``"OFF"`` (the TGR on/off argument)."""
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

def parse_int(response: str) -> int:
    """Parse an integer response (``<nr1>``), tolerating a trailing CR."""
    return int(round(float(response.strip())))


def parse_float(response: str) -> float:
    """Parse a numeric response, tolerating a trailing CR."""
    return float(response.strip())


def parse_word(response: str) -> str:
    """Parse a mnemonic response (e.g. ``RUN``/``STOP``), upper-cased and trimmed."""
    return response.strip().upper()
