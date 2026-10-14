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
  answer to the next query — for good: every later reply is then one behind.
  So a query that raises marks the session **out of step**, and the next query
  first resynchronises it (:meth:`SHA850A._resync`): it sends ``*IDN?`` and
  reads lines until the identity comes back, discarding the late reply and
  anything else in front of it. The error queue is asked on a short timeout.
- **Waiting with ``*OPC?``.** ``*OPC?`` "stops any new commands from being
  processed until the current processing is complete. Then it returns a '1'"
  (§10.5), so the driver waits with one ``*OPC?`` whose read timeout covers the
  operation, rather than polling it on the normal I/O timeout, and accepts only
  an exact ``1``. ``*OPC?`` is never re-sent while its ``1`` is owed: each one
  sent owes a reply, and a second would leave one ``1`` in flight. The
  ``*IDN?`` of the resynchronisation is held behind the operation like any
  other command, so its reply also means the operation is over.

Measurement sequence
--------------------
:meth:`SHA850A.single_sweep` runs ``:INIT:CONT OFF``, ``:INIT:IMM`` and
``*OPC?`` with a timeout of the number of sweeps × (the sweep time × 1.25 plus a
per-sweep overhead) plus a margin. When ``*OPC?`` does not answer ``1`` in time
the session is resynchronised (the late ``1`` is read there); when the ``1``
never comes but the session is in step again it sleeps the expected time instead
— the sister SSA3015X Plus has been seen to stall on ``*OPC?``, and SHA firmware
before 1.8R4 froze on it (see
:meth:`~labkit.instruments.drivers.siglent.system.System.require_firmware`).
When even the resynchronisation gets no answer, :class:`TimeoutError`: a marker
is never read on a session that is out of step.
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
from .amplitude import CORRECTION_SETS, Amplitude
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

#: The measured sweep takes longer than ``:SWE:TIME?``: that is the data-sampling
#: time only, without the scheduling time, which cannot be read ("Sweep Time
#: Estimate", §3.3.3). Each sweep is expected to take ``:SWE:TIME?`` × this factor
#: plus :data:`_PER_SWEEP_OVERHEAD_S`.
_SWEEP_OVERHEAD = 1.25
_PER_SWEEP_OVERHEAD_S = 0.2
#: Added to the ``*OPC?`` read timeout of a single sweep.
_OPC_MARGIN_S = 3.0
#: Added to the fallback sleep when ``*OPC?`` does not answer.
_SLEEP_MARGIN_S = 0.5
#: Sweep time assumed when ``:SWE:TIME?`` does not give a number.
_DEFAULT_SWEEP_S = 1.0
#: Read timeout of the error-queue query, which the SHA850A may not answer.
_ERROR_QUERY_TIMEOUT_S = 2.0
#: The most error-queue entries read by one :meth:`SHA850A.check_errors`.
_ERROR_QUEUE_READS = 32
#: The query whose reply resynchronises the socket: distinctive, and answered
#: in order behind a running operation (§10.5).
_SENTINEL = "*IDN?"
#: How long a resynchronisation waits for its sentinel, on top of the operation's
#: own time when it follows an ``*OPC?``.
_RESYNC_GRACE_S = 30.0
#: The ``*OPC?`` read timeout after a mode or measurement switch.
_MODE_SWITCH_TIMEOUT_S = 30.0
#: The error code of an undefined header (IEEE 488.2): a command or query the
#: instrument did not know — always an *earlier* one by the time ``:SYST:ERR?``
#: reports it.
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
        # Socket bookkeeping (see the module note): a query raised, so a late
        # reply may be on its way; sentinels sent and not yet read back; the
        # identity last read; read forms probed without an answer.
        self._out_of_sync = False
        self._owed_sentinels = 0
        self._identity: Optional[str] = None
        self._probed_headers: list[str] = []
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

    def query(self, command: str) -> str:
        """Send a SCPI query and return the reply (see :meth:`BaseInstrument.query`).

        Resynchronises first when an earlier query raised (:meth:`_resync`), and
        marks the session out of step when this one raises: on the raw socket
        its reply may still arrive, and would be read as the next query's.
        """
        if self._out_of_sync:
            self._resync(_RESYNC_GRACE_S)
        is_sentinel = command.strip().upper() == _SENTINEL
        try:
            reply = super().query(command)
        except BaseException:
            if self._can_read():
                self._out_of_sync = True
                if is_sentinel:
                    # Its late reply will look like the resynchronisation's own.
                    self._owed_sentinels += 1
            raise
        if is_sentinel:
            self._identity = reply.strip()
        return reply

    def _can_read(self) -> bool:
        """Whether the backend can be read without a query (a VISA resource; a mock cannot)."""
        return callable(getattr(self._backend, "read", None))

    def _is_identity(self, line: str) -> bool:
        """Whether `line` is the reply to the resynchronisation's ``*IDN?``."""
        if self._identity and line == self._identity:
            return True
        fields = [field.strip() for field in line.split(",")]
        return len(fields) >= 4 and ("siglent" in fields[0].lower() or fields[1].upper().startswith("SHA"))

    def _resync(self, budget_s: float) -> bool:
        """Bring the socket back in step after a query whose reply may still be on its way.

        Sends ``*IDN?`` and reads lines until its reply arrives, discarding
        everything in front of it: a late ``*OPC?`` ``1``, a stale reply to a
        query that timed out. ``*IDN?`` is held behind a running operation like
        any other command (§10.5), so its reply also means that operation is
        over. Returns whether a bare ``1`` — the late reply of an ``*OPC?`` — was
        among the discarded lines.

        Raises :class:`TimeoutError` when the identity has not come back within
        `budget_s`. The session stays out of step and the next query waits for
        that same reply again (no second ``*IDN?`` is sent while one is owed);
        reopen the connection if the analyzer was restarted. A backend that
        cannot be read without a query (a mock) cannot fall out of step: nothing
        to do.
        """
        read = getattr(self._backend, "read", None)
        if not callable(read):
            self._out_of_sync = False
            return False
        self._out_of_sync = True  # until the identity is back, even if this is interrupted
        if self._owed_sentinels == 0:
            self._backend.write(_SENTINEL)
            self._owed_sentinels = 1
        saw_opc = False
        failure: Optional[BaseException] = None
        deadline = time.monotonic() + budget_s
        while self._owed_sentinels:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                with self._read_timeout(remaining):
                    line = str(read()).strip()
            except Exception as exc:
                failure = exc
                break
            if self._is_identity(line):
                self._owed_sentinels -= 1
            elif line == "1":
                saw_opc = True
        if self._owed_sentinels:
            self._out_of_sync = True
            raise TimeoutError(
                f"Lost step with '{self._name}': a reply came late and the {_SENTINEL} sent to "
                f"resynchronise did not come back within {budget_s:g} s."
            ) from failure
        self._out_of_sync = False
        return saw_opc

    def _query_opc(self, timeout_s: float) -> bool:
        """Wait for the running operation with one ``*OPC?`` of up to `timeout_s`.

        ``True`` when the operation is known to be over: ``*OPC?`` answered
        exactly ``1``, or — after a timeout or any other reply — the
        resynchronisation read its late ``1``. ``False`` when that ``1`` never
        came but the session is in step again (or the backend cannot be read
        without a query): the caller decides — :meth:`single_sweep` sleeps,
        :meth:`wait_for_instrument` raises. Raises :class:`TimeoutError` when the
        session cannot be resynchronised.
        """
        if self._out_of_sync:
            self._resync(_RESYNC_GRACE_S)
        response: Optional[str]
        try:
            with self._read_timeout(timeout_s):
                response = self.query("*OPC?")
        except Exception:
            response = None
        if response is not None and response.strip() == "1":
            return True
        if not self._can_read():
            return False
        # Timed out, or read some other reply (a stale one): the "1" is still owed.
        return self._resync(timeout_s + _RESYNC_GRACE_S)

    def wait_for_instrument(self, timeout: Quantity = quantity(60, "s")) -> None:
        """Block until ``*OPC?`` answers, with a single query of up to `timeout`.

        Overrides the base, which polls ``*OPC?`` on the normal I/O timeout: on a
        raw socket an ``*OPC?`` that times out still answers later, and that late
        ``1`` would be read as the reply to the next query (see
        :meth:`_query_opc`). Raises :class:`TimeoutError` when no ``1`` comes.
        """
        if not self._query_opc(ensure_time(timeout).to("s").magnitude):
            raise TimeoutError(f"Timed out waiting for '{self._name}' to finish (*OPC?).")

    # -- error handling ----------------------------------------------------
    def check_errors(self, context: str) -> None:
        """Raise if the error queue reports an error.

        ``:SYSTem:ERRor?`` is not in the SHA850A's command list (§10.6), so it is
        asked on a short timeout, and nothing is raised when it gets no reply:
        the queue cannot be read (a reply that comes later is discarded by the
        next query's resynchronisation). Otherwise the queue is read until it
        reports ``0``/``+0`` or an empty reply (at most 32 entries), and every
        error in it is raised in one :class:`RuntimeError` — ``-113`` "undefined
        header" included: by the time ``:SYST:ERR?`` reports it, it names an
        *earlier* command the analyzer did not know. The one exception is the
        driver's own probing: a ``-113`` for a read form that
        :meth:`~labkit.instruments.drivers.siglent.measurement.Measurement.channel_power`
        tried and got no answer from is expected and skipped. Overload is shown
        on the screen only (``ADC_ERROR``, §11.2); this cannot see it.
        """
        probed, self._probed_headers = self._probed_headers, []
        errors: list[str] = []
        for _ in range(_ERROR_QUEUE_READS):
            try:
                with self._read_timeout(_ERROR_QUERY_TIMEOUT_S):
                    response = self.query(":SYST:ERR?").strip()
            except Exception:
                break
            code = _error_code(response)
            if not response or code == 0:
                break
            if not _expected_error(response, code, probed):
                errors.append(response)
        if errors:
            raise RuntimeError(f"{context}. Instrument error: {'; '.join(dict.fromkeys(errors))}")

    def _note_probe(self, command: str) -> None:
        """Remember a query the driver tried on purpose and got no answer to (see :meth:`check_errors`)."""
        self._probed_headers.append(command)

    # -- measurement / mode ------------------------------------------------
    def ensure_swept_sa(self) -> None:
        """Make the Swept SA measurement of Spectrum Analyzer mode the active one, and confirm it.

        "Only one [mode / measurement] can be activated at the same time" and
        each keeps its own state (§2): the span and RBW of channel power, say,
        are its own (§3.1.1, §3.2.1), so with another measurement left active at
        the front panel the swept-spectrum settings would not be the ones the
        sweep runs with. Reads ``:INST?`` and ``:INST:MEAS?`` and sends
        ``:INST SA`` / ``:INST:MEAS SA`` only where they differ (re-loading a
        mode is slow), then waits with ``*OPC?`` and reads both back.

        Raises :class:`RuntimeError` when the analyzer is not in Swept SA
        afterwards. Call it before configuring a swept measurement;
        :meth:`measure_cw` does, in its one-time setup.
        """
        mode = _enum_reply(self.measurement.get_mode())
        selected = _enum_reply(self.measurement.get_selected())
        if mode == "SA" and selected == "SA":
            return
        if mode != "SA":
            self.measurement.set_mode("SA")
        # After a mode switch the mode's last measurement comes back: select anyway.
        self.measurement.select("SA")
        self.wait_for_instrument(quantity(_MODE_SWITCH_TIMEOUT_S, "s"))
        mode = _enum_reply(self.measurement.get_mode())
        selected = _enum_reply(self.measurement.get_selected())
        if mode != "SA" or selected != "SA":
            raise RuntimeError(
                f"'{self._name}' did not switch to the Swept SA measurement (mode {mode or '?'}, "
                f"measurement {selected or '?'}): select Spectrum Analyzer > Swept SA at the analyzer."
            )

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
        The ``*OPC?`` read timeout is `timeout`, or `sweeps` × (the sweep time
        (``:SWE:TIME?``) × 1.25 + 0.2 s) plus 3 s. When ``*OPC?`` does not answer
        ``1`` in time the session is resynchronised, which reads the late ``1``;
        when that ``1`` never comes but the session is in step again, the method
        sleeps the expected time (+ 0.5 s) instead. :class:`TimeoutError` when
        the session cannot be resynchronised.
        """
        count = int(sweeps) if sweeps is not None else self.trace.sweeps_per_acquisition()
        self._single_sweep(self.sweep_seconds(), max(count, 1), timeout)

    def _single_sweep(self, sweep_s: float, sweeps: int, timeout: Optional[Quantity]) -> None:
        expected_s = sweeps * (sweep_s * _SWEEP_OVERHEAD + _PER_SWEEP_OVERHEAD_S)
        opc_s = ensure_time(timeout).to("s").magnitude if timeout is not None else expected_s + _OPC_MARGIN_S
        if self._out_of_sync:
            self._resync(_RESYNC_GRACE_S)
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
        ``trace.set_average_type("POWer")``), 1 is a clear-write trace. Every
        setting is checked before the first write, so a refused one
        (:class:`ValueError`) leaves the analyzer as it was.

        Only the settings that changed since the previous call are sent (center,
        span, RBW, VBW, averaging). The one-time setup is sent on the first call
        and again after anything else has been written (see :meth:`write`) or a
        call failed part-way: the Swept SA measurement (:meth:`ensure_swept_sa`),
        the dBm y-axis, no reference level offset (the displayed reference level
        is kept, see :meth:`_clear_ref_level_offset`), no peak threshold or
        excursion criteria, every amplitude correction set off — front-panel
        settings that would shift or move the reading —, RBW/VBW coupling off,
        trace 1 active, and marker 1 a normal marker on trace 1 with no marker
        function. The sweep time is re-read only after a change. With a shared
        10 MHz reference the tone sits on the center and a 5 kHz span is enough;
        without one use about 20 kHz, so the reference offset (±1.6 kHz at
        1.6 GHz) stays on screen.
        """
        if not 1 <= int(averages) <= 999:
            raise ValueError(f"Averages must be 1–999, got {averages}.")
        if vbw is None:
            vbw = rbw
        self.frequency.check_center(frequency)
        self.frequency.check_span(span)
        self.bandwidth.check_rbw(rbw)
        self.bandwidth.check_vbw(vbw)
        wanted = {
            "center": c.hz(frequency),
            "span": c.hz(span),
            "rbw": c.hz(rbw),
            "vbw": c.hz(vbw),
            "averages": str(int(averages)),
        }
        marker = self.marker(1)
        with self._owned():
            configured = False
            try:
                if not self._cw_settings:
                    self._cw_setup(marker)
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
                sweep_s = self._cw_sweep_s
                if changed or sweep_s is None:
                    sweep_s = self.sweep_seconds()
                    self._cw_sweep_s = sweep_s
                settings.update(wanted)
                configured = True
            finally:
                if not configured:
                    # Part of the configuration may have been sent: the memory
                    # no longer says what the analyzer has, so the next call
                    # sends everything again.
                    self.forget_cw_settings()
            sweeps = max(int(averages), self.trace.sweeps_per_acquisition())
            self._single_sweep(sweep_s, sweeps, None)
            marker.peak_search()
        return self._read_marker_level(marker)

    def _cw_setup(self, marker: Marker) -> None:
        """The one-time setup of :meth:`measure_cw` (see its docstring)."""
        self.ensure_swept_sa()
        self.write(":UNIT:POW DBM")
        self._clear_ref_level_offset()
        marker.set_peak_threshold_enabled(False)
        marker.set_peak_excursion_enabled(False)
        for number in CORRECTION_SETS:
            self.amplitude.set_correction(number, False)
        self.bandwidth.set_rbw_auto(False)
        self.bandwidth.set_vbw_auto(False)
        self.trace.set_display_state("ACTIve", 1)
        marker.enable(True)
        marker.set_mode("POSition")
        marker.set_trace(1)
        marker.set_function("OFF")

    def _clear_ref_level_offset(self) -> None:
        """Set the reference level offset to 0 dB, keeping the displayed reference level.

        The offset "changes both the reference level readout and the amplitude
        readout of the marker; but does not impact the position of traces"
        (§3.4.4): with 10 dB left on at the front panel every marker reads 10 dB
        high. The displayed reference level is what a caller set (it includes the
        offset), so it is read first and set again after the offset is cleared —
        the analyzer then works at the reference level the caller asked for.
        Nothing is sent when the offset is already 0.
        """
        offset = self.amplitude.get_ref_level_offset().to("dB").magnitude
        if abs(offset) < 1e-9:
            return
        reference = self.amplitude.get_ref_level()
        self.amplitude.check_ref_level(reference)
        self.amplitude.set_ref_level_offset(quantity(0, "dB"))
        self.amplitude.set_ref_level(reference)

    def _read_marker_level(self, marker: Marker) -> Quantity:
        """Marker `marker`'s level in dBm, read on a session that is in step.

        A bare ``1`` is what an ``*OPC?`` answers; read where a level was asked
        for it means a late ``*OPC?`` reply got in front: the session is
        resynchronised (which discards the level queued behind it) and the
        marker read again.
        """
        command = f":CALC:MARK{marker.number}:Y?"
        reply = self.query(command)
        if reply.strip() == "1" and self._can_read():
            self._out_of_sync = True
            reply = self.query(command)
        return c.as_power(reply)

    def _shutdown_procedure(self) -> None:
        """Return the analyzer to continuous sweeping on close (``:INIT:CONT ON``)."""
        self.write(":INIT:CONT ON")


def _enum_reply(response: str) -> str:
    """An enumeration reply (``SA``, ``"CHP"``) in upper case, without quotes."""
    return response.strip().strip('"').strip().upper()


def _error_code(response: str) -> Optional[int]:
    """The number in front of an error-queue entry (``-222,"Data out of range"`` -> -222)."""
    try:
        return int(float(response.split(",", 1)[0]))
    except ValueError:
        return None


def _expected_error(response: str, code: Optional[int], probed: list[str]) -> bool:
    """Whether an error-queue entry is the driver's own doing, consuming the probe it explains.

    Only an "undefined header" (``-113``) can be: one that names a header the
    driver probed on purpose, or ``SYST:ERR`` itself; or one that names no
    header at all while a probe is unaccounted for.
    """
    lowered = response.lower()
    if code != _UNDEFINED_HEADER and not (code is None and "undefined header" in lowered):
        return False
    message = response.split(",", 1)[1] if code is not None and "," in response else response
    text = message.upper()
    if "SYST:ERR" in text or "SYSTEM:ERROR" in text:
        return True
    for header in probed:
        if header.strip().lstrip(":").rstrip("?").upper() in text:
            probed.remove(header)
            return True
    names_header = any(mark in message for mark in ":*?")
    if not names_header and probed:
        probed.pop(0)
        return True
    return False
