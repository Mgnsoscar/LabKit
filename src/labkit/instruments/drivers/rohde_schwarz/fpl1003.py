"""Rohde & Schwarz FPL1003 spectrum analyzer.

The FPL1003 is the 3 GHz model of the R&S FPL1000 family. It shares the FSV
family's SCPI command set, so this driver is simply the shared
:class:`~labkit.instruments.drivers.rohde_schwarz._spectrum_analyzer.SpectrumAnalyzer`
with the FPL1003's identity — no command logic is duplicated from the FSV3007.

This is the payoff of the menu/base structure: in the earlier prototype the FPL
and FSV shipped byte-identical ``sweep``/``trace``/``marker`` files; here they
share one implementation.

Commands are verified against the R&S FSVA3000/FSV3000 User Manual
(1178.8520.02, issue 16), which the FPL1000 family shares; validate against your
firmware version if a command behaves unexpectedly.
"""

from __future__ import annotations

from ._spectrum_analyzer import SpectrumAnalyzer

__all__ = ["FPL1003"]


class FPL1003(SpectrumAnalyzer):
    """Driver for the R&S FPL1003 spectrum analyzer (5 kHz – 3 GHz, TCP/IP).

    Exposes the instrument through menus — ``frequency``, ``bandwidth``,
    ``sweep``, ``amplitude``, ``trace``, ``display``, ``reference``,
    ``measurement`` (channel power, ACLR, OBW, SEM, spurious, time-domain power,
    harmonics, TOI, AM depth) and ``noise_figure`` (the R&S FSV3-K30 application)
    — plus :meth:`~...SpectrumAnalyzer.marker`, :meth:`~...SpectrumAnalyzer.trigger`,
    :meth:`~...SpectrumAnalyzer.measure_trace`, and the ``INSTrument``
    channel/application controls (:meth:`~...SpectrumAnalyzer.create_channel`,
    :meth:`~...SpectrumAnalyzer.select_channel`).
    """
