"""Shared base for Keysight/Agilent MXG analog signal generators.

A concrete model (:class:`~labkit.instruments.drivers.keysight.n5183a.N5183A`)
is this base plus its identity: the frequency and level ranges of that model.
All command logic lives here, composed from per-topic menus, so another MXG
analog generator (an N5181A, say) reuses it instead of copy-pasting a driver.

Connection
----------
The MXG is a full SCPI-99 instrument reachable over LAN (VXI-11 or sockets),
USB and GPIB. The driver addresses it by the standard VXI-11 resource name,
``TCPIP::<ip>::INSTR``.

Read-back
---------
Unlike the Aim-TTi TGR6000, every MXG setting has a query form: the menus
expose ``get_*`` counterparts for the settings a measurement is likely to
verify (frequency, level, modulation parameters, sweep state).

Commands follow the *Agilent N5161A/62A/81A/82A/83A MXG Signal Generators SCPI
Command Reference* (N5180-90004). The short-form mnemonics are used and the
optional ``[:SOURce]`` root is left implicit, as the instrument accepts both.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ....units import Quantity, quantity
from ...base import Backend, BaseInstrument
from .frequency import Frequency
from .modulation import Modulation
from .power import Power
from .reference import Reference
from .sweep import Sweep
from .system import System

if TYPE_CHECKING:
    from ...environment import TestEnvironment

__all__ = ["AnalogSignalGenerator"]


class AnalogSignalGenerator(BaseInstrument):
    """Common driver logic for Keysight/Agilent MXG analog signal generators.

    Concrete models subclass this and set :attr:`frequency_range` and
    :attr:`level_range`; they inherit the menus and control methods below. The
    failsafe :meth:`_shutdown_procedure` forces the RF output **off** so the
    bench is left safe when a session ends, however it ends.
    """

    #: Inclusive ``(min, max)`` carrier-frequency range of the model.
    frequency_range: tuple[Quantity, Quantity]
    #: Inclusive ``(min, max)`` settable output-level range of the model.
    level_range: tuple[Quantity, Quantity]

    frequency: Frequency
    power: Power
    modulation: Modulation
    sweep: Sweep
    reference: Reference
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
        self.frequency = Frequency(self)
        self.power = Power(self)
        self.modulation = Modulation(self)
        self.sweep = Sweep(self)
        self.reference = Reference(self)
        self.system = System(self)

    def _build_address(self, address: str) -> str:
        """``"192.168.0.10"`` -> ``"TCPIP::192.168.0.10::INSTR"``."""
        return f"TCPIP::{address}::INSTR"

    # -- convenience -------------------------------------------------------
    def set_rf_enabled(self, enabled: bool) -> None:
        """Switch the RF output on/off (delegates to :meth:`Power.set_rf_enabled`)."""
        self.power.set_rf_enabled(enabled)

    def set_cw(self, frequency: Quantity, level: Quantity, rf_on: bool = True) -> None:
        """Configure a CW tone: stop any sweep, set frequency and level, and enable RF.

        Convenience for the most common use — ``FREQ:MODE CW`` and
        ``POW:MODE FIX`` are sent first so a previously configured sweep does
        not override the values.
        """
        self.frequency.set_mode("CW")
        self.power.set_mode("FIXED")
        self.frequency.set_frequency(frequency)
        self.power.set_level(level)
        self.power.set_rf_enabled(rf_on)

    def run_self_test(self) -> bool:
        """Run the instrument self-test (``*TST?``); return ``True`` if it passes."""
        return self.system.self_test()

    def trigger(self) -> None:
        """Issue a bus trigger (``*TRG``) for a sweep whose trigger source is ``BUS``."""
        self.write("*TRG")

    # -- error handling ----------------------------------------------------
    def check_errors(self, context: str) -> None:
        """Raise if the error queue (``SYST:ERR?``) is non-empty.

        Overrides the base because the MXG reports an empty queue as
        ``+0,"No error"`` — with a leading ``+`` that the base's ``startswith("0")``
        test would misread as an error.
        """
        response = self.query("SYST:ERR?").strip()
        if not response:
            return
        code_text = response.split(",", 1)[0]
        try:
            code = int(float(code_text))
        except ValueError:
            code = -1
        if code != 0:
            raise RuntimeError(f"{context}. Instrument error: {response}")

    # -- failsafe shutdown -------------------------------------------------
    def _shutdown_procedure(self) -> None:
        """Force the RF output **off** (``OUTP OFF``) before the session closes."""
        self.write("OUTP OFF")
