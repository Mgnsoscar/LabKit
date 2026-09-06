"""Guaranteed instrument shutdown.

Lab instruments often need to be left in a safe state — RF output off, for
example — no matter how a script ends: normal exit, an unhandled exception, or
Ctrl-C. This module keeps a registry of open instruments and resource managers
and closes them all at interpreter exit.

Each instrument runs its own ``_shutdown_procedure`` (defined by the driver)
before its VISA session is closed; see :class:`labkit.instruments.base.BaseInstrument`.

The earlier prototype had a bug where the resource-manager cleanup and the
final registry clear were nested *inside* the per-instrument loop, so resource
managers were closed after the first instrument and the loop's later iterations
operated on already-cleared state. That is fixed here: instruments are closed
first, then resource managers, then the registry is cleared — each stage its
own loop.
"""

from __future__ import annotations

import atexit
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import BaseInstrument

__all__ = ["register", "unregister", "register_rm", "unregister_rm", "shutdown"]

_lock = threading.Lock()
_instruments: "set[BaseInstrument]" = set()
_resource_managers: "set[Any]" = set()


def register(instrument: "BaseInstrument") -> None:
    """Add an instrument (and its resource manager, if any) to the registry."""
    with _lock:
        _instruments.add(instrument)
        rm = getattr(instrument, "_rm", None)
        if rm is not None:
            _resource_managers.add(rm)


def unregister(instrument: "BaseInstrument") -> None:
    """Remove an instrument from the registry (e.g. after it is closed)."""
    with _lock:
        _instruments.discard(instrument)


def register_rm(rm: Any) -> None:
    """Register a VISA resource manager for cleanup at exit."""
    if rm is None:
        return
    with _lock:
        _resource_managers.add(rm)


def unregister_rm(rm: Any) -> None:
    """Remove a resource manager from the registry."""
    if rm is None:
        return
    with _lock:
        _resource_managers.discard(rm)


def shutdown() -> None:
    """Close every registered instrument, then every resource manager.

    Registered as an :mod:`atexit` handler, and safe to call directly. Every
    close is guarded so one failure cannot prevent the rest from shutting down.
    """
    with _lock:
        instruments = list(_instruments)
        resource_managers = list(_resource_managers)

    for instrument in instruments:
        try:
            instrument.close()
        except Exception:
            pass

    for rm in resource_managers:
        try:
            rm.close()
        except Exception:
            pass

    with _lock:
        _instruments.clear()
        _resource_managers.clear()


atexit.register(shutdown)
