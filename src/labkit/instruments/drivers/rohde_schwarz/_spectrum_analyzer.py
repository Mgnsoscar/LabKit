"""Shared base for Rohde & Schwarz FSV-family spectrum analyzers.

The FSV3007 and FPL1003 (and other FSV-family analyzers) share the same SCPI
command set and the same set of menus, so the composition lives here once. A
concrete model is then just a subclass with its own identity and, where needed,
model-specific extras — instead of a copy-pasted driver per instrument.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ....units import Quantity, quantity
from ...base import Backend, BaseInstrument
from .amplitude import Amplitude
from .bandwidth import Bandwidth
from .frequency import Frequency
from .marker import Marker
from .measurement import Measurement
from .noise_figure import NoiseFigure
from .sweep import Sweep
from .system import Display, ReferenceOscillator
from .trace import Trace

if TYPE_CHECKING:
    from ...environment import TestEnvironment

__all__ = ["SpectrumAnalyzer"]


class SpectrumAnalyzer(BaseInstrument):
    """Common driver logic for R&S FSV-family spectrum analyzers (TCP/IP).

    Concrete models (:class:`FSV3007`, :class:`FPL1003`) subclass this; they
    inherit all the menus and measurement control below and typically only add
    their own docstring/identity.
    """

    frequency: Frequency
    bandwidth: Bandwidth
    sweep: Sweep
    amplitude: Amplitude
    trace: Trace
    display: Display
    reference: ReferenceOscillator
    measurement: Measurement
    noise_figure: NoiseFigure

    def __init__(
        self,
        environment: "TestEnvironment",
        name: str,
        address: str,
        timeout: Quantity = quantity(10, "s"),
        backend: Optional[Backend] = None,
    ) -> None:
        super().__init__(environment, name, address, timeout, backend=backend)
        self.frequency = Frequency(self)
        self.bandwidth = Bandwidth(self)
        self.sweep = Sweep(self)
        self.amplitude = Amplitude(self)
        self.trace = Trace(self)
        self.display = Display(self)
        self.reference = ReferenceOscillator(self)
        self.measurement = Measurement(self)
        self.noise_figure = NoiseFigure(self)

    def _build_address(self, address: str) -> str:
        """``"192.168.0.10"`` -> ``"TCPIP::192.168.0.10::INSTR"``."""
        return f"TCPIP::{address}::INSTR"

    # -- measurement channels / applications ------------------------------
    def create_channel(self, channel_type: str, name: str) -> None:
        """Add a measurement channel/application (``INST:CRE <type>,'<name>'``).

        `channel_type` is an R&S channel-type mnemonic, e.g. ``"SANALYZER"``
        (Spectrum), ``"IQ"`` (I/Q Analyzer), ``"ADEM"`` (analog demod) or
        ``"NOISe"`` (Noise Figure, requires the K30 option).
        """
        self.write(f"INST:CRE {channel_type},'{name}'")

    def select_channel(self, name: str) -> None:
        """Activate an existing measurement channel by name (``INST:SEL '<name>'``)."""
        self.write(f"INST:SEL '{name}'")

    def delete_channel(self, name: str) -> None:
        """Delete a measurement channel by name (``INST:DEL '<name>'``)."""
        self.write(f"INST:DEL '{name}'")

    def list_channels(self) -> list[tuple[str, str]]:
        """List channels as ``(type, name)`` pairs (``INST:LIST?``)."""
        items = [x.strip().strip("'\"") for x in self.query("INST:LIST?").split(",")]
        items = [x for x in items if x != ""]
        return [(items[i], items[i + 1]) for i in range(0, len(items) - 1, 2)]

    # -- markers -----------------------------------------------------------
    def marker(self, number: int = 1, enable: bool = False) -> Marker:
        """Return the marker with the given number (optionally switching it on)."""
        marker = Marker(self, number)
        if enable:
            marker.enable(True)
        return marker

    # -- measurement control ----------------------------------------------
    def trigger(self, wait_for_completion: bool = False) -> None:
        """Start a measurement (``INIT``); optionally block until it finishes."""
        self.write("INIT")
        if wait_for_completion:
            self.wait_for_instrument()

    def abort(self) -> None:
        """Abort the running measurement (``ABOR``)."""
        self.write("ABOR")

    def measure_trace(self, trace: int = 1) -> tuple[Quantity, Quantity]:
        """Run one single sweep and return the trace as ``(frequencies, levels)``."""
        self.sweep.set_continuous(False)
        self.trigger(wait_for_completion=True)
        return self.trace.get_data(trace)

    def _shutdown_procedure(self) -> None:
        """Return the instrument to continuous sweeping on close."""
        self.write("INIT:CONT ON")
