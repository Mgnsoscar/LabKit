"""Siglent SHA852A handheld spectrum analyzer.

The SHA852A is the 7.5 GHz model of the SHA850A family. All of its command logic
is shared with the SHA851A and lives in
:class:`~labkit.instruments.drivers.siglent._spectrum_analyzer.SHA850A`; this
class is the concrete, named entry point with the model's frequency range.

Commands are verified against the *SHA850A User Manual* (EN01D) and
cross-checked against the *SSA3000X Plus / SVA1000X Programming Guide*
(PG0703P_E02B); validate against your firmware version if a command behaves
unexpectedly.
"""

from __future__ import annotations

from ....units import Quantity, quantity
from ._spectrum_analyzer import SHA850A

__all__ = ["SHA852A"]


class SHA852A(SHA850A):
    """Driver for the Siglent SHA852A spectrum analyzer (9 kHz – 7.5 GHz, LAN socket).

    Exposes the instrument through menus — ``frequency``, ``bandwidth``,
    ``sweep``, ``amplitude``, ``trace``, ``measurement`` (channel power, with the
    SHA850-AMK option), ``reference`` (10 MHz input) and ``system`` (identity,
    firmware check, alignment) — plus :meth:`~...SHA850A.marker`,
    :meth:`~...SHA850A.single_sweep` and :meth:`~...SHA850A.measure_cw`.
    """

    max_frequency: Quantity = quantity(7.5, "GHz")
