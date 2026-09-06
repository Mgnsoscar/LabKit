"""Shared base for Rohde & Schwarz ZNL/ZNLE-family vector network analyzers.

A concrete model (:class:`~labkit.instruments.drivers.rohde_schwarz.vna.znle18.ZNLE18`)
is this base plus its identity — the frequency range and port count of that model.
All command logic lives here, composed from per-topic menus, so another
ZNL/ZNLE-family model reuses it instead of a copy-pasted driver.

The instrument is controlled over VXI-11/HiSLIP with the standard
``TCPIP::<ip>::INSTR`` VISA resource name (a raw socket is not required, unlike the
Aim-TTi generators). Commands follow the *R&S ZNL/ZNLE User Manual*
(1178.5966.02, issue 23), chapter 11.5.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np

from .....units import Quantity, quantity
from ....base import Backend, BaseInstrument
from .average import Average
from .bandwidth import Bandwidth
from .calibration import Calibration
from .channel import Channel
from .display import Display
from .frequency import Frequency
from .marker import Marker
from .power import Power
from .sweep import Sweep
from .trace import Trace

if TYPE_CHECKING:
    from ....environment import TestEnvironment

__all__ = ["NetworkAnalyzer"]


class NetworkAnalyzer(BaseInstrument):
    """Common driver logic for R&S ZNL/ZNLE-family VNAs (TCP/IP).

    Concrete models subclass this and set :attr:`frequency_range` and
    :attr:`port_count`; they inherit the menus and control methods below. The
    failsafe :meth:`_shutdown_procedure` switches the RF source output **off** so
    the connected DUT is left un-driven when a session ends.
    """

    #: Inclusive ``(min, max)`` stimulus-frequency range of the model.
    frequency_range: tuple[Quantity, Quantity]
    #: Number of physical test ports.
    port_count: int

    channel: Channel
    frequency: Frequency
    trace: Trace
    sweep: Sweep
    bandwidth: Bandwidth
    power: Power
    average: Average
    calibration: Calibration
    display: Display

    def __init__(
        self,
        environment: "TestEnvironment",
        name: str,
        address: str,
        timeout: Quantity = quantity(10, "s"),
        backend: Optional[Backend] = None,
    ) -> None:
        super().__init__(environment, name, address, timeout, backend=backend)
        self.channel = Channel(self)
        self.frequency = Frequency(self)
        self.trace = Trace(self)
        self.sweep = Sweep(self)
        self.bandwidth = Bandwidth(self)
        self.power = Power(self)
        self.average = Average(self)
        self.calibration = Calibration(self)
        self.display = Display(self)

    def _build_address(self, address: str) -> str:
        """``"192.168.0.20"`` -> ``"TCPIP::192.168.0.20::INSTR"``."""
        return f"TCPIP::{address}::INSTR"

    # -- markers -----------------------------------------------------------
    def marker(self, number: int = 1, channel: int = 1, enable: bool = False) -> Marker:
        """Return marker `number` on `channel` (optionally switching it on)."""
        marker = Marker(self, number, channel)
        if enable:
            marker.enable(True)
        return marker

    # -- measurement control ----------------------------------------------
    def trigger(self, channel: int = 1, wait_for_completion: bool = False) -> None:
        """Start a measurement (``INIT<Ch>:IMM``); optionally block until it finishes."""
        self.write(f"INIT{channel}:IMM")
        if wait_for_completion:
            self.wait_for_instrument()

    def stop_sweep(self, channel: int = 1) -> None:
        """Stop the running measurement sequence (``INIT<Ch>:STOP``)."""
        self.write(f"INIT{channel}:STOP")

    def measure(self, channel: int = 1) -> tuple[Quantity, np.ndarray]:
        """Run one single sweep and return the active trace as complex data.

        Switches to single-sweep mode, triggers one sweep, waits for completion,
        and returns ``(stimulus, complex_values)`` for the channel's active trace
        (frequency quantity array and complex numpy array).
        """
        self.sweep.set_continuous(False, channel)
        self.trigger(channel, wait_for_completion=True)
        return self.trace.get_complex_data(channel)

    def _shutdown_procedure(self) -> None:
        """Switch the RF source output off (``OUTP OFF``) before the session closes."""
        self.write("OUTP OFF")
