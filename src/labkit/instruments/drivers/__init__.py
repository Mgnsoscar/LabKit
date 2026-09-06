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
- :class:`~labkit.instruments.drivers.rohde_schwarz.ZNLE18` — R&S ZNLE18
  vector network analyzer (18 GHz).
- :class:`~labkit.instruments.drivers.aim_tti.TGR6000` — Aim-TTi TGR6000
  RF signal generator (6 GHz).
"""

from __future__ import annotations

from .aim_tti import TGR6000
from .rohde_schwarz import FPL1003, FSV3007, ZNLE18

__all__ = ["FSV3007", "FPL1003", "ZNLE18", "TGR6000"]
