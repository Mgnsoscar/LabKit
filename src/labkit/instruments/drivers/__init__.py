"""Concrete instrument drivers.

Drivers are built on :class:`labkit.instruments.BaseInstrument`, with shared
behaviour factored into reusable menus (see
:mod:`labkit.instruments.drivers.rohde_schwarz`) rather than copy-pasted between
instruments — the key problem in the earlier prototype.

Available:

- :class:`~labkit.instruments.drivers.rohde_schwarz.FSV3007` — R&S FSV3007
  signal and spectrum analyzer (7.5 GHz).
- :class:`~labkit.instruments.drivers.rohde_schwarz.FPL1003` — R&S FPL1003
  spectrum analyzer (3 GHz).
"""

from __future__ import annotations

from .rohde_schwarz import FPL1003, FSV3007

__all__ = ["FSV3007", "FPL1003"]
