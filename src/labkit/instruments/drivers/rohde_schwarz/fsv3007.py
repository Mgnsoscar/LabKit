"""Rohde & Schwarz FSV3007 signal and spectrum analyzer.

The FSV3007 is the 7.5 GHz model of the R&S FSV3000 family. Almost all of its
behaviour is shared with the rest of the family and lives in
:class:`~labkit.instruments.drivers.rohde_schwarz._spectrum_analyzer.SpectrumAnalyzer`;
this class is the concrete, named entry point.

Commands are verified against the R&S FSVA3000/FSV3000 User Manual
(1178.8520.02, issue 16) and, for the noise-figure application, the R&S FSV3-K30
Noise Figure User Manual (1178.9432.02, issue 13); validate against your firmware
version if a command behaves unexpectedly.
"""

from __future__ import annotations

from ._spectrum_analyzer import SpectrumAnalyzer

__all__ = ["FSV3007"]


class FSV3007(SpectrumAnalyzer):
    """Driver for the R&S FSV3007 spectrum analyzer (9 kHz – 7.5 GHz, TCP/IP).

    Exposes the instrument through menus — ``frequency``, ``bandwidth``,
    ``sweep``, ``amplitude``, ``trace``, ``display``, ``reference``,
    ``measurement`` (channel power, ACLR, OBW, SEM, spurious, time-domain power,
    harmonics, TOI, AM depth) and ``noise_figure`` (the R&S FSV3-K30 application)
    — plus :meth:`~...SpectrumAnalyzer.marker`, :meth:`~...SpectrumAnalyzer.trigger`,
    :meth:`~...SpectrumAnalyzer.measure_trace`, and the ``INSTrument``
    channel/application controls (:meth:`~...SpectrumAnalyzer.create_channel`,
    :meth:`~...SpectrumAnalyzer.select_channel`).
    """
