"""A scriptable backend for testing drivers without hardware.

:class:`MockBackend` records every SCPI write and query, and answers queries
from a scripted table (or a callable). :func:`mock_instrument` builds a real
driver wired to one, so you can assert the exact SCPI a driver emits and feed it
canned responses to test parsing — no instrument, no `pyvisa`.

    sa, backend = mock_instrument(FSV3007, responses={"*IDN?": "R&S,FSV3007,..."})
    sa.frequency.set_center(quantity(1, "GHz"))
    assert "FREQ:CENT 1000000000.0" in backend.writes
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Union

from .base import BaseInstrument, DummyBackend
from .environment import TestEnvironment

__all__ = ["MockBackend", "MockEnvironment", "mock_instrument"]

Responder = Callable[[str], str]
ResponseTable = Union[dict[str, str], Responder]


class MockBackend(DummyBackend):
    """A backend that records traffic and returns scripted query responses.

    Parameters
    ----------
    responses:
        Either a ``{query: response}`` mapping (matched exactly) or a callable
        ``query -> response``. Unmatched queries return ``""``. Register more at
        runtime with :meth:`on`.
    """

    def __init__(self, responses: Optional[ResponseTable] = None) -> None:
        super().__init__()
        self.writes: list[str] = []
        self.queries: list[str] = []
        self._responses: ResponseTable = {} if responses is None else responses

    def on(self, query: str, response: str) -> "MockBackend":
        """Register (or replace) the response for an exact `query`. Chainable."""
        if not isinstance(self._responses, dict):
            raise TypeError("on() is only available when responses is a mapping.")
        self._responses[query] = response
        return self

    def query(self, command: str) -> str:
        self.queries.append(command)
        self.log.append(f"QUERY: {command}")
        if callable(self._responses):
            return self._responses(command)
        return self._responses.get(command, "")

    def write(self, command: str) -> Any:
        self.writes.append(command)
        self.log.append(f"WRITE: {command}")


class MockEnvironment(TestEnvironment):
    """A stand-in environment (``resource_manager is None``) for mock drivers.

    Skips the real VISA resource manager and the ``_configure_instruments``
    step; the instrument's backend is supplied directly instead.
    """

    def __init__(self) -> None:
        self.resource_manager = None

    def _configure_instruments(self) -> None:
        pass


def mock_instrument(
    driver_cls: type[BaseInstrument],
    *,
    responses: Optional[ResponseTable] = None,
    name: str = "mock",
    address: str = "0.0.0.0",
    **kwargs: Any,
) -> tuple[Any, MockBackend]:
    """Build `driver_cls` wired to a fresh :class:`MockBackend`.

    Returns ``(instrument, backend)``. Extra keyword arguments are forwarded to
    the driver constructor.
    """
    backend = MockBackend(responses)
    instrument = driver_cls(MockEnvironment(), name, address, backend=backend, **kwargs)
    return instrument, backend
