"""Shared helpers for the Rohde & Schwarz oscilloscope menus.

The oscilloscope reuses the analyzer conversions (frequency in Hz, time in
seconds, on/off, float/bool parsing) from the sibling :mod:`..\\_common` module
and adds what a scope needs on top: voltages, percentages, comma-separated
waveform arrays, the ``DATA:HEADer?`` record, and the source names the RTO
uses for channels (``C1W1``), math (``M1``) and reference (``R1``) waveforms.

Every command these helpers feed is verified against the *R&S RTO6 User
Manual* (1801.6687.02), chapter 24 "Remote control commands".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Re-export the analyzer conversions used unchanged by the scope menus.
from .._common import (
    as_frequency,
    as_seconds,
    hz,
    onoff,
    parse_bool,
    parse_float,
    parse_int,
    scpi_number,
    seconds,
)
from .....units import Quantity, ensure_voltage, quantity

__all__ = [
    # re-exported analyzer conversions
    "scpi_number",
    "hz",
    "seconds",
    "onoff",
    "parse_bool",
    "parse_float",
    "parse_int",
    "as_frequency",
    "as_seconds",
    # scope-specific helpers
    "volts",
    "as_volts",
    "percent",
    "quoted",
    "parse_name",
    "parse_float_array",
    "WaveformHeader",
    "parse_header",
    "channel_source",
    "source_name",
]


def volts(q: Quantity) -> str:
    """A voltage quantity as a value in volts."""
    return scpi_number(ensure_voltage(q).to("V").magnitude)


def as_volts(response: str) -> Quantity:
    return quantity(parse_float(response), "V")


def percent(value: float) -> str:
    """A plain percentage (0–100) as a SCPI number."""
    return scpi_number(float(value))


def quoted(text: str) -> str:
    """Wrap a name or expression as a SCPI string literal: ``FFTmag(Ch1)`` → ``'FFTmag(Ch1)'``."""
    return f"'{text}'"


def parse_name(response: str) -> str:
    """Strip the surrounding quotes/whitespace from a string response."""
    return response.strip().strip("'\"")


def parse_float_array(response: str) -> np.ndarray:
    """Parse a comma-separated ASCII response into a float array."""
    return np.array([float(v) for v in response.split(",") if v.strip()], dtype=float)


@dataclass(frozen=True)
class WaveformHeader:
    """The four values of a ``...:DATA:HEADer?`` response.

    ``x_start``/``x_stop`` are in the waveform's x unit (seconds for a channel,
    hertz for an FFT); ``values_per_sample`` is 1 for plain waveforms and 2 for
    envelope / peak-detect waveforms (min and max per sample interval).
    """

    x_start: float
    x_stop: float
    record_length: int
    values_per_sample: int

    def x_axis(self) -> np.ndarray:
        """The x values of the record, evenly spaced from ``x_start`` to ``x_stop``."""
        if self.record_length <= 1:
            return np.array([self.x_start], dtype=float)
        return np.linspace(self.x_start, self.x_stop, self.record_length)


def parse_header(response: str) -> WaveformHeader:
    """Parse ``<XStart>,<XStop>,<RecordLength>,<ValuesPerSample>``."""
    parts = [p.strip() for p in response.split(",") if p.strip()]
    if len(parts) != 4:
        raise ValueError(f"Unexpected waveform header response: {response!r}")
    return WaveformHeader(float(parts[0]), float(parts[1]), int(float(parts[2])), int(float(parts[3])))


def channel_source(channel: int, waveform: int = 1) -> str:
    """The RTO source name of a channel waveform: channel 1 → ``C1W1``."""
    return f"C{channel}W{waveform}"


def source_name(source: str) -> str:
    """Normalise a user-facing source to the RTO's name.

    ``"CH1"``/``"C1"``/``1`` → ``C1W1``; ``"M1"`` (math) and ``"R1"`` (reference)
    pass through; an already-formed ``C2W1`` passes through too.
    """
    text = str(source).strip().upper()
    if text.isdigit():
        return channel_source(int(text))
    if text.startswith("CH") and text[2:].isdigit():
        return channel_source(int(text[2:]))
    if text.startswith("C") and text[1:].isdigit():
        return channel_source(int(text[1:]))
    return text
