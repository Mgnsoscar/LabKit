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
    sa.noise_figure.set_input_loss(quantity(0.8, "dB"))          # cable before the DUT
    sa.noise_figure.set_loss_from_path("OUTPUT", out_path, f)    # frequency-dependent
    # ... calibrate, then measure ...
    sa.trigger(wait_for_completion=True)
    nf = sa.noise_figure.get_noise_figure()
    gain = sa.noise_figure.get_gain()

Losses in the input and output paths change the noise figure the application
computes, so unlike other measurements they are best entered **on the
instrument** (constant, or as a frequency table it interpolates) rather than
corrected afterwards; see :meth:`NoiseFigure.set_loss` and
:meth:`NoiseFigure.set_loss_table`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Union

from ....units import Quantity, ensure_frequency
from ...base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ....signal_path import LossTable, SignalPath

__all__ = ["NoiseFigure", "EnrMode", "NoiseSourceType", "NoiseResult", "LossPort"]

#: Where a loss correction applies: before the DUT, after it, or during calibration.
LossPort = Literal["INPUT", "OUTPUT", "CALIBRATION"]

_LOSS_PORT_SCPI = {"INPUT": "INP", "OUTPUT": "OUTP", "CALIBRATION": "CAL"}
#: Maximum number of entries in a K30 loss table.
_LOSS_TABLE_MAX_POINTS = 10001

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

    # -- additional loss (input / output / calibration paths) ---------------
    def set_loss(self, port: LossPort, loss: Quantity) -> None:
        """Use a constant loss for every measurement point (``CORR:LOSS:<port>:SPOT``).

        `loss` is a ``dB`` quantity; the mode is switched to ``SPOT``. ``INPUT``
        is the loss between the noise source and the DUT, ``OUTPUT`` the loss
        between the DUT and the analyzer, ``CALIBRATION`` the loss between the
        noise source and the analyzer during the calibration measurement.
        """
        scpi = _LOSS_PORT_SCPI[port]
        self.write(f"CORR:LOSS:{scpi}:MODE SPOT")
        self.write(f"CORR:LOSS:{scpi}:SPOT {c.scpi_number(loss.to('dB').magnitude)}")

    def set_loss_table(
        self,
        port: LossPort,
        frequencies: Quantity,
        losses: Quantity,
        name: str = "LabKit",
    ) -> None:
        """Use a frequency-dependent loss table (``CORR:LOSS:<port>:TABL``).

        Selects (creating or overwriting) the table `name`, loads it with the
        ``(frequency, loss)`` pairs — up to 10001 points; the application
        interpolates between them at its measurement frequencies — and switches
        the mode to ``TABLe``. `frequencies` is a frequency quantity array and
        `losses` a ``dB`` quantity array of the same length.
        """
        f_hz = [float(v) for v in ensure_frequency(frequencies).to("Hz").magnitude.reshape(-1)]
        l_db = [float(v) for v in losses.to("dB").magnitude.reshape(-1)]
        if len(f_hz) != len(l_db):
            raise ValueError(
                f"frequencies and losses must have the same length, got {len(f_hz)} and {len(l_db)}."
            )
        if not 1 <= len(f_hz) <= _LOSS_TABLE_MAX_POINTS:
            raise ValueError(f"A loss table needs 1 to {_LOSS_TABLE_MAX_POINTS} points, got {len(f_hz)}.")
        scpi = _LOSS_PORT_SCPI[port]
        pairs = ",".join(f"{c.scpi_number(f)},{c.scpi_number(l)}" for f, l in zip(f_hz, l_db))
        self.write(f"CORR:LOSS:{scpi}:TABL:SEL '{name}'")
        self.write(f"CORR:LOSS:{scpi}:TABL {pairs}")
        self.write(f"CORR:LOSS:{scpi}:MODE TABL")

    def set_loss_from_path(
        self,
        port: LossPort,
        path: Union["SignalPath", "LossTable"],
        frequencies: Quantity,
        name: str = "LabKit",
    ) -> None:
        """Load a loss table evaluated from a :class:`~labkit.signal_path.SignalPath`.

        The path's loss is evaluated at `frequencies` (normally the measurement
        frequencies, so the table needs no further interpolation on the
        instrument) and sent with :meth:`set_loss_table`.
        """
        self.set_loss_table(port, frequencies, path.loss_at(frequencies), name)

    def set_loss_temperature(self, port: LossPort, temperature: Quantity) -> None:
        """Set the temperature considered in the loss calculation (``CORR:LOSS:<port>:TEMP``, in K)."""
        scpi = _LOSS_PORT_SCPI[port]
        self.write(f"CORR:LOSS:{scpi}:TEMP {c.scpi_number(temperature.to('K').magnitude)}")

    def list_loss_tables(self, port: LossPort) -> list[str]:
        """List the loss tables stored for `port` (``CORR:LOSS:<port>:TABL:LIST?``)."""
        response = self.query(f"CORR:LOSS:{_LOSS_PORT_SCPI[port]}:TABL:LIST?").strip().strip("'\"")
        return [n.strip() for n in response.split(",") if n.strip()]

    def delete_loss_table(self, port: LossPort, name: str) -> None:
        """Delete a stored loss table (``CORR:LOSS:<port>:TABL:DEL``)."""
        self.write(f"CORR:LOSS:{_LOSS_PORT_SCPI[port]}:TABL:DEL '{name}'")

    def set_input_loss(self, loss: Quantity) -> None:
        """Constant loss between the noise source and the DUT (see :meth:`set_loss`)."""
        self.set_loss("INPUT", loss)

    def set_output_loss(self, loss: Quantity) -> None:
        """Constant loss between the DUT and the analyzer (see :meth:`set_loss`)."""
        self.set_loss("OUTPUT", loss)

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
