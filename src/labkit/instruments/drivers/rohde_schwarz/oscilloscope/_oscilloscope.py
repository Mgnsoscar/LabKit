"""Shared base for Rohde & Schwarz RTO6-family oscilloscopes.

A concrete model (:class:`~labkit.instruments.drivers.rohde_schwarz.oscilloscope.rto64.RTO64`)
is this base plus its identity — channel count, bandwidth, sample rate. All
command logic lives here, composed from per-topic menus, so another RTO6 model
(an RTO62, say) reuses it instead of a copy-pasted driver.

The instrument is controlled over VXI-11/HiSLIP with the standard
``TCPIP::<ip>::INSTR`` resource name. Commands follow the *R&S RTO6 User
Manual* (1801.6687.02), chapter 24 "Remote control commands"; the RTO6 shares
its command set with the RTO2000/RTP family.

Acquisition control
-------------------
``RUN`` starts continuous acquisition, ``RUNSingle`` takes the number of
acquisitions set with ``ACQuire:COUNt`` and stops, ``STOP`` stops. The
commands are asynchronous, so :meth:`Oscilloscope.run_single` waits with
``*OPC?`` before returning — the record is complete when it does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .....units import Quantity, quantity
from ....base import Backend, BaseInstrument
from .acquisition import Acquisition
from .channel import Channel
from .history import History
from .math import Math
from .measurement import Measurement
from .system import System
from .timebase import Timebase
from .trigger import Trigger
from .waveform import Waveform

if TYPE_CHECKING:
    from ....environment import TestEnvironment

__all__ = ["Oscilloscope"]


class Oscilloscope(BaseInstrument):
    """Common driver logic for R&S RTO6-family oscilloscopes (TCP/IP).

    Concrete models subclass this and set :attr:`channel_count`,
    :attr:`bandwidth` and :attr:`max_sample_rate`; they inherit the menus and
    control methods below. The failsafe :meth:`_shutdown_procedure` switches
    the display update back on and returns the scope to continuous
    acquisition, so it is usable at the front panel when a session ends.
    """

    #: Number of analog input channels.
    channel_count: int
    #: Analog bandwidth of the model (with its bandwidth option).
    bandwidth: Quantity
    #: Maximum real-time sample rate.
    max_sample_rate: Quantity
    #: Number of math waveforms.
    math_count: int = 8

    timebase: Timebase
    acquisition: Acquisition
    trigger: Trigger
    waveform: Waveform
    history: History
    measurement: Measurement
    math: Math
    system: System

    def __init__(
        self,
        environment: "TestEnvironment",
        name: str,
        address: str,
        timeout: Quantity = quantity(10, "s"),
        backend: Optional[Backend] = None,
    ) -> None:
        super().__init__(environment, name, address, timeout, backend=backend)
        self.timebase = Timebase(self)
        self.acquisition = Acquisition(self)
        self.trigger = Trigger(self)
        self.waveform = Waveform(self)
        self.history = History(self)
        self.measurement = Measurement(self)
        self.math = Math(self)
        self.system = System(self)
        self._channels = {n: Channel(self, n) for n in range(1, self.channel_count + 1)}

    def _build_address(self, address: str) -> str:
        """``"192.168.0.30"`` -> ``"TCPIP::192.168.0.30::INSTR"``."""
        return f"TCPIP::{address}::INSTR"

    # -- checks --------------------------------------------------------------
    def check_channel(self, number: int) -> None:
        """Raise :class:`ValueError` unless `number` is one of the model's channels."""
        if not 1 <= int(number) <= self.channel_count:
            raise ValueError(f"Channel must be between 1 and {self.channel_count}, got {number}.")

    def check_math(self, number: int) -> None:
        if not 1 <= int(number) <= self.math_count:
            raise ValueError(f"Math waveform must be between 1 and {self.math_count}, got {number}.")

    # -- channels --------------------------------------------------------------
    def channel(self, number: int) -> Channel:
        """The settings menu of analog channel `number`."""
        self.check_channel(number)
        return self._channels[number]

    @property
    def channels(self) -> tuple[Channel, ...]:
        """All analog channels, in order."""
        return tuple(self._channels[n] for n in range(1, self.channel_count + 1))

    # -- acquisition control -----------------------------------------------------
    def run(self) -> None:
        """Start continuous acquisition (``RUN``)."""
        self.write("RUN")

    def run_single(self, wait_for_completion: bool = True) -> None:
        """Take ``ACQuire:COUNt`` acquisitions and stop (``RUNS``); waits with ``*OPC?`` by default."""
        self.write("RUNS")
        if wait_for_completion:
            self.wait_for_instrument()

    def stop(self) -> None:
        """Stop the running acquisition (``STOP``)."""
        self.write("STOP")

    def autoscale(self) -> None:
        """Let the instrument set horizontal, vertical and trigger settings from the signal (``AUT``).

        Handy interactively; Rohde & Schwarz advise against it in automated tests,
        where the settings should be explicit.
        """
        self.write("AUT")
        self.wait_for_instrument()

    def acquire(self, channel: int, waveform: int = 1) -> tuple[Quantity, Quantity]:
        """One single acquisition, then the channel's record as ``(time, voltage)``."""
        self.check_channel(channel)
        self.run_single(wait_for_completion=True)
        return self.waveform.get_data(channel, waveform)

    def _shutdown_procedure(self) -> None:
        """Display update on and continuous acquisition, so the scope is usable locally."""
        self.write("SYST:DISP:UPD ON")
        self.write("RUN")
