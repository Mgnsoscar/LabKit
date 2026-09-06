"""Base classes for SCPI/VISA instruments.

:class:`BaseInstrument` wraps a communication backend and provides the SCPI
plumbing every instrument shares: ``*IDN?``, ``*RST``, ``*OPC?`` completion
waiting, error checking, and a *failsafe* ``close`` that is guaranteed to run at
interpreter exit (see :mod:`labkit.instruments.registry`).

:class:`Menu` groups related commands into a sub-object, so a driver can expose
``analyzer.sweep.set_span(...)`` and ``analyzer.trace.get_data()`` instead of
one flat namespace of methods.

Offline use
-----------
Pass an environment whose ``resource_manager`` is ``None`` (or a
:class:`DummyBackend` directly) to exercise driver logic without hardware: SCPI
commands are printed and recorded instead of sent. This means the instrument
layer — and its tests — do not require `pyvisa` or a physical instrument.
`pyvisa` is imported only when a real VISA resource is opened.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Lock
from time import perf_counter, sleep
from typing import TYPE_CHECKING, Any, Optional, Protocol, runtime_checkable

from ..units import Quantity, quantity
from . import registry

if TYPE_CHECKING:
    from .environment import TestEnvironment

__all__ = ["Backend", "DummyBackend", "BaseInstrument", "Menu"]


@runtime_checkable
class Backend(Protocol):
    """The minimal transport an instrument needs: query, write, close."""

    def query(self, command: str) -> str: ...
    def write(self, command: str) -> Any: ...
    def close(self) -> None: ...


class DummyBackend:
    """A backend that prints and records SCPI traffic instead of sending it.

    Queries return an empty string. Useful for developing and testing drivers
    with no instrument attached; inspect :attr:`log` to assert what was sent.
    """

    def __init__(self) -> None:
        self.log: list[str] = []

    def query(self, command: str) -> str:
        self.log.append(f"QUERY: {command}")
        print(f"DUMMY QUERY: {command}")
        return ""

    def write(self, command: str) -> Any:
        self.log.append(f"WRITE: {command}")
        print(f"DUMMY WRITE: {command}")

    def close(self) -> None:
        self.log.append("CLOSE")


class BaseInstrument(ABC):
    """Abstract base class for a VISA-controlled instrument.

    Subclasses implement :meth:`_build_address` to turn a short address (such as
    an IP) into a full VISA resource string, and may override
    :meth:`_shutdown_procedure` to leave the hardware safe on close.

    Parameters
    ----------
    environment:
        The owning :class:`~labkit.instruments.environment.TestEnvironment`;
        supplies the shared VISA resource manager (or ``None`` for dummy mode).
    name:
        A human-readable name for this instrument.
    address:
        A short address (e.g. ``"192.168.0.10"``); expanded by
        :meth:`_build_address`.
    timeout:
        Communication timeout as a duration quantity, e.g. ``quantity(10, "s")``.
    backend:
        An explicit transport to use instead of one derived from `environment`.
        Mainly for testing: pass a :class:`~labkit.instruments.mock.MockBackend`
        to drive a real driver with scripted responses and no hardware.
    """

    def __init__(
        self,
        environment: "TestEnvironment",
        name: str,
        address: str,
        timeout: Quantity = quantity(10, "s"),
        backend: Optional[Backend] = None,
    ) -> None:
        self._name = name
        self._address = self._build_address(address)
        self._rm = getattr(environment, "resource_manager", None)
        self._closed = False
        self._lock = Lock()

        self._backend: Backend
        if backend is not None:
            self._backend = backend
        elif self._rm is None:
            self._backend = DummyBackend()
        else:
            resource = self._rm.open_resource(self._address)
            resource.write_termination = "\n"
            resource.read_termination = "\n"
            self._backend = resource
            self.set_timeout(timeout)

        registry.register(self)

    # -- transport ---------------------------------------------------------
    def query(self, command: str) -> str:
        """Send a SCPI query and return the instrument's response."""
        return self._backend.query(command)

    def write(self, command: str) -> Any:
        """Send a SCPI command with no response."""
        return self._backend.write(command)

    @abstractmethod
    def _build_address(self, address: str) -> str:
        """Turn a short address into a full VISA resource string.

        For example ``"192.168.0.10"`` → ``"TCPIP::192.168.0.10::INSTR"``.
        """
        ...

    # -- common SCPI -------------------------------------------------------
    def set_timeout(self, timeout: Quantity) -> None:
        """Set the communication timeout (PyVISA expects milliseconds)."""
        self._timeout = timeout
        resource = self._backend
        if not isinstance(resource, DummyBackend):
            resource.timeout = timeout.to("ms").magnitude  # type: ignore[attr-defined]

    def get_id(self) -> str:
        """Return the ``*IDN?`` identification string."""
        return self.query("*IDN?")

    def reset_instrument(self, wait_for_instrument: bool = False) -> None:
        """Reset the instrument (``*RST`` then ``*CLS``)."""
        self.write("*RST")
        self.write("*CLS")
        if wait_for_instrument:
            self.wait_for_instrument()

    def wait_for_instrument(self, timeout: Quantity = quantity(60, "s")) -> None:
        """Block until the instrument reports operation-complete (``*OPC?``)."""
        deadline = perf_counter() + timeout.to("s").magnitude
        while True:
            try:
                response = self.query("*OPC?").strip()
            except Exception:
                response = ""
            if response.startswith("1"):
                return
            if perf_counter() > deadline:
                raise TimeoutError(
                    f"Timed out waiting for '{self._name}' to finish (*OPC?)."
                )
            sleep(0.2)

    def check_errors(self, context: str) -> None:
        """Raise if the instrument's error queue (``SYST:ERR?``) is non-empty."""
        error = self.query("SYST:ERR?").strip()
        if error and not error.startswith("0"):
            raise RuntimeError(f"{context}. Instrument error: {error}")

    # -- failsafe shutdown -------------------------------------------------
    def _shutdown_procedure(self) -> None:
        """Leave the instrument in a safe state before its session closes.

        Override in drivers (e.g. turn RF output off). Must not call
        :meth:`close`. The default does nothing.
        """

    def close(self) -> None:
        """Run the shutdown procedure and close the session, at most once."""
        with self._lock:
            if self._closed:
                return
            try:
                self._shutdown_procedure()
                self._backend.close()
            except Exception:
                pass
            finally:
                self._closed = True
        registry.unregister(self)


class Menu:
    """A group of related commands attached to an instrument.

    A menu forwards :meth:`query`/:meth:`write` to its parent instrument, so
    drivers can organise commands hierarchically::

        analyzer.sweep.set_span(quantity(10, "MHz"))
    """

    def __init__(self, parent: BaseInstrument) -> None:
        self._parent = parent

    def query(self, command: str) -> str:
        """Send a SCPI query via the parent instrument."""
        return self._parent.query(command)

    def write(self, command: str) -> Any:
        """Send a SCPI command via the parent instrument."""
        return self._parent.write(command)

    def wait_for_instrument(self, timeout: Optional[Quantity] = None) -> None:
        """Wait for the parent instrument to finish its current operation."""
        if timeout is None:
            self._parent.wait_for_instrument()
        else:
            self._parent.wait_for_instrument(timeout)
