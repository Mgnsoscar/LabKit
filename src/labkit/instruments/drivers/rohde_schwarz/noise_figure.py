"""Noise Figure measurement application (R&S FSV3-K30).

Noise figure is a separate measurement *application*: it runs in its own
measurement channel (channel type ``NOISe``), created and selected with the
``INSTrument`` commands on the driver. Once its channel is active, this menu
configures the excess-noise-ratio (ENR) of the noise source, the measurement
frequencies, the second-stage (calibration) correction, and reads the results
(noise figure, gain, noise temperature, Y-factor, …).

Requires the R&S FSV3-K30 option. Verified against the *R&S FSV3-K30 Noise Figure
User Manual* (1178.9432.02, issue 13).

Typical flow::

    sa.create_channel("NOISe", "Noise")     # or sa.noise_figure.create()
    sa.noise_figure.set_enr(15.2)           # constant ENR, in dB
    sa.noise_figure.set_points(101)
    sa.noise_figure.set_start(quantity(10, "MHz"))
    sa.noise_figure.set_stop(quantity(3, "GHz"))
    # ... calibrate, then measure ...
    sa.trigger(wait_for_completion=True)
    nf = sa.noise_figure.get_noise_figure()
    gain = sa.noise_figure.get_gain()
"""

from __future__ import annotations

from typing import Literal

from ....units import Quantity
from ...base import Menu
from . import _common as c

__all__ = ["NoiseFigure", "EnrMode", "NoiseSourceType", "NoiseResult"]

#: Where the ENR/temperature values come from.
EnrMode = Literal["CONSTANT", "TABLE"]
#: The kind of noise source connected.
NoiseSourceType = Literal["DIODE", "RESISTOR", "SMART"]
#: A noise-figure result trace to read back.
NoiseResult = Literal[
    "NOISE_FIGURE", "GAIN", "TEMPERATURE", "Y_FACTOR", "ENR", "P_HOT", "P_COLD",
]

#: Channel type used to create the Noise Figure application channel.
CHANNEL_TYPE = "NOISe"

_ENR_MODE_SCPI = {"CONSTANT": "SPOT", "TABLE": "TABL"}
_SOURCE_TYPE_SCPI = {"DIODE": "DIOD", "RESISTOR": "RES", "SMART": "SMAR"}
_RESULT_SCPI = {
    "NOISE_FIGURE": "NOIS", "GAIN": "GAIN", "TEMPERATURE": "TEMP",
    "Y_FACTOR": "YFAC", "ENR": "ENR", "P_HOT": "PHOT", "P_COLD": "PCOL",
}


class NoiseFigure(Menu):
    """Configure and read the R&S FSV3-K30 Noise Figure application."""

    # -- application channel ----------------------------------------------
    def create(self, name: str = "Noise") -> None:
        """Create the Noise Figure channel (``INST:CRE NOISe,'<name>'``)."""
        self.write(f"INST:CRE {CHANNEL_TYPE},'{name}'")

    def select(self, name: str = "Noise") -> None:
        """Select an existing Noise Figure channel by name (``INST:SEL '<name>'``)."""
        self.write(f"INST:SEL '{name}'")

    # -- noise source / ENR -----------------------------------------------
    def set_enr_mode(self, mode: EnrMode) -> None:
        """Use a constant ENR value or an ENR table (``CORR:ENR:MODE``)."""
        self.write(f"CORR:ENR:MODE {_ENR_MODE_SCPI[mode]}")

    def set_enr(self, enr_db: float) -> None:
        """Set the constant ENR for all measurement points, in dB (``CORR:ENR:SPOT``)."""
        self.write(f"CORR:ENR:SPOT {c.scpi_number(enr_db)}")

    def set_noise_source_type(self, source_type: NoiseSourceType) -> None:
        """Select the noise-source type (``CORR:ENR:TYPE``): diode, resistor or smart."""
        self.write(f"CORR:ENR:TYPE {_SOURCE_TYPE_SCPI[source_type]}")

    # -- measurement frequencies ------------------------------------------
    def set_single_frequency(self, frequency: Quantity) -> None:
        """Set the frequency for single-frequency measurements (``FREQ:SING``)."""
        self.write(f"FREQ:SING {c.hz(frequency)}")

    def set_points(self, points: int) -> None:
        """Set the number of measurement points, 1–10001 (``FREQ:POIN``)."""
        self.write(f"FREQ:POIN {int(points)}")

    def set_center(self, frequency: Quantity) -> None:
        """Set the center of the measurement frequency range (``FREQ:CENT``)."""
        self.write(f"FREQ:CENT {c.hz(frequency)}")

    def set_start(self, frequency: Quantity) -> None:
        """Set the start of the measurement frequency range (``FREQ:STAR``)."""
        self.write(f"FREQ:STAR {c.hz(frequency)}")

    def set_stop(self, frequency: Quantity) -> None:
        """Set the stop of the measurement frequency range (``FREQ:STOP``)."""
        self.write(f"FREQ:STOP {c.hz(frequency)}")

    def use_frequency_list(self, continuous: bool = False) -> None:
        """Measure across the frequency list/table (``CONF:LIST:CONT`` / ``CONF:LIST:SING``)."""
        self.write("CONF:LIST:CONT" if continuous else "CONF:LIST:SING")

    def use_single_frequency(self, continuous: bool = False) -> None:
        """Measure at a single frequency (``CONF:FREQ:CONT`` / ``CONF:FREQ:SING``)."""
        self.write("CONF:FREQ:CONT" if continuous else "CONF:FREQ:SING")

    # -- calibration (second-stage correction) ----------------------------
    def set_second_stage_correction(self, enabled: bool) -> None:
        """Enable/disable second-stage (calibration) correction (``CORR``)."""
        self.write(f"CORR {c.onoff(enabled)}")

    def configure_calibration(self) -> None:
        """Arm a calibration measurement (``CONF:CORR``).

        The next :meth:`~...SpectrumAnalyzer.trigger` then runs a calibration
        instead of the actual measurement; call :meth:`use_frequency_list` or
        :meth:`use_single_frequency` afterwards to return to measuring.
        """
        self.write("CONF:CORR")

    # -- results -----------------------------------------------------------
    def get_result(self, result: NoiseResult, window: int = 1, trace: int = 1) -> list[float]:
        """Read a noise-figure result trace (``TRAC<n>:DATA? TRACE<t>,<result>``)."""
        response = self.query(f"TRAC{window}:DATA? TRACE{trace},{_RESULT_SCPI[result]}")
        return c.parse_float_list(response)

    def get_noise_figure(self, window: int = 1, trace: int = 1) -> list[float]:
        """Read the noise-figure result (in dB) per measurement point."""
        return self.get_result("NOISE_FIGURE", window, trace)

    def get_gain(self, window: int = 1, trace: int = 1) -> list[float]:
        """Read the gain result (in dB) per measurement point."""
        return self.get_result("GAIN", window, trace)

    def get_temperature(self, window: int = 1, trace: int = 1) -> list[float]:
        """Read the noise-temperature result (in K) per measurement point."""
        return self.get_result("TEMPERATURE", window, trace)

    def get_y_factor(self, window: int = 1, trace: int = 1) -> list[float]:
        """Read the Y-factor result (in dB) per measurement point."""
        return self.get_result("Y_FACTOR", window, trace)
