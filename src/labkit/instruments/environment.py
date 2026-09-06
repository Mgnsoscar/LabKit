"""The user-facing test environment.

A :class:`TestEnvironment` owns the shared VISA resource manager and the set of
instruments a measurement uses. You subclass it, declare your instruments as
annotations for editor autocompletion, and create them in
:meth:`_configure_instruments`::

    class MyBench(TestEnvironment):
        analyzer: FSV3007
        source: TGR

        def _configure_instruments(self) -> None:
            self.analyzer = FSV3007(self, "Spectrum Analyzer", "192.168.0.10")
            self.source = TGR(self, "Signal Generator", "192.168.0.11")

    bench = MyBench()                       # talks to real hardware
    bench = MyBench(use_dummy_instruments=True)   # prints SCPI, no hardware

`pyvisa` is imported only when a real resource manager is created, so dummy
mode needs neither `pyvisa` nor any instrument attached.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .base import BaseInstrument

__all__ = ["TestEnvironment"]


class TestEnvironment(ABC):
    """Base class for a bench of instruments used by a measurement.

    Parameters
    ----------
    use_dummy_instruments:
        If ``True``, no VISA resource manager is created and instruments run in
        dummy mode (SCPI is printed, not sent).
    visa_backend:
        ``"auto"`` to let PyVISA choose, or ``"@py"`` for the pure-Python
        pyvisa-py backend. Ignored in dummy mode.
    """

    #: The VISA resource manager shared by this environment's instruments, or
    #: ``None`` in dummy mode.
    resource_manager: Optional[Any]

    def __init__(
        self,
        use_dummy_instruments: bool = False,
        visa_backend: str = "auto",
    ) -> None:
        if use_dummy_instruments:
            self.resource_manager = None
        else:
            import pyvisa

            self.resource_manager = (
                pyvisa.ResourceManager()
                if visa_backend == "auto"
                else pyvisa.ResourceManager(visa_backend)
            )
        self._configure_instruments()

    @abstractmethod
    def _configure_instruments(self) -> None:
        """Create and configure every instrument in the environment."""
        ...

    @staticmethod
    def reset_instruments(
        *instruments: BaseInstrument,
        wait_for_instruments: bool = True,
    ) -> None:
        """Reset each of the given instruments."""
        for instrument in instruments:
            instrument.reset_instrument(wait_for_instruments)
