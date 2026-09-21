"""Math waveforms and the FFT.

A math waveform is an expression over other waveforms (``'Ch1Wfm1*Ch2Wfm1'``,
``'FFTmag(Ch1Wfm1)'``). The FFT settings — centre, span, resolution bandwidth,
window — apply to a math waveform whose expression is an FFT.

Verified against the *R&S RTO6 User Manual*, chapters 24.10.5 "Mathematics"
and 24.13.1 "Basic FFT": ``CALCulate:MATH<m>[:EXPRession][:DEFine]``,
``CALCulate:MATH<m>:STATe``, ``CALCulate:MATH<m>:FFT:CFRequency`` / ``:SPAN`` /
``:STARt`` / ``:STOP`` / ``:FULLspan`` / ``:BANDwidth[:RESolution][:VALue]`` /
``:BANDwidth[:RESolution]:AUTO`` / ``:BANDwidth[:RESolution]:ADJusted?`` /
``:WINDow:TYPE`` / ``:TYPE`` / ``:LOGScale`` / ``:MAGNitude:RANGe`` /
``:MAGNitude:LEVel``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

from .....units import Quantity, ensure_frequency
from ....base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._oscilloscope import Oscilloscope

__all__ = ["Math", "FftWindow"]

FftWindow = Literal["RECTANGULAR", "HAMMING", "HANN", "BLACKMAN_HARRIS", "GAUSSIAN", "FLATTOP", "KAISER_BESSEL"]
_WINDOW_SCPI = {
    "RECTANGULAR": "RECT", "HAMMING": "HAMM", "HANN": "HANN", "BLACKMAN_HARRIS": "BLAC",
    "GAUSSIAN": "GAUS", "FLATTOP": "FLATTOP2", "KAISER_BESSEL": "KAIS",
}


class Math(Menu):
    """Math waveforms 1–8 and their FFT settings."""

    def __init__(self, parent: "Oscilloscope") -> None:
        super().__init__(parent)
        self._scope = parent

    def _check(self, math: int) -> None:
        self._scope.check_math(math)

    # -- expression ------------------------------------------------------------
    def define(self, math: int, expression: str) -> None:
        """Define the expression of math waveform `math` (``CALC:MATH<m> '<expr>'``)."""
        self._check(math)
        self.write(f"CALC:MATH{math} {c.quoted(expression)}")

    def get_expression(self, math: int) -> str:
        self._check(math)
        return c.parse_name(self.query(f"CALC:MATH{math}?"))

    def enable(self, math: int, enabled: bool = True) -> None:
        """Show / calculate the math waveform (``CALC:MATH<m>:STAT``)."""
        self._check(math)
        self.write(f"CALC:MATH{math}:STAT {c.onoff(enabled)}")

    def is_enabled(self, math: int) -> bool:
        self._check(math)
        return c.parse_bool(self.query(f"CALC:MATH{math}:STAT?"))

    # -- FFT --------------------------------------------------------------------
    def set_fft_center(self, math: int, frequency: Quantity) -> None:
        """Set the centre frequency of the displayed span (``CALC:MATH<m>:FFT:CFR``)."""
        self._check(math)
        ensure_frequency(frequency)
        self.write(f"CALC:MATH{math}:FFT:CFR {c.hz(frequency)}")

    def set_fft_span(self, math: int, span: Quantity) -> None:
        """Set the frequency span (``CALC:MATH<m>:FFT:SPAN``)."""
        self._check(math)
        ensure_frequency(span)
        self.write(f"CALC:MATH{math}:FFT:SPAN {c.hz(span)}")

    def set_fft_start(self, math: int, frequency: Quantity) -> None:
        self._check(math)
        ensure_frequency(frequency)
        self.write(f"CALC:MATH{math}:FFT:STAR {c.hz(frequency)}")

    def set_fft_stop(self, math: int, frequency: Quantity) -> None:
        self._check(math)
        ensure_frequency(frequency)
        self.write(f"CALC:MATH{math}:FFT:STOP {c.hz(frequency)}")

    def set_fft_full_span(self, math: int) -> None:
        """Show the full frequency range (``CALC:MATH<m>:FFT:FULL``)."""
        self._check(math)
        self.write(f"CALC:MATH{math}:FFT:FULL")

    def set_fft_rbw(self, math: int, rbw: Optional[Quantity]) -> None:
        """Set the resolution bandwidth (``CALC:MATH<m>:FFT:BAND``), or ``None`` to couple it to the span (``:BAND:AUTO ON``)."""
        self._check(math)
        if rbw is None:
            self.write(f"CALC:MATH{math}:FFT:BAND:AUTO ON")
            return
        ensure_frequency(rbw)
        self.write(f"CALC:MATH{math}:FFT:BAND:AUTO OFF")
        self.write(f"CALC:MATH{math}:FFT:BAND {c.hz(rbw)}")

    def get_fft_rbw(self, math: int) -> Quantity:
        """The effective resolution bandwidth (``CALC:MATH<m>:FFT:BAND:ADJ?``)."""
        self._check(math)
        return c.as_frequency(self.query(f"CALC:MATH{math}:FFT:BAND:ADJ?"))

    def set_fft_window(self, math: int, window: FftWindow) -> None:
        """Set the FFT window (``CALC:MATH<m>:FFT:WIND:TYPE``); Blackman-Harris by default."""
        self._check(math)
        self.write(f"CALC:MATH{math}:FFT:WIND:TYPE {_WINDOW_SCPI[window]}")

    def set_fft_type(self, math: int, magnitude: bool = True) -> None:
        """Show the magnitude (default) or the phase spectrum (``CALC:MATH<m>:FFT:TYPE``)."""
        self._check(math)
        self.write(f"CALC:MATH{math}:FFT:TYPE {'MAGN' if magnitude else 'PHAS'}")

    def set_fft_log_frequency(self, math: int, logarithmic: bool) -> None:
        """Logarithmic or linear frequency axis (``CALC:MATH<m>:FFT:LOGS``)."""
        self._check(math)
        self.write(f"CALC:MATH{math}:FFT:LOGS {'LOG' if logarithmic else 'LIN'}")

    def set_fft_magnitude_range(self, math: int, range_db: float, level: Optional[float] = None) -> None:
        """Set the vertical range in dB (``:FFT:MAGN:RANG``, 1–500) and optionally the reference level (``:FFT:MAGN:LEV``)."""
        self._check(math)
        if not 1 <= range_db <= 500:
            raise ValueError("FFT magnitude range must be between 1 and 500 dB.")
        self.write(f"CALC:MATH{math}:FFT:MAGN:RANG {c.scpi_number(range_db)}")
        if level is not None:
            self.write(f"CALC:MATH{math}:FFT:MAGN:LEV {c.scpi_number(level)}")

    # -- convenience ---------------------------------------------------------------
    def fft(
        self,
        source: str,
        center: Quantity,
        span: Quantity,
        math: int = 1,
        rbw: Optional[Quantity] = None,
        window: FftWindow = "BLACKMAN_HARRIS",
    ) -> None:
        """Define math waveform `math` as the magnitude FFT of `source` and set it up.

        `source` is a channel (``"CH1"``) or another math waveform (``"M2"``);
        the expression becomes ``'FFTmag(Ch1Wfm1)'``. Read the spectrum with
        ``scope.waveform.get_math_data(math, x_unit="Hz")``.
        """
        self.define(math, f"FFTmag({_expression_source(source)})")
        self.enable(math, True)
        self.set_fft_center(math, center)
        self.set_fft_span(math, span)
        self.set_fft_rbw(math, rbw)
        self.set_fft_window(math, window)


def _expression_source(source: str) -> str:
    """``"CH1"`` → ``Ch1Wfm1`` (the expression form of a channel), ``"M2"`` → ``Math2``."""
    text = str(source).strip().upper()
    if text.startswith("CH") and text[2:].isdigit():
        return f"Ch{int(text[2:])}Wfm1"
    if text.startswith("C") and text[1:].isdigit():
        return f"Ch{int(text[1:])}Wfm1"
    if text.startswith("M") and text[1:].isdigit():
        return f"Math{int(text[1:])}"
    return str(source)
