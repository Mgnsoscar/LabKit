"""Shared base for Aim-TTi TGR-family RF signal generators.

A concrete model (:class:`~labkit.instruments.drivers.aim_tti.tgr6000.TGR6000`)
is this base plus its identity: the frequency and level ranges of that model.
All command logic lives here, composed from per-topic menus, so a future
TGR-family generator reuses it instead of copy-pasting a driver.

Connection
----------
The TGR6000 is controlled over a **raw TCP socket on port 9221** with **line-feed
(``\\n``) command terminators**; replies are terminated with ``CR`` ``LF``. It has
only VXI-11 *discovery* support, so it must be addressed by its raw-socket VISA
resource name, ``TCPIP0::<ip>::9221::SOCKET`` (Instruction Manual Iss 9, "VISA
Resource Name" / "TCP Sockets"). The parent transport uses ``\\n`` for both read
and write termination; the trailing ``CR`` on replies is stripped when parsed.

Read-back
---------
The TGR remote language is largely *set-only*: there are **no query forms** for
frequency (``FREQ``) or output level (``DBMLEV`` etc.), so those cannot be read
back over the interface. The queries that do exist (sweep status, error queues,
self-test, ``*IDN?``) are exposed by the relevant menus.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ....units import Quantity, quantity
from ...base import Backend, BaseInstrument
from .frequency import Frequency
from .modulation import Modulation
from .output import Output
from .reference import Reference
from .sweep import Sweep
from .system import System

if TYPE_CHECKING:
    from ...environment import TestEnvironment

__all__ = ["SignalGenerator"]


class SignalGenerator(BaseInstrument):
    """Common driver logic for Aim-TTi TGR-family RF signal generators (TCP/IP).

    Concrete models subclass this and set :attr:`frequency_range` and
    :attr:`level_range`; they inherit the menus and control methods below. The
    failsafe :meth:`_shutdown_procedure` forces the RF output **off** so the
    bench is left safe when a session ends, however it ends.
    """

    #: Inclusive ``(min, max)`` carrier-frequency range of the model.
    frequency_range: tuple[Quantity, Quantity]
    #: Inclusive ``(min, max)`` output-level range of the model.
    level_range: tuple[Quantity, Quantity]

    frequency: Frequency
    output: Output
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
        self.output = Output(self)
        self.modulation = Modulation(self)
        self.sweep = Sweep(self)
        self.reference = Reference(self)
        self.system = System(self)

    def _build_address(self, address: str) -> str:
        """``"192.168.0.10"`` -> ``"TCPIP0::192.168.0.10::9221::SOCKET"``.

        The TGR6000 is a raw-socket instrument on TCP port 9221 (it has no full
        VXI-11 support), so it must be addressed by raw-socket resource name.
        """
        return f"TCPIP0::{address}::9221::SOCKET"

    # -- convenience -------------------------------------------------------
    def set_rf_enabled(self, enabled: bool) -> None:
        """Switch the RF output on/off (delegates to :meth:`Output.set_rf_enabled`)."""
        self.output.set_rf_enabled(enabled)

    def run_self_test(self) -> bool:
        """Run the instrument self-test (``*TST?``); return ``True`` if it passes."""
        return self.system.self_test()

    def trigger(self) -> None:
        """Issue a manual trigger (``*TRG``), equivalent to the front-panel TRIG key."""
        self.write("*TRG")

    # -- error handling ----------------------------------------------------
    def check_errors(self, context: str) -> None:
        """Raise if the Execution Error Register (``EER?``) is non-zero.

        Overrides the base, which uses the SCPI-99 ``SYST:ERR?`` queue that the
        TGR6000 does not implement.
        """
        error = self.query("EER?").strip()
        if error and not error.startswith("0"):
            raise RuntimeError(f"{context}. Instrument error: {error}")

    # -- failsafe shutdown -------------------------------------------------
    def _shutdown_procedure(self) -> None:
        """Force the RF output **off** (``RFOFF``) before the session closes."""
        self.write("RFOFF")
