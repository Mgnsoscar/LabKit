"""Keysight/Agilent N5183A MXG microwave analog signal generator.

The N5183A is the microwave member of the MXG analog family: 100 kHz to
20 GHz (Option 520; 31.8 GHz and 40 GHz with Options 532/540), with AM/FM/ΦM
(Option UNT) and pulse modulation (Options UNU/UNW). Almost all of its
behaviour is shared with every MXG analog generator and lives in
:class:`~labkit.instruments.drivers.keysight._signal_generator.AnalogSignalGenerator`;
this class is the concrete, named entry point that pins the model's ranges.

Ranges are taken from the *Agilent N5183A MXG Microwave Analog Signal
Generator Data Sheet* (5989-7572EN). The output level range is the
**settable** envelope the firmware accepts (down to −130 dBm with the Option
1E1 step attenuator, up to +30 dBm); the level the hardware can actually
deliver depends on the installed options and frequency — see the data sheet.
Commands are verified against the *MXG SCPI Command Reference* (N5180-90004).
"""

from __future__ import annotations

from ....units import quantity
from ._signal_generator import AnalogSignalGenerator

__all__ = ["N5183A"]


class N5183A(AnalogSignalGenerator):
    """Driver for the Keysight/Agilent N5183A MXG (100 kHz – 20 GHz, TCP/IP).

    Exposes the instrument through menus — ``frequency``, ``power`` (level, RF
    on/off, ALC, attenuator), ``modulation`` (``am``, ``fm``, ``pm``, ``pulse``),
    ``sweep`` (step/list sweeps and triggering), ``reference`` and ``system`` —
    plus :meth:`~...AnalogSignalGenerator.set_cw`,
    :meth:`~...AnalogSignalGenerator.set_rf_enabled`,
    :meth:`~...AnalogSignalGenerator.run_self_test` and
    :meth:`~...AnalogSignalGenerator.trigger`.

    Example
    -------
    ::

        gen.set_cw(quantity(2.45, "GHz"), quantity(-10, "dBm"))

        gen.modulation.pulse.set_source("FREE_RUN")
        gen.modulation.pulse.set_period(quantity(100, "us"))
        gen.modulation.pulse.set_width(quantity(10, "us"))
        gen.modulation.pulse.enable(True)
        gen.power.set_modulation_enabled(True)

    The failsafe shutdown forces the RF output off when the session ends.
    """

    #: Carrier-frequency range with Option 520: 100 kHz – 20 GHz.
    frequency_range = (quantity(100, "kHz"), quantity(20, "GHz"))
    #: Settable output-level range: −130 dBm (Option 1E1) – +30 dBm.
    level_range = (quantity(-130, "dBm"), quantity(30, "dBm"))
