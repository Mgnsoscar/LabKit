"""Aim-TTi TGR6000 6 GHz RF signal generator.

The TGR6000 is a fast-sweep synthesised RF signal generator covering
10 MHz – 6 GHz with an output level of −110 dBm to +7 dBm. Almost all of its
behaviour is shared with any TGR-family generator and lives in
:class:`~labkit.instruments.drivers.aim_tti._signal_generator.SignalGenerator`;
this class is the concrete, named entry point that pins the model's ranges.

All commands are taken from the TGR6000 Instruction Manual (Iss 9), "Remote
Commands" / "Command List". Note that the instrument has **no modulation
capability** and **no query form** for frequency or output level — see
:mod:`~labkit.instruments.drivers.aim_tti.modulation` and the ``SignalGenerator``
module note.
"""

from __future__ import annotations

from ....units import quantity
from ._signal_generator import SignalGenerator

__all__ = ["TGR6000"]


class TGR6000(SignalGenerator):
    """Driver for the Aim-TTi TGR6000 signal generator (10 MHz – 6 GHz, TCP/IP).

    Exposes the instrument through menus — ``frequency``, ``output``, ``sweep``,
    ``reference``, ``system`` (and a ``modulation`` menu that reports the
    TGR6000's lack of modulation) — plus :meth:`~...SignalGenerator.set_rf_enabled`,
    :meth:`~...SignalGenerator.run_self_test` and
    :meth:`~...SignalGenerator.trigger`.

    Example
    -------
    ::

        gen.frequency.set_frequency(quantity(2.45, "GHz"))
        gen.output.set_level(quantity(-10, "dBm"))
        gen.output.set_rf_enabled(True)

    The failsafe shutdown forces the RF output off when the session ends.
    """

    #: Carrier-frequency range: 10 MHz – 6 GHz.
    frequency_range = (quantity(10, "MHz"), quantity(6, "GHz"))
    #: Output-level range: −110 dBm – +7 dBm.
    level_range = (quantity(-110, "dBm"), quantity(7, "dBm"))
