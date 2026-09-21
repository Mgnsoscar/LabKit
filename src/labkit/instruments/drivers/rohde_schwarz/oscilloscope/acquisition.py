"""Sample rate, record length, resolution, averaging count and interpolation.

Verified against the *R&S RTO6 User Manual*, chapter 24.8.3 "Acquisition":
``ACQuire:SRATe``, ``ACQuire:POINts[:VALue]``, ``ACQuire:POINts:AUTO``,
``ACQuire:POINts:MAXimum``, ``ACQuire:POINts:ARATe?``, ``ACQuire:RESolution``,
``ACQuire:COUNt`` and ``ACQuire:INTerpolate``.
"""

from __future__ import annotations

from typing import Literal

from .....units import Quantity, ensure_frequency, ensure_time, quantity
from ....base import Menu
from . import _common as c

__all__ = ["Acquisition", "PointsMode", "Interpolation"]

#: Which of resolution / record length stays constant when the time scale changes.
PointsMode = Literal["RESOLUTION", "RECORD_LENGTH"]
_POINTS_MODE_SCPI = {"RESOLUTION": "RES", "RECORD_LENGTH": "RECL"}

#: Interpolation between waveform points.
Interpolation = Literal["LINEAR", "SINX", "SAMPLE_HOLD"]
_INTERPOLATION_SCPI = {"LINEAR": "LIN", "SINX": "SINX", "SAMPLE_HOLD": "SMHD"}


class Acquisition(Menu):
    """How the ADC stream becomes a waveform record."""

    # -- sample rate / record length / resolution ---------------------------
    def set_sample_rate(self, rate: Quantity) -> None:
        """Set the waveform sample rate in samples per second (``ACQ:SRAT``).

        A frequency quantity (``quantity(10, "GHz")`` = 10 GSa/s).
        """
        ensure_frequency(rate)
        self.write(f"ACQ:SRAT {c.hz(rate)}")

    def get_sample_rate(self) -> Quantity:
        """The waveform sample rate as a frequency quantity (``ACQ:SRAT?``)."""
        return c.as_frequency(self.query("ACQ:SRAT?"))

    def get_adc_sample_rate(self) -> Quantity:
        """The ADC sample rate (``ACQ:POIN:ARAT?``)."""
        return c.as_frequency(self.query("ACQ:POIN:ARAT?"))

    def set_record_length(self, points: int) -> None:
        """Set the number of waveform points per acquisition (``ACQ:POIN``)."""
        if points < 1:
            raise ValueError("Record length must be at least 1 point.")
        self.write(f"ACQ:POIN {int(points)}")

    def get_record_length(self) -> int:
        return c.parse_int(self.query("ACQ:POIN?"))

    def set_max_record_length(self, points: int) -> None:
        """Limit the automatically chosen record length (``ACQ:POIN:MAX``)."""
        self.write(f"ACQ:POIN:MAX {int(points)}")

    def set_resolution(self, interval: Quantity) -> None:
        """Set the time between successive waveform points (``ACQ:RES``)."""
        ensure_time(interval)
        self.write(f"ACQ:RES {c.seconds(interval)}")

    def get_resolution(self) -> Quantity:
        return c.as_seconds(self.query("ACQ:RES?"))

    def set_points_mode(self, mode: PointsMode) -> None:
        """Choose what stays constant when the time scale changes (``ACQ:POIN:AUTO``):
        the ``RESOLUTION`` (sample interval) or the ``RECORD_LENGTH``."""
        self.write(f"ACQ:POIN:AUTO {_POINTS_MODE_SCPI[mode]}")

    # -- count / interpolation ---------------------------------------------
    def set_count(self, acquisitions: int) -> None:
        """Set the number of acquisitions a single run takes, and the number used
        for averaging and envelope (``ACQ:COUN``), 1 – 16 777 215."""
        if not 1 <= acquisitions <= 16_777_215:
            raise ValueError("Acquisition count must be between 1 and 16777215.")
        self.write(f"ACQ:COUN {int(acquisitions)}")

    def get_count(self) -> int:
        return c.parse_int(self.query("ACQ:COUN?"))

    def set_interpolation(self, mode: Interpolation) -> None:
        """Set the interpolation between waveform points (``ACQ:INT``): ``SINX`` (default), ``LINEAR`` or ``SAMPLE_HOLD``."""
        self.write(f"ACQ:INT {_INTERPOLATION_SCPI[mode]}")

    def get_interpolation(self) -> str:
        return self.query("ACQ:INT?").strip()

    def restart_arithmetics(self) -> None:
        """Restart averaging / envelope calculation now (``ACQ:ARES:IMM``)."""
        self.write("ACQ:ARES:IMM")

    def sample_interval(self) -> Quantity:
        """The current sample interval derived from the sample rate (1 / rate)."""
        rate = self.get_sample_rate().to("Hz").magnitude
        return quantity(1.0 / rate, "s")
