"""LabKit — a framework for automated laboratory measurement.

LabKit is organised into small, independently useful sub-packages:

- :mod:`labkit.units` — physical quantities built on `pint`, including correct
  arithmetic for logarithmic units such as ``dBm`` and ``dB``.
- :mod:`labkit.plotting` — a declarative layer over `matplotlib`: build plot
  description objects and hand them to :func:`labkit.plotting.plot`.
- :mod:`labkit.io` — declarative helpers for writing measurement data (CSV).
- :mod:`labkit.instruments` — SCPI/VISA instrument control with guaranteed
  failsafe shutdown.
- :mod:`labkit.utils` — small filesystem / formatting helpers.

Only :mod:`labkit.units` and its dependencies are imported eagerly. The
plotting and instrument layers pull in `matplotlib` and `pyvisa` respectively,
and those imports are deferred until the relevant functionality is used, so
``import labkit`` stays light and works with only the core dependencies
installed.

This is a ground-up rebuild of an earlier prototype; the public API is still
taking shape and will change before 1.0.
"""

from __future__ import annotations

from . import units
from .units import Quantity, quantity, ureg

__version__ = "0.0.1"

__all__ = [
    "__version__",
    "units",
    "Quantity",
    "quantity",
    "ureg",
]
