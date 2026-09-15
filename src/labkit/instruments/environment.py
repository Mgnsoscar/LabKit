"""The user-facing test environment.

A :class:`TestEnvironment` owns the shared VISA resource manager and the set of
instruments a measurement uses. You subclass it, declare your instruments as
annotations for editor autocompletion, and create them in
:meth:`_configure_instruments`::

    class MyBench(TestEnvironment):
        analyzer: FSV3007
        source: TGR6000

        def _configure_instruments(self) -> None:
            self.analyzer = FSV3007(self, "Spectrum Analyzer", "192.168.0.10")
            self.source = TGR6000(self, "Signal Generator", "192.168.0.11")

    bench = MyBench()                             # talks to real hardware
    bench = MyBench(use_dummy_instruments=True)   # prints SCPI, no hardware

One bench, many modules
-----------------------
A measurement project usually defines its bench in one module and uses it from
many scripts and helper modules. Each of those must **not** construct its own
``MyBench()`` — every construction opens a new VISA session to every
instrument. Use :meth:`TestEnvironment.instance` instead, which builds the
bench the first time and hands the same object back afterwards::

    bench = MyBench.instance()                    # anywhere, as often as you like

`pyvisa` is imported only when a real resource manager is created, so dummy
mode needs neither `pyvisa` nor any instrument attached.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional, TypeVar

from .base import BaseInstrument

__all__ = ["TestEnvironment"]

_E = TypeVar("_E", bound="TestEnvironment")


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

    _instances: ClassVar[dict[tuple[type, tuple[tuple[str, Any], ...]], "TestEnvironment"]] = {}

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

    # -- one shared instance ----------------------------------------------
    @classmethod
    def instance(cls: type[_E], **kwargs: Any) -> _E:
        """Return the shared bench, constructing it on first use.

        Keyword arguments are passed to the constructor the first time and
        identify the instance afterwards: ``MyBench.instance()`` and
        ``MyBench.instance(use_dummy_instruments=True)`` are two different
        benches, each built once. Every module in a project can call this and
        get the same connected instruments back — no reconnecting.
        """
        key = (cls, tuple(sorted(kwargs.items())))
        bench = TestEnvironment._instances.get(key)
        if bench is None:
            bench = cls(**kwargs)
            TestEnvironment._instances[key] = bench
        return bench  # type: ignore[return-value]

    @classmethod
    def discard_instance(cls, **kwargs: Any) -> None:
        """Close the shared bench built with these arguments (if any) and forget it.

        The next :meth:`instance` call constructs a fresh one. Mainly for tests
        and for recovering from a lost connection.
        """
        key = (cls, tuple(sorted(kwargs.items())))
        bench = TestEnvironment._instances.pop(key, None)
        if bench is not None:
            bench.close()

    # -- lifecycle ---------------------------------------------------------
    @property
    def instruments(self) -> list[BaseInstrument]:
        """Every :class:`BaseInstrument` attribute of this bench."""
        return [v for v in vars(self).values() if isinstance(v, BaseInstrument)]

    def close(self) -> None:
        """Close every instrument on the bench (each runs its failsafe shutdown)."""
        for instrument in self.instruments:
            instrument.close()

    @staticmethod
    def reset_instruments(
        *instruments: BaseInstrument,
        wait_for_instruments: bool = True,
    ) -> None:
        """Reset each of the given instruments."""
        for instrument in instruments:
            instrument.reset_instrument(wait_for_instruments)
