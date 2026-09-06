"""Rohde & Schwarz FSV3007 signal and spectrum analyzer.

The FSV3007 is the 7.5 GHz model of the R&S FSV3000 family. Almost all of its
behaviour is shared with the rest of the family and lives in
:class:`~labkit.instruments.drivers.rohde_schwarz._spectrum_analyzer.SpectrumAnalyzer`;
this class is the concrete, named entry point.

Commands follow the standard R&S FSV3000 / FSW remote-control set; validate
against your firmware if a command behaves unexpectedly.
"""

from __future__ import annotations

from ._spectrum_analyzer import SpectrumAnalyzer

__all__ = ["FSV3007"]


class FSV3007(SpectrumAnalyzer):
    """Driver for the R&S FSV3007 spectrum analyzer (9 kHz – 7.5 GHz, TCP/IP).

    Exposes the instrument through menus — ``frequency``, ``bandwidth``,
    ``sweep``, ``amplitude``, ``trace``, ``display``, ``reference`` — plus
    :meth:`~...SpectrumAnalyzer.marker`, :meth:`~...SpectrumAnalyzer.trigger`
    and :meth:`~...SpectrumAnalyzer.measure_trace`.
    """
