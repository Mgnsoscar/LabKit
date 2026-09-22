"""One analog input channel: vertical settings, coupling, bandwidth, probe, arithmetic.

Verified against the *R&S RTO6 User Manual*, chapter 24.8 "Acquisition and
setup": ``CHANnel<m>:STATe``, ``:SCALe``, ``:RANGe``, ``:OFFSet``,
``:POSition``, ``:COUPling``, ``:BANDwidth``, ``:INVert``, ``:IMPedance``,
``:OVERload``, ``CHANnel<m>[:WAVeform<n>]:ARIThmetics``,
``CHANnel<m>[:WAVeform<n>]:TYPE`` and ``PROBe<m>:SETup:ATTenuation:...``.
On the instrument ``ARIThmetics`` accepts ``OFF | ENVelope | AVERage`` only
(``PDETect`` is rejected with "Invalid character data"); the decimation
modes belong to ``TYPE``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .....units import Quantity, ensure_time, quantity
from ....base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._oscilloscope import Oscilloscope

__all__ = ["Channel", "Coupling", "BandwidthLimit", "Arithmetics", "Decimation"]

#: Input coupling. ``DC`` is 50 Ω, ``DC_1M`` (the instrument's ``DCLimit``) and
#: ``AC`` are the 1 MΩ input.
Coupling = Literal["DC", "DC_1M", "AC"]
_COUPLING_SCPI = {"DC": "DC", "DC_1M": "DCL", "AC": "AC"}
_COUPLING_FROM_SCPI = {"DC": "DC", "DCL": "DC_1M", "DCLIMIT": "DC_1M", "AC": "AC"}

#: Bandwidth limit filter.
BandwidthLimit = Literal["FULL", "200MHz", "20MHz"]
_BANDWIDTH_SCPI = {"FULL": "FULL", "200MHz": "B200", "20MHz": "B20"}

#: Waveform arithmetic across acquisitions (``CHANnel<m>[:WAVeform<n>]:ARIThmetics``).
#: The instrument accepts only these three; the per-sample-interval modes are
#: the *decimation* (:data:`Decimation`, ``...:TYPE``).
Arithmetics = Literal["OFF", "ENVELOPE", "AVERAGE"]
_ARITHMETICS_SCPI = {"OFF": "OFF", "ENVELOPE": "ENV", "AVERAGE": "AVER"}

#: How the ADC stream is reduced to waveform points at a lower sample rate
#: (``CHANnel<m>[:WAVeform<n>]:TYPE``): one sample per interval, the minimum
#: and maximum of the interval (two values per point), their average, or RMS.
Decimation = Literal["SAMPLE", "PEAK_DETECT", "HIGH_RESOLUTION", "RMS"]
_DECIMATION_SCPI = {"SAMPLE": "SAMP", "PEAK_DETECT": "PDET", "HIGH_RESOLUTION": "HRES", "RMS": "RMS"}


class Channel(Menu):
    """Settings of analog channel `number` (``scope.channel(1)``)."""

    def __init__(self, parent: "Oscilloscope", number: int) -> None:
        super().__init__(parent)
        parent.check_channel(number)
        self.number = number

    @property
    def source(self) -> str:
        """The channel's waveform source name for measurements and math (``C1W1``)."""
        return c.channel_source(self.number)

    def _cmd(self, suffix: str) -> str:
        return f"CHAN{self.number}:{suffix}"

    # -- on/off ------------------------------------------------------------
    def enable(self, enabled: bool = True) -> None:
        """Switch the channel on or off (``CHAN<m>:STAT``)."""
        self.write(f"{self._cmd('STAT')} {c.onoff(enabled)}")

    def is_enabled(self) -> bool:
        return c.parse_bool(self.query(f"{self._cmd('STAT')}?"))

    # -- vertical ----------------------------------------------------------
    def set_scale(self, volts_per_division: Quantity) -> None:
        """Set the vertical scale in volts per division (``CHAN<m>:SCAL``)."""
        self.write(f"{self._cmd('SCAL')} {c.volts(volts_per_division)}")

    def get_scale(self) -> Quantity:
        return c.as_volts(self.query(f"{self._cmd('SCAL')}?"))

    def set_range(self, full_scale: Quantity) -> None:
        """Set the voltage range across the ten divisions (``CHAN<m>:RANG``)."""
        self.write(f"{self._cmd('RANG')} {c.volts(full_scale)}")

    def get_range(self) -> Quantity:
        return c.as_volts(self.query(f"{self._cmd('RANG')}?"))

    def set_offset(self, offset: Quantity) -> None:
        """Set the offset voltage subtracted from the signal (``CHAN<m>:OFFS``)."""
        self.write(f"{self._cmd('OFFS')} {c.volts(offset)}")

    def get_offset(self) -> Quantity:
        return c.as_volts(self.query(f"{self._cmd('OFFS')}?"))

    def set_position(self, divisions: float) -> None:
        """Set the vertical position in divisions, −5 to 5 (``CHAN<m>:POS``)."""
        if not -5.0 <= divisions <= 5.0:
            raise ValueError("Vertical position must be between -5 and 5 divisions.")
        self.write(f"{self._cmd('POS')} {c.scpi_number(divisions)}")

    def get_position(self) -> float:
        return c.parse_float(self.query(f"{self._cmd('POS')}?"))

    # -- input -------------------------------------------------------------
    def set_coupling(self, coupling: Coupling) -> None:
        """Set the input coupling (``CHAN<m>:COUP``): ``DC`` (50 Ω), ``DC_1M`` or ``AC`` (1 MΩ)."""
        self.write(f"{self._cmd('COUP')} {_COUPLING_SCPI[coupling]}")

    def get_coupling(self) -> str:
        text = self.query(f"{self._cmd('COUP')}?").strip().upper()
        return _COUPLING_FROM_SCPI.get(text, text)

    def set_bandwidth_limit(self, limit: BandwidthLimit) -> None:
        """Set the bandwidth limit filter (``CHAN<m>:BAND``): ``FULL``, ``200MHz`` or ``20MHz``."""
        self.write(f"{self._cmd('BAND')} {_BANDWIDTH_SCPI[limit]}")

    def get_bandwidth_limit(self) -> str:
        return self.query(f"{self._cmd('BAND')}?").strip()

    def set_invert(self, inverted: bool) -> None:
        """Invert the signal around ground (``CHAN<m>:INV``)."""
        self.write(f"{self._cmd('INV')} {c.onoff(inverted)}")

    def set_impedance(self, ohms: float) -> None:
        """Set the impedance used for power calculations, 0.1 Ω – 100 kΩ (``CHAN<m>:IMP``)."""
        if not 0.1 <= ohms <= 100e3:
            raise ValueError("Impedance must be between 0.1 Ω and 100 kΩ.")
        self.write(f"{self._cmd('IMP')} {c.scpi_number(ohms)}")

    def is_overloaded(self) -> bool:
        """Read (and clear) the channel's overload status (``CHAN<m>:OVER?``)."""
        return c.parse_bool(self.query(f"{self._cmd('OVER')}?"))

    # -- probe -------------------------------------------------------------
    def set_probe_attenuation(self, factor: float) -> None:
        """Set a manual probe attenuation factor in V/V, e.g. 10 for a 10:1 probe.

        Switches the probe attenuation to manual mode (``PROB<m>:SET:ATT:MODE
        MAN``) and sets the factor (``PROB<m>:SET:ATT:MAN``). Probes with an
        interface report their attenuation themselves; this is for passive
        probes and direct connections through pads.
        """
        if factor <= 0:
            raise ValueError("Probe attenuation must be positive.")
        self.write(f"PROB{self.number}:SET:ATT:MODE MAN")
        self.write(f"PROB{self.number}:SET:ATT:MAN {c.scpi_number(factor)}")

    def get_probe_attenuation(self) -> float:
        """Read the effective probe attenuation factor (``PROB<m>:SET:ATT?``)."""
        return c.parse_float(self.query(f"PROB{self.number}:SET:ATT?"))

    # -- arithmetic --------------------------------------------------------
    def set_arithmetics(self, mode: Arithmetics, waveform: int = 1) -> None:
        """Set the waveform arithmetic across acquisitions (``CHAN<m>[:WAV<n>]:ARIT``):
        ``AVERAGE``, ``ENVELOPE`` or ``OFF``.

        Averaging and envelope run over the number of acquisitions set with
        :meth:`~labkit.instruments.drivers.rohde_schwarz.oscilloscope.acquisition.Acquisition.set_count`.
        Peak detect and the other per-sample-interval reductions are the
        decimation, :meth:`set_decimation`.
        """
        self.write(f"CHAN{self.number}:WAV{waveform}:ARIT {_ARITHMETICS_SCPI[mode]}")

    def get_arithmetics(self, waveform: int = 1) -> str:
        return self.query(f"CHAN{self.number}:WAV{waveform}:ARIT?").strip()

    # -- decimation --------------------------------------------------------
    def set_decimation(self, mode: Decimation, waveform: int = 1) -> None:
        """Set how the ADC stream becomes waveform points (``CHAN<m>[:WAV<n>]:TYPE``):
        ``SAMPLE`` (one sample per interval), ``PEAK_DETECT`` (the minimum and
        maximum of each interval, two values per point), ``HIGH_RESOLUTION``
        (their average) or ``RMS``.

        Peak detect makes a record at a reduced sample rate keep every glitch
        the ADC saw; the waveform then transfers with two values per sample.
        """
        self.write(f"CHAN{self.number}:WAV{waveform}:TYPE {_DECIMATION_SCPI[mode]}")

    def get_decimation(self, waveform: int = 1) -> str:
        return self.query(f"CHAN{self.number}:WAV{waveform}:TYPE?").strip()

    # -- deskew ------------------------------------------------------------
    def set_skew(self, delay: Quantity) -> None:
        """Set the channel's deskew time (``CHAN<m>:SKEW:TIME``) — a manual delay
        to align probes of different length."""
        ensure_time(delay)
        self.write(f"CHAN{self.number}:SKEW:MAN ON")
        self.write(f"CHAN{self.number}:SKEW:TIME {c.seconds(delay)}")

    def get_skew(self) -> Quantity:
        return quantity(c.parse_float(self.query(f"CHAN{self.number}:SKEW:TIME?")), "s")
