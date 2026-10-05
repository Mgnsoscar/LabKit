"""Measurement selection and channel power — the analyzer's "Meas" menu.

Verified against the *SHA850A User Manual* (EN01D) §2 (``:INSTrument[:SELect]``,
``:INSTrument:MEASure``) and §3.11.2 "Channel Power" (the SHA850-AMK option).

Channel power on the SHA850A
----------------------------
The manual is not consistent about channel power, so the driver is defensive:

- **Reading.** The SHA850A manual documents ``:CHPower:MEASure:CHPower?``
  (channel power and density); the SSA3000X Plus programming guide
  (PG0703P_E02B) documents ``:MEASure:CHPower?`` for the same result. The driver
  asks the SHA form first and falls back to the SSA form. Each may answer with
  both values (power, density) or just the power; the density is then the
  power normalised to 1 Hz over the integration bandwidth, which is what the
  analyzer reports as its density ("Power (in dBm/Hz) normalized to 1Hz within
  the integration bandwidth", §3.11.2). A form the analyzer does not know gets
  no reply and leaves a ``-113`` in its error queue, which
  :meth:`~labkit.instruments.drivers.siglent._spectrum_analyzer.SHA850A.check_errors`
  then expects.
- **Span.** The SHA's note on ``[:SENSe]:FREQuency:SPAN`` says channel power has
  its own span command, printed ``[:SENSe]:CHPower:REQuency:SPAN`` — taken as a
  typo for ``FREQuency``. ``[:SENSe]:CHPower:FREQuency:SPAN:POWer`` ("span
  power") sets the span to the integration bandwidth, but the SSA guide asks for
  a span larger than the integration bandwidth, so the driver always sets an
  explicit span (1.5 × the integration bandwidth unless given).
- **Resolution bandwidth.** Channel power has its own RBW command,
  ``[:SENSe]:CHPower:BANDwidth[:RESolution]`` (named in the note on §3.2.1 only);
  it is sent only when asked for, otherwise the analyzer's choice stands.
- **Averaging.** The average mode is ``[:SENSe]:CHPower:AVERage:TCONtrol
  EXPOnential|REPEat``; no channel-power average count is documented, so the
  trace-1 average count is used.

All of this needs checking on the instrument in the driver's first session.
"""

from __future__ import annotations

import contextlib
import math
from typing import TYPE_CHECKING, Literal, Optional

from ....units import Quantity, ensure_frequency, quantity
from ...base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._spectrum_analyzer import SHA850A

__all__ = ["Measurement", "MeasurementType", "AnalyzerMode", "CHANNEL_POWER_QUERIES"]

#: The measurements of Spectrum Analyzer mode (``:INST:MEAS``, §2).
MeasurementType = Literal["SA", "ACPR", "CHPower", "OBW", "TPOWer", "SPECtrogram", "TOI", "HARMonics", "CNR"]
#: Operating mode (``:INST``, §2). The manual lists ``SA`` and ``MA`` (and an
#: ``RTSA`` copied from another product); the cable-and-antenna and VNA modes'
#: mnemonics are not documented.
AnalyzerMode = Literal["SA", "MA"]

#: The channel-power read-outs, in the order they are tried: SHA850A, then SSA3000X Plus.
CHANNEL_POWER_QUERIES = (":CHP:MEAS:CHP?", ":MEAS:CHP?")

#: Span used when none is given, as a multiple of the integration bandwidth.
_SPAN_PER_BANDWIDTH = 1.5


class Measurement(Menu):
    """Select the operating mode and measurement, and run channel power."""

    def __init__(self, parent: "SHA850A") -> None:
        super().__init__(parent)
        self._analyzer = parent

    # -- mode / measurement ---------------------------------------------------
    def set_mode(self, mode: AnalyzerMode) -> None:
        """Select the operating mode (``:INST``): spectrum analyzer or modulation analyzer."""
        self.write(f":INST {mode}")

    def get_mode(self) -> str:
        return self.query(":INST?").strip()

    def select(self, measurement: MeasurementType) -> None:
        """Select the Spectrum Analyzer measurement (``:INST:MEAS``); ``"SA"`` is the swept spectrum."""
        self.write(f":INST:MEAS {measurement}")

    def get_selected(self) -> str:
        """The active measurement as the analyzer reports it (``SA``, ``CHP``, …)."""
        return self.query(":INST:MEAS?").strip()

    # -- channel power -----------------------------------------------------------
    def channel_power(
        self,
        center: Quantity,
        bandwidth: Quantity,
        span: Optional[Quantity] = None,
        averages: Optional[int] = None,
        rbw: Optional[Quantity] = None,
    ) -> tuple[Quantity, Quantity]:
        """Measure the power in `bandwidth` around `center` with the channel-power measurement.

        Selects channel power, sets the density unit to dBm/Hz, the center
        frequency, the integration bandwidth and the span (`span`, default
        1.5 × `bandwidth`; it must not be smaller than the bandwidth), optionally
        the RBW and an average over `averages` sweeps (repeat mode), runs one
        single sweep and reads the result (see the module note for the two read
        forms). The Swept SA measurement is selected again afterwards, also when
        the measurement fails.

        Returns ``(power, density)``: the channel power in dBm and the power
        spectral density as a linear quantity in mW/Hz. LabKit quantities cannot
        carry dBm/Hz (a logarithmic unit does not divide), so convert with
        :func:`~labkit.instruments.drivers.siglent.dbm_per_hz` when the dBm/Hz
        figure is wanted.
        """
        bw_hz = float(ensure_frequency(bandwidth).to("Hz").magnitude)
        if bw_hz <= 0:
            raise ValueError(f"Integration bandwidth must be positive, got {bandwidth}.")
        if span is None:
            span = quantity(bw_hz * _SPAN_PER_BANDWIDTH, "Hz")
        span_hz = float(ensure_frequency(span).to("Hz").magnitude)
        if span_hz < bw_hz:
            raise ValueError(f"Span {span} is smaller than the integration bandwidth {bandwidth}.")
        c.check_range(span_hz, 0.0, self._analyzer.max_frequency.to("Hz").magnitude, "Span", "Hz")
        if averages is not None and not 1 <= int(averages) <= 999:
            raise ValueError(f"Averages must be 1–999, got {averages}.")

        try:
            self.select("CHPower")
            self.write(":UNIT:CHP:POW:PSD DBMHZ")
            self._analyzer.frequency.set_center(center)
            self.write(f":CHP:BWID:INT {c.hz(bandwidth)}")
            self.write(f":CHP:FREQ:SPAN {c.hz(span)}")
            if rbw is not None:
                self.write(f":CHP:BAND {c.hz(rbw)}")
            if averages is not None:
                self.write(":CHP:AVER:TCON REPE")
                self._analyzer.trace.set_type(1, "AVERage" if int(averages) > 1 else "WRITe")
                self._analyzer.trace.set_average_count(int(averages), 1)
            # Without `averages` the sweep waits for whatever averaging the
            # driver configured before.
            self._analyzer.single_sweep(sweeps=None if averages is None else int(averages))
            power, density = self._read_channel_power(bw_hz)
        except BaseException:
            with contextlib.suppress(Exception):
                self.select("SA")
            raise
        self.select("SA")
        return quantity(power, "dBm"), quantity(10 ** (density / 10.0), "mW/Hz")

    def _read_channel_power(self, bandwidth_hz: float) -> tuple[float, float]:
        """``(dBm, dBm/Hz)`` from the first read form that answers with a number."""
        for command in CHANNEL_POWER_QUERIES:
            try:
                response = self.query(command)
            except Exception:
                # An unknown query gets no reply on the raw socket (the next
                # query resynchronises the session, in case a slow one answers
                # after all) and leaves a -113 in the error queue that
                # check_errors expects.
                self._analyzer._note_probe(command)
                continue
            try:
                values = c.parse_float_list(response)
            except ValueError:
                continue
            if not values:
                continue
            power = values[0]
            density = values[1] if len(values) > 1 else power - 10.0 * math.log10(bandwidth_hz)
            return power, density
        raise RuntimeError(
            "The analyzer returned no channel-power result "
            f"(tried {' and '.join(CHANNEL_POWER_QUERIES)}); is the SHA850-AMK option installed?"
        )
