"""Spectrum measurement functions — the analyzer's "Meas" menu.

Beyond a plain frequency sweep, the FSV3000 offers a set of measurements in the
Spectrum application: channel/adjacent-channel power, occupied bandwidth,
spectrum emission mask, spurious emissions, time-domain power, harmonic
distortion, third-order intercept, and AM modulation depth. This menu selects,
configures and reads them.

Verified against the *R&S FSVA3000/FSV3000 User Manual* (1178.8520.02, issue 16):
``[SENSe:]SWEep:MODE``, ``CALCulate:MARKer:FUNCtion:POWer``,
``[SENSe:]POWer:ACHannel``, and the ``CALCulate:MARKer:FUNCtion:SUMMary /
HARMonics / TOI / MDEPth`` subsystems.

Result readouts return plain floats: for the power-scaled results the unit follows
the y-axis scaling (the current amplitude unit for log scaling, W for linear), so
the driver does not assert a unit. Most results are only valid in single-sweep
mode after a synchronized sweep — set
:meth:`~...SpectrumAnalyzer.sweep.set_continuous` ``False`` and
:meth:`~...SpectrumAnalyzer.trigger` with ``wait_for_completion=True`` first.
"""

from __future__ import annotations

from typing import Literal

from ....units import Quantity
from ...base import Menu
from . import _common as c

__all__ = [
    "Measurement",
    "MeasurementMode",
    "PowerMeasurement",
    "PowerResult",
    "TimeDomainPower",
    "TimeDomainMode",
]

#: Top-level measurement type (selects SEM/spurious vs. a normal sweep).
MeasurementMode = Literal["SPECTRUM", "SEM", "SPURIOUS"]
#: A channel-power measurement to activate.
PowerMeasurement = Literal["CHANNEL_POWER", "ACLR", "MULTICARRIER_ACLR", "OCCUPIED_BANDWIDTH"]
#: A channel-power result to read back.
PowerResult = Literal[
    "CHANNEL_POWER", "PEAK_POWER", "ACLR", "MULTICARRIER_ACLR",
    "OCCUPIED_BANDWIDTH", "CARRIER_NOISE", "CARRIER_NOISE_1HZ",
]
#: A time-domain-power statistic.
TimeDomainPower = Literal["RMS", "MEAN", "PEAK", "STDDEV"]
#: Absolute vs. relative time-domain-power results.
TimeDomainMode = Literal["ABSOLUTE", "RELATIVE"]

_MODE_SCPI = {"SPECTRUM": "AUTO", "SEM": "ESP", "SPURIOUS": "LIST"}
_POWER_SELECT_SCPI = {
    "CHANNEL_POWER": "CPOW", "ACLR": "ACP",
    "MULTICARRIER_ACLR": "MCAC", "OCCUPIED_BANDWIDTH": "OBW",
}
_POWER_RESULT_SCPI = {
    "CHANNEL_POWER": "CPOW", "PEAK_POWER": "PPOW", "ACLR": "ACP",
    "MULTICARRIER_ACLR": "MCAC", "OCCUPIED_BANDWIDTH": "OBW",
    "CARRIER_NOISE": "CN", "CARRIER_NOISE_1HZ": "CN0",
}
_TDP_SCPI = {"RMS": "RMS", "MEAN": "MEAN", "PEAK": "PPE", "STDDEV": "SDEV"}


class Measurement(Menu):
    """Select, configure and read the analyzer's spectrum measurement functions."""

    # -- measurement type (SEM / spurious / normal sweep) ------------------
    def set_mode(self, mode: MeasurementMode) -> None:
        """Select the measurement type (``SWE:MODE``).

        ``SPECTRUM`` is a normal sweep, ``SEM`` the spectrum emission mask, and
        ``SPURIOUS`` the spurious emission measurement.
        """
        self.write(f"SWE:MODE {_MODE_SCPI[mode]}")

    def get_mode(self) -> str:
        """Read the measurement type (``SWE:MODE?``)."""
        return self.query("SWE:MODE?").strip()

    # -- channel power / ACLR / OBW ---------------------------------------
    def select_power(self, measurement: PowerMeasurement) -> None:
        """Turn on a channel-power measurement (``CALC:MARK:FUNC:POW:SEL``)."""
        self.write(f"CALC:MARK:FUNC:POW:SEL {_POWER_SELECT_SCPI[measurement]}")

    def channel_power(self) -> None:
        """Activate the single-carrier channel-power measurement."""
        self.select_power("CHANNEL_POWER")

    def aclr(self) -> None:
        """Activate the adjacent-channel-leakage-ratio (ACLR) measurement."""
        self.select_power("ACLR")

    def multicarrier_aclr(self) -> None:
        """Activate the multi-carrier ACLR measurement."""
        self.select_power("MULTICARRIER_ACLR")

    def occupied_bandwidth(self) -> None:
        """Activate the occupied-bandwidth (OBW) measurement."""
        self.select_power("OCCUPIED_BANDWIDTH")

    def power_off(self) -> None:
        """Turn the channel-power measurement off (``CALC:MARK:FUNC:POW OFF``)."""
        self.write("CALC:MARK:FUNC:POW OFF")

    def preset_power(self, measurement: PowerMeasurement) -> None:
        """Optimize span/bandwidths/detector for a power measurement (``POW:ACH:PRES``)."""
        self.write(f"POW:ACH:PRES {_POWER_SELECT_SCPI[measurement]}")

    def get_power_result(self, result: PowerResult) -> list[float]:
        """Read a channel-power result (``CALC:MARK:FUNC:POW:RES?``).

        Returns a list of values (e.g. TX then adjacent/alternate channel powers
        for ACLR; a single value for channel power, OBW or C/N).
        """
        return c.parse_float_list(
            self.query(f"CALC:MARK:FUNC:POW:RES? {_POWER_RESULT_SCPI[result]}")
        )

    # -- ACLR channel configuration ---------------------------------------
    def set_channel_pairs(self, pairs: int) -> None:
        """Set the number of adjacent/alternate channel pairs (``POW:ACH:ACP``), 0–12."""
        self.write(f"POW:ACH:ACP {int(pairs)}")

    def set_tx_channel_bandwidth(self, bandwidth: Quantity) -> None:
        """Set the transmission-channel bandwidth (``POW:ACH:BWID:CHAN``)."""
        self.write(f"POW:ACH:BWID:CHAN {c.hz(bandwidth)}")

    def set_adjacent_channel_bandwidth(self, bandwidth: Quantity) -> None:
        """Set the adjacent-channel bandwidth (``POW:ACH:BWID:ACH``)."""
        self.write(f"POW:ACH:BWID:ACH {c.hz(bandwidth)}")

    def set_channel_spacing(self, spacing: Quantity) -> None:
        """Set the TX-to-adjacent-channel spacing (``POW:ACH:SPAC:ACH``)."""
        self.write(f"POW:ACH:SPAC:ACH {c.hz(spacing)}")

    # -- time-domain power -------------------------------------------------
    def enable_time_domain_power(
        self,
        rms: bool = False,
        mean: bool = False,
        peak: bool = False,
        std_dev: bool = False,
    ) -> None:
        """Enable time-domain-power statistics (``CALC:MARK:FUNC:SUMM:<stat>``).

        Each flag turns the corresponding evaluation on; the measurement runs on
        the trace marker 1 is positioned on.
        """
        self.write(f"CALC:MARK:FUNC:SUMM:RMS {c.onoff(rms)}")
        self.write(f"CALC:MARK:FUNC:SUMM:MEAN {c.onoff(mean)}")
        self.write(f"CALC:MARK:FUNC:SUMM:PPE {c.onoff(peak)}")
        self.write(f"CALC:MARK:FUNC:SUMM:SDEV {c.onoff(std_dev)}")

    def set_time_domain_mode(self, mode: TimeDomainMode) -> None:
        """Report time-domain power absolute or relative to a reference (``SUMM:MODE``)."""
        scpi = "ABS" if mode == "ABSOLUTE" else "REL"
        self.write(f"CALC:MARK:FUNC:SUMM:MODE {scpi}")

    def get_time_domain_power(self, statistic: TimeDomainPower) -> float:
        """Read a time-domain-power statistic (``CALC:MARK:FUNC:SUMM:<stat>:RES?``)."""
        return c.parse_float(
            self.query(f"CALC:MARK:FUNC:SUMM:{_TDP_SCPI[statistic]}:RES?")
        )

    # -- harmonic distortion ----------------------------------------------
    def enable_harmonics(self, enabled: bool = True) -> None:
        """Turn the harmonic-distortion measurement on/off (``CALC:MARK:FUNC:HARM``)."""
        self.write(f"CALC:MARK:FUNC:HARM {c.onoff(enabled)}")

    def set_harmonic_count(self, count: int) -> None:
        """Set the number of harmonics to measure, 1–26 (``HARM:NHAR``)."""
        self.write(f"CALC:MARK:FUNC:HARM:NHAR {int(count)}")

    def preset_harmonics(self) -> None:
        """Auto-configure the harmonic-distortion measurement (``HARM:PRES``)."""
        self.write("CALC:MARK:FUNC:HARM:PRES")

    def get_thd(self) -> tuple[float, float]:
        """Read total harmonic distortion (``HARM:DIST? TOT``) as ``(percent, dB)``."""
        values = c.parse_float_list(self.query("CALC:MARK:FUNC:HARM:DIST? TOT"))
        return values[0], values[1]

    def get_harmonics(self) -> list[float]:
        """Read the list of harmonic power levels (``HARM:LIST?``)."""
        return c.parse_float_list(self.query("CALC:MARK:FUNC:HARM:LIST?"))

    # -- third-order intercept --------------------------------------------
    def enable_toi(self, enabled: bool = True) -> None:
        """Turn the third-order-intercept (TOI) measurement on/off (``CALC:MARK:FUNC:TOI``)."""
        self.write(f"CALC:MARK:FUNC:TOI {c.onoff(enabled)}")

    def get_toi(self) -> float:
        """Read the third-order intercept point (``CALC:MARK:FUNC:TOI:RES?``)."""
        return c.parse_float(self.query("CALC:MARK:FUNC:TOI:RES?"))

    # -- AM modulation depth ----------------------------------------------
    def enable_am_depth(self, enabled: bool = True) -> None:
        """Turn the AM-modulation-depth measurement on/off (``CALC:MARK:FUNC:MDEP``)."""
        self.write(f"CALC:MARK:FUNC:MDEP {c.onoff(enabled)}")

    def search_am_signal(self) -> None:
        """Search for the signals the AM-depth measurement needs (``MDEP:SEAR ONCE``)."""
        self.write("CALC:MARK:FUNC:MDEP:SEAR ONCE")

    def get_am_depth(self) -> float:
        """Read the AM modulation depth in percent (``CALC:MARK:FUNC:MDEP:RES?``)."""
        return c.parse_float(self.query("CALC:MARK:FUNC:MDEP:RES?"))
