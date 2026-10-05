"""Shared base for the Siglent SHA850A handheld spectrum analyzers.

The SHA851A (3.6 GHz) and SHA852A (7.5 GHz) share one SCPI command set — the
SSA3000X Plus / SVA1000X family's, with the SHA's own spellings — so the
composition lives here once and a concrete model is the base plus its frequency
range.

Connection
----------
The analyzer is reached over LAN on a **raw TCP socket, port 5025** ("Standard
mode … Use this port for programming", *SHA850A User Manual* (EN01D) §9.2.2), or
over VXI-11 or USB-TMC; there is no HiSLIP. A bare IP address becomes
``TCPIP::<ip>::5025::SOCKET``; any full VISA resource string (anything with
``::``) is used as given. The parent transport uses ``\\n`` read and write
termination, which a socket resource needs.

Two consequences of the raw socket shape the driver:

- **A query that gets no reply** (an undefined command) times out instead of
  failing fast, and a reply that arrives *after* a timeout would be read as the
  answer to the next query. The driver drains late replies after a timed-out
  query (:meth:`SHA850A._drain_input`, best effort) and keeps queries it is not
  sure of — the error queue — on a short timeout.
- **Waiting with ``*OPC?``.** ``*OPC?`` "stops any new commands from being
  processed until the current processing is complete. Then it returns a '1'"
  (§10.5), so the driver waits with one ``*OPC?`` whose read timeout covers the
  operation, rather than polling it on the normal I/O timeout.

Measurement sequence
--------------------
:meth:`SHA850A.single_sweep` runs ``:INIT:CONT OFF``, ``:INIT:IMM`` and
``*OPC?`` with a timeout of at least the sweep time × the number of sweeps plus a
margin. If ``*OPC?`` raises or answers anything but ``1`` it sleeps the expected
sweep time instead: the sister SSA3015X Plus has been seen to stall on
``*OPC?``, and SHA firmware before 1.8R4 froze on it (see
:meth:`~labkit.instruments.drivers.siglent.system.System.require_firmware`).
:meth:`SHA850A.measure_cw` builds the CW reading on top of it, sending only the
settings that changed since its last call.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Iterator, Optional

from ....units import Quantity, ensure_time, quantity
from ...base import Backend, BaseInstrument
from . import _common as c
from .amplitude import Amplitude
from .bandwidth import Bandwidth
from .frequency import Frequency
from .marker import Marker
from .measurement import Measurement
from .sweep import Sweep
from .system import ReferenceOscillator, System
from .trace import Trace

if TYPE_CHECKING:
    from ...environment import TestEnvironment

__all__ = ["SHA850A"]

#: Socket port of the analyzer's SCPI service ("Standard mode", §9.2.2).
SOCKET_PORT = 5025

#: The measured sweep takes longer than ``:SWE:TIME?`` (scheduling, FFT
#: processing: "Sweep Time Estimate", §3.3.3), so expected durations carry this factor.
_SWEEP_OVERHEAD = 1.25
#: Added to the ``*OPC?`` read timeout of a single sweep.
_OPC_MARGIN_S = 3.0
#: Added to the fallback sleep when ``*OPC?`` does not answer.
_SLEEP_MARGIN_S = 0.5
#: Sweep time assumed when ``:SWE:TIME?`` does not give a number.
_DEFAULT_SWEEP_S = 1.0
#: Read timeout of the error-queue query, which the SHA850A may not answer.
_ERROR_QUERY_TIMEOUT_S = 2.0
#: Read timeout, and the most reads, used to drain late replies.
_DRAIN_TIMEOUT_S = 0.25
_DRAIN_READS = 16
#: The error code of an undefined header: the instrument does not know SYST:ERR? itself.
_UNDEFINED_HEADER = -113


class SHA850A(BaseInstrument):
    """Common driver logic for the Siglent SHA850A spectrum analyzers (LAN, socket port 5025).

    Concrete models (:class:`~labkit.instruments.drivers.siglent.sha851a.SHA851A`,
    :class:`~labkit.instruments.drivers.siglent.sha852a.SHA852A`) set
    :attr:`max_frequency`; the base on its own assumes the family's 7.5 GHz.
    The constructor takes the parameters of
    :class:`~labkit.instruments.base.BaseInstrument`, plus one:

    Parameters
    ----------
    sleep:
        The function used to wait when ``*OPC?`` does not answer (the
        :meth:`single_sweep` fallback); :func:`time.sleep` unless a test injects
        one.
    """

    #: Top of the model's frequency range (the spectrum analyzer's, 9 kHz up).
    max_frequency: Quantity = quantity(7.5, "GHz")

    frequency: Frequency
    bandwidth: Bandwidth
    sweep: Sweep
    amplitude: Amplitude
    trace: Trace
    measurement: Measurement
    reference: ReferenceOscillator
    system: System

    def __init__(
        self,
        environment: "TestEnvironment",
        name: str,
        address: str,
        timeout: Quantity = quantity(10, "s"),
        backend: Optional[Backend] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        # measure_cw's memory of what it configured; any other write clears it.
        self._cw_settings: dict[str, str] = {}
        self._cw_sweep_s: Optional[float] = None
        self._cw_owner = False
        self._sleep = sleep
        super().__init__(environment, name, address, timeout, backend=backend)
        self.frequency = Frequency(self)
        self.bandwidth = Bandwidth(self)
        self.sweep = Sweep(self)
        self.amplitude = Amplitude(self)
        self.trace = Trace(self)
        self.measurement = Measurement(self)
        self.reference = ReferenceOscillator(self)
        self.system = System(self)

    def _build_address(self, address: str) -> str:
        """``"192.168.0.10"`` -> ``"TCPIP::192.168.0.10::5025::SOCKET"``; a VISA string is kept.

        Anything containing ``::`` (``"TCPIP0::…::INSTR"`` for VXI-11, a
        ``USB0::…`` resource) is taken to be a full resource name.
        """
        if "::" in address:
            return address
        return f"TCPIP::{address}::{SOCKET_PORT}::SOCKET"

    # -- transport bookkeeping ---------------------------------------------
    def write(self, command: str) -> Any:
        """Send a SCPI command (see :meth:`BaseInstrument.write`).

        A command not sent by :meth:`measure_cw` or :meth:`single_sweep`
        themselves makes :meth:`measure_cw` forget what it configured, so its next
        call sends every setting again: a change made through a menu (or by
        :meth:`~labkit.instruments.drivers.siglent.measurement.Measurement.channel_power`)
        is never mistaken for one it still owns. Changes at the front panel are
        not seen; call :meth:`forget_cw_settings` after those.
        """
        if not self._cw_owner:
            self.forget_cw_settings()
        return super().write(command)

    def forget_cw_settings(self) -> None:
        """Make the next :meth:`measure_cw` send all of its settings again."""
        self._cw_settings.clear()
        self._cw_sweep_s = None

    @contextmanager
    def _owned(self) -> Iterator[None]:
        """Writes in this block belong to measure_cw/single_sweep (they keep its memory)."""
        previous = self._cw_owner
        self._cw_owner = True
        try:
            yield
        finally:
            self._cw_owner = previous

    @contextmanager
    def _read_timeout(self, seconds: float) -> Iterator[None]:
        """Use a different I/O timeout inside the block, restoring the previous one."""
        previous: Optional[Quantity] = getattr(self, "_timeout", None)
        if previous is None:
            # A backend handed in directly keeps its own timeout (VISA: in ms).
            raw = getattr(self._backend, "timeout", None)
            if isinstance(raw, (int, float)):
                previous = quantity(raw, "ms")
        self.set_timeout(quantity(seconds, "s"))
        try:
            yield
        finally:
            if previous is not None:
                self.set_timeout(previous)

    def _drain_input(self) -> None:
        """Discard replies that arrived after a query timed out (best effort).

        Reads with a short timeout until nothing more arrives. Only a real VISA
        resource can be read without a query; for any other backend this does
        nothing. A reply later than the drain window still desynchronises the
        session — keep operation timeouts generous.
        """
        read = getattr(self._backend, "read", None)
        if not callable(read):
            return
        with self._read_timeout(_DRAIN_TIMEOUT_S):
            for _ in range(_DRAIN_READS):
                try:
                    read()
                except Exception:
                    return

    def _query_opc(self, timeout_s: float) -> bool:
        """One ``*OPC?`` with a read timeout of `timeout_s`; ``True`` when it answers ``1``."""
        try:
            with self._read_timeout(timeout_s):
                response = self.query("*OPC?")
        except Exception:
            self._drain_input()
            return False
        return response.strip().startswith("1")

    def wait_for_instrument(self, timeout: Quantity = quantity(60, "s")) -> None:
        """Block until ``*OPC?`` answers, with a single query of up to `timeout`.

        Overrides the base, which polls ``*OPC?`` on the normal I/O timeout: on a
        raw socket an ``*OPC?`` that times out still answers later, and that late
        ``1`` would be read as the reply to the next query.
        """
        if not self._query_opc(ensure_time(timeout).to("s").magnitude):
            raise TimeoutError(f"Timed out waiting for '{self._name}' to finish (*OPC?).")

    # -- error handling ----------------------------------------------------
    def check_errors(self, context: str) -> None:
        """Raise if the error queue reports an error — tolerantly.

        ``:SYSTem:ERRor?`` is not in the SHA850A's command list (§10.6), so it is
        asked on a short timeout and nothing is raised when it gets no reply, an
        empty one, ``0``/``+0`` ("no error"), or an "undefined header" error
        (``-113``, the instrument's complaint about the query itself). Only
        another error answer raises :class:`RuntimeError`. Overload is shown on
        the screen only (``ADC_ERROR``, §11.2); this cannot see it.
        """
        try:
            with self._read_timeout(_ERROR_QUERY_TIMEOUT_S):
                response = self.query(":SYST:ERR?").strip()
        except Exception:
            self._drain_input()
            return
        if not response:
            return
        code: Optional[int]
        try:
            code = int(float(response.split(",", 1)[0]))
        except ValueError:
            code = None
        if code == 0 or code == _UNDEFINED_HEADER or "undefined header" in response.lower():
            return
        raise RuntimeError(f"{context}. Instrument error: {response}")

    # -- markers -----------------------------------------------------------
    def marker(self, number: int = 1, enable: bool = False) -> Marker:
        """Return the marker with the given number, 1-8 (optionally switching it on)."""
        marker = Marker(self, number)
        if enable:
            marker.enable(True)
        return marker

    # -- measurement control ----------------------------------------------
    def sweep_seconds(self) -> float:
        """The sweep time the analyzer reports (``:SWE:TIME?``), in seconds.

        Falls back to 1 s when the reply is not a number, so a sweep is still
        given time to finish.
        """
        try:
            value = c.parse_float(self.query(":SWE:TIME?"))
        except (ValueError, TypeError):
            return _DEFAULT_SWEEP_S
        return value if value > 0 else _DEFAULT_SWEEP_S

    def single_sweep(self, timeout: Optional[Quantity] = None, sweeps: Optional[int] = None) -> None:
        """Run one single acquisition and wait for it to finish.

        Sends ``:INIT:CONT OFF``, restarts the averages of the traces the driver
        put into average mode (``:AVER:TRAC<n>:CLE``), sends ``:INIT:IMM`` and waits
        with ``*OPC?``. `sweeps` is how many sweeps the acquisition takes (the
        average/hold count); by default the count the
        :class:`~labkit.instruments.drivers.siglent.trace.Trace` menu configured.
        The ``*OPC?`` read timeout is `timeout`, or the sweep time (``:SWE:TIME?``)
        × `sweeps` × 1.25 plus 3 s. When ``*OPC?`` raises or does not answer
        ``1``, the method sleeps that expected time (+ 0.5 s) instead.
        """
        count = int(sweeps) if sweeps is not None else self.trace.sweeps_per_acquisition()
        self._single_sweep(self.sweep_seconds(), max(count, 1), timeout)

    def _single_sweep(self, sweep_s: float, sweeps: int, timeout: Optional[Quantity]) -> None:
        expected_s = sweep_s * sweeps * _SWEEP_OVERHEAD
        opc_s = ensure_time(timeout).to("s").magnitude if timeout is not None else expected_s + _OPC_MARGIN_S
        with self._owned():
            self.write(":INIT:CONT OFF")
            for trace in self.trace.averaging_traces():
                self.trace.clear_average(trace)
            self.write(":INIT:IMM")
        if not self._query_opc(opc_s):
            self._sleep(expected_s + _SLEEP_MARGIN_S)

    def measure_cw(
        self,
        frequency: Quantity,
        span: Quantity = quantity(5, "kHz"),
        rbw: Quantity = quantity(1, "kHz"),
        vbw: Optional[Quantity] = None,
        averages: int = 1,
    ) -> Quantity:
        """Read the level of a CW tone at `frequency` with marker 1 — the robust CW reading.

        Configures the analyzer for the tone, runs :meth:`single_sweep`, puts
        marker 1 on the peak and returns its level in dBm. `vbw` defaults to the
        RBW (fixed, never auto-coupled); `averages` > 1 averages that many sweeps
        on trace 1 (with the average type set by the caller, e.g.
        ``trace.set_average_type("POWer")``), 1 is a clear-write trace.

        Only the settings that changed since the previous call are sent (center,
        span, RBW, VBW, averaging); the one-time setup — dBm y-axis, RBW/VBW
        coupling off, trace 1 active, marker 1 a normal marker on trace 1 with no
        marker function — is sent on the first call and again after anything else
        has been written (see :meth:`write`). The sweep time is re-read only
        after a change. With a shared 10 MHz reference the tone sits on the
        center and a 5 kHz span is enough; without one use about 20 kHz, so the
        reference offset (±1.6 kHz at 1.6 GHz) stays on screen.
        """
        if not 1 <= int(averages) <= 999:
            raise ValueError(f"Averages must be 1–999, got {averages}.")
        if vbw is None:
            vbw = rbw
        wanted = {
            "center": c.hz(frequency),
            "span": c.hz(span),
            "rbw": c.hz(rbw),
            "vbw": c.hz(vbw),
            "averages": str(int(averages)),
        }
        marker = self.marker(1)
        with self._owned():
            if not self._cw_settings:
                self.write(":UNIT:POW DBM")
                self.bandwidth.set_rbw_auto(False)
                self.bandwidth.set_vbw_auto(False)
                self.trace.set_display_state("ACTIve", 1)
                marker.enable(True)
                marker.set_mode("POSition")
                marker.set_trace(1)
                marker.set_function("OFF")
            settings = self._cw_settings
            changed = False
            if settings.get("center") != wanted["center"]:
                self.frequency.set_center(frequency)
                changed = True
            if settings.get("span") != wanted["span"]:
                self.frequency.set_span(span)
                changed = True
            if settings.get("rbw") != wanted["rbw"]:
                self.bandwidth.set_rbw(rbw)
                changed = True
            if settings.get("vbw") != wanted["vbw"]:
                self.bandwidth.set_vbw(vbw)
                changed = True
            if settings.get("averages") != wanted["averages"]:
                if int(averages) > 1:
                    self.trace.set_type(1, "AVERage")
                    self.trace.set_average_count(int(averages), 1)
                else:
                    self.trace.set_type(1, "WRITe")
                changed = True
            settings.update(wanted)
            if changed or self._cw_sweep_s is None:
                self._cw_sweep_s = self.sweep_seconds()
            sweeps = max(int(averages), self.trace.sweeps_per_acquisition())
            self._single_sweep(self._cw_sweep_s, sweeps, None)
            marker.peak_search()
        return marker.get_y()

    def _shutdown_procedure(self) -> None:
        """Return the analyzer to continuous sweeping on close (``:INIT:CONT ON``)."""
        self.write(":INIT:CONT ON")
