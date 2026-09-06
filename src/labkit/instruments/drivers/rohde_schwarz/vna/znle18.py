"""Rohde & Schwarz ZNLE18 vector network analyzer.

The ZNLE18 is the 18 GHz model of the R&S ZNLE economy VNA family: a 2-port
analyzer covering 1 MHz to 18 GHz. Almost all of its behaviour is shared with the
rest of the ZNL/ZNLE family and lives in
:class:`~labkit.instruments.drivers.rohde_schwarz.vna._network_analyzer.NetworkAnalyzer`;
this class is the concrete, named entry point that pins the model's range and port
count.

All commands are taken from the *R&S ZNL/ZNLE User Manual* (1178.5966.02, issue
23), chapter 11.5 "VNA command reference".
"""

from __future__ import annotations

from .....units import quantity
from ._network_analyzer import NetworkAnalyzer

__all__ = ["ZNLE18"]


class ZNLE18(NetworkAnalyzer):
    """Driver for the R&S ZNLE18 vector network analyzer (1 MHz – 18 GHz, 2-port).

    Exposes the instrument through menus — ``channel``, ``frequency``, ``trace``,
    ``sweep``, ``bandwidth``, ``power``, ``average``, ``calibration``, ``display``
    — plus :meth:`~...NetworkAnalyzer.marker`, :meth:`~...NetworkAnalyzer.trigger`
    and :meth:`~...NetworkAnalyzer.measure`.

    Example
    -------
    ::

        vna.channel.create(1)
        vna.trace.create("Trc1", "S21")
        vna.display.set_window_state(1, True)
        vna.display.feed_trace(1, 1, "Trc1")
        vna.frequency.set_start(quantity(1, "GHz"))
        vna.frequency.set_stop(quantity(18, "GHz"))
        vna.sweep.set_points(1001)
        vna.bandwidth.set_if_bandwidth(quantity(10, "kHz"))
        freqs, s21 = vna.measure()          # complex S21 over the sweep

    The failsafe shutdown switches the RF source output off when the session ends.
    """

    #: Stimulus-frequency range: 1 MHz – 18 GHz.
    frequency_range = (quantity(1, "MHz"), quantity(18, "GHz"))
    #: Two physical test ports.
    port_count = 2
