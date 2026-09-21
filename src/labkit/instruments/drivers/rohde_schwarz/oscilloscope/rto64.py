"""Rohde & Schwarz RTO64 oscilloscope.

The RTO64 is the four-channel model of the R&S RTO6 series: 600 MHz base
bandwidth, extendable by option to 1, 2, 3, 4 or 6 GHz, 20 GSa/s real-time
sampling on every channel, and up to 2 Gsample of acquisition memory. All of
its behaviour is shared with the RTO6 family and lives in
:class:`~labkit.instruments.drivers.rohde_schwarz.oscilloscope._oscilloscope.Oscilloscope`;
this class is the concrete, named entry point that pins the model's identity.

Commands are verified against the *R&S RTO6 User Manual* (1801.6687.02),
chapter 24 "Remote control commands". Validate against your firmware version
if a command behaves unexpectedly.
"""

from __future__ import annotations

from .....units import Quantity, quantity
from ._oscilloscope import Oscilloscope

__all__ = ["RTO64"]


class RTO64(Oscilloscope):
    """Driver for the R&S RTO64 oscilloscope (4 channels, 600 MHz – 6 GHz by option, TCP/IP).

    Exposes the instrument through menus — ``channel(n)`` (vertical, coupling,
    bandwidth limit, probe attenuation, arithmetic), ``timebase``,
    ``acquisition`` (sample rate, record length, count, interpolation),
    ``trigger``, ``waveform`` (record transfer), ``history`` (stored
    acquisitions and their timestamps), ``measurement`` (automatic
    amplitude/time measurements with statistics), ``math`` (expressions and
    FFT) and ``system`` — plus :meth:`~...Oscilloscope.run`,
    :meth:`~...Oscilloscope.run_single`, :meth:`~...Oscilloscope.stop` and
    :meth:`~...Oscilloscope.acquire`.

    Example
    -------
    ::

        scope.system.set_display_update(False)     # faster while scripted
        ch = scope.channel(1)
        ch.enable(True)
        ch.set_coupling("DC")                      # 50 Ω
        ch.set_scale(quantity(100, "mV"))
        scope.timebase.set_scale(quantity(20, "ns"))
        scope.acquisition.set_sample_rate(quantity(10, "GHz"))
        scope.trigger.edge("CH1", quantity(0, "V"), slope="POSITIVE", mode="NORMAL")

        t, v = scope.acquire(1)                    # single shot -> (time, voltage) arrays
        f = scope.measurement.measure("FREQUENCY", "CH1")

    The failsafe shutdown switches the display update on and returns the
    instrument to continuous acquisition.
    """

    #: Four analog input channels.
    channel_count = 4
    #: Base bandwidth; the B1/B2/B3/B4/B6 options raise it to 1, 2, 3, 4 or 6 GHz.
    bandwidth: Quantity = quantity(600, "MHz")
    #: 20 GSa/s real-time sample rate on every channel.
    max_sample_rate: Quantity = quantity(20, "GHz")
