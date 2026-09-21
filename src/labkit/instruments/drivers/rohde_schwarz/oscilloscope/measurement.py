"""Automatic measurements: amplitude/time results per measurement group.

The RTO has ten measurement groups. Each has a *main* measurement (the
result that :meth:`Measurement.get_result` returns by default), optional
*additional* measurements of the same category, one or two sources, and
statistics over acquisitions.

Verified against the *R&S RTO6 User Manual*, chapter 24.12 "Automatic
measurements": ``MEASurement<m>[:ENABle]``, ``MEASurement<m>:SOURce``,
``MEASurement<m>:CATegory``, ``MEASurement<m>:MAIN``,
``MEASurement<m>:ADDitional``, ``MEASurement<m>:RESult[:ACTual]?`` /
``:AVG?`` / ``:RMS?`` / ``:STDDev?`` / ``:PPEak?`` / ``:NPEak?`` /
``:WFMCount?``, ``MEASurement<m>:STATistics[:ENABle]`` and
``MEASurement<m>:STATistics:RESet``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

from .....units import Quantity, quantity
from ....base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._oscilloscope import Oscilloscope

__all__ = ["Measurement", "MeasurementType", "Category"]

#: Amplitude and time measurements (``MEASurement<m>:MAIN`` / ``:ADDitional``).
MeasurementType = Literal[
    "HIGH", "LOW", "AMPLITUDE", "MAXIMUM", "MINIMUM", "PEAK_TO_PEAK", "MEAN", "RMS", "STDDEV",
    "POSITIVE_OVERSHOOT", "NEGATIVE_OVERSHOOT", "AREA", "RISE_TIME", "FALL_TIME",
    "POSITIVE_PULSE", "NEGATIVE_PULSE", "PERIOD", "FREQUENCY", "POSITIVE_DUTY_CYCLE",
    "NEGATIVE_DUTY_CYCLE", "CYCLE_AREA", "CYCLE_MEAN", "CYCLE_RMS", "CYCLE_STDDEV",
    "PULSE_COUNT", "DELAY", "PHASE", "BURST_WIDTH", "EDGE_COUNT",
]

#: ``(SCPI mnemonic, result unit)`` per measurement; ``None`` = a plain number.
_TYPES: dict[str, tuple[str, Optional[str]]] = {
    "HIGH": ("HIGH", "V"), "LOW": ("LOW", "V"), "AMPLITUDE": ("AMPL", "V"),
    "MAXIMUM": ("MAX", "V"), "MINIMUM": ("MIN", "V"), "PEAK_TO_PEAK": ("PDEL", "V"),
    "MEAN": ("MEAN", "V"), "RMS": ("RMS", "V"), "STDDEV": ("STDD", "V"),
    "POSITIVE_OVERSHOOT": ("POV", "%"), "NEGATIVE_OVERSHOOT": ("NOV", "%"),
    "AREA": ("AREA", "V*s"), "RISE_TIME": ("RTIM", "s"), "FALL_TIME": ("FTIM", "s"),
    "POSITIVE_PULSE": ("PPUL", "s"), "NEGATIVE_PULSE": ("NPUL", "s"),
    "PERIOD": ("PER", "s"), "FREQUENCY": ("FREQ", "Hz"),
    "POSITIVE_DUTY_CYCLE": ("PDCY", "%"), "NEGATIVE_DUTY_CYCLE": ("NDCY", "%"),
    "CYCLE_AREA": ("CYCA", "V*s"), "CYCLE_MEAN": ("CYCM", "V"), "CYCLE_RMS": ("CYCR", "V"),
    "CYCLE_STDDEV": ("CYCS", "V"), "PULSE_COUNT": ("PULC", None), "DELAY": ("DEL", "s"),
    "PHASE": ("PHAS", "deg"), "BURST_WIDTH": ("BWID", "s"), "EDGE_COUNT": ("EDGE", None),
}

Category = Literal["AMPLITUDE_TIME", "SPECTRUM", "HISTOGRAM", "JITTER", "EYE"]
_CATEGORY_SCPI = {
    "AMPLITUDE_TIME": "AMPT", "SPECTRUM": "SPEC", "HISTOGRAM": "HIST", "JITTER": "JITT", "EYE": "EYEJ",
}

_GROUPS = range(1, 11)


class Measurement(Menu):
    """The measurement groups (1–10) and their results."""

    def __init__(self, parent: "Oscilloscope") -> None:
        super().__init__(parent)
        self._scope = parent

    @staticmethod
    def _check_group(group: int) -> None:
        if group not in _GROUPS:
            raise ValueError("Measurement group must be between 1 and 10.")

    @staticmethod
    def _type(measurement: str) -> tuple[str, Optional[str]]:
        try:
            return _TYPES[measurement]
        except KeyError:
            raise ValueError(f"Unknown measurement {measurement!r}; one of {', '.join(_TYPES)}.") from None

    # -- setup ---------------------------------------------------------------
    def enable(self, group: int, enabled: bool = True) -> None:
        """Switch measurement group `group` on or off (``MEAS<m>:ENAB``)."""
        self._check_group(group)
        self.write(f"MEAS{group}:ENAB {c.onoff(enabled)}")

    def set_source(self, group: int, source: str, second_source: Optional[str] = None) -> None:
        """Set the group's source(s) (``MEAS<m>:SOUR``): ``"CH1"``, ``"M1"``, ``"R1"``, ...

        Two-source measurements (delay, phase) take `second_source` as well.
        """
        self._check_group(group)
        sources = c.source_name(source)
        if second_source is not None:
            sources += f",{c.source_name(second_source)}"
        self.write(f"MEAS{group}:SOUR {sources}")

    def set_category(self, group: int, category: Category) -> None:
        """Set the group's measurement category (``MEAS<m>:CAT``); amplitude/time by default."""
        self._check_group(group)
        self.write(f"MEAS{group}:CAT {_CATEGORY_SCPI[category]}")

    def set_main(self, group: int, measurement: MeasurementType) -> None:
        """Set the group's main measurement (``MEAS<m>:MAIN``), e.g. ``FREQUENCY`` or ``AMPLITUDE``."""
        self._check_group(group)
        scpi, _ = self._type(measurement)
        self.write(f"MEAS{group}:MAIN {scpi}")

    def add(self, group: int, measurement: MeasurementType, enabled: bool = True) -> None:
        """Enable an additional measurement in the group (``MEAS<m>:ADD <type>,ON``)."""
        self._check_group(group)
        scpi, _ = self._type(measurement)
        self.write(f"MEAS{group}:ADD {scpi},{c.onoff(enabled)}")

    # -- statistics ------------------------------------------------------------
    def set_statistics(self, group: int, enabled: bool) -> None:
        """Enable statistics over acquisitions for the group (``MEAS<m>:STAT``)."""
        self._check_group(group)
        self.write(f"MEAS{group}:STAT {c.onoff(enabled)}")

    def reset_statistics(self, group: int) -> None:
        """Reset the group's statistics, histogram and long-term results (``MEAS<m>:STAT:RES``)."""
        self._check_group(group)
        self.write(f"MEAS{group}:STAT:RES")

    # -- results -----------------------------------------------------------------
    def _result(self, group: int, kind: str, measurement: Optional[str]) -> Quantity | float:
        self._check_group(group)
        if measurement is None:
            response = self.query(f"MEAS{group}:RES:{kind}?")
            return c.parse_float(response)
        scpi, unit = self._type(measurement)
        value = c.parse_float(self.query(f"MEAS{group}:RES:{kind}? {scpi}"))
        return quantity(value, unit) if unit is not None else value

    def get_result(self, group: int, measurement: Optional[MeasurementType] = None) -> Quantity | float:
        """The current result (``MEAS<m>:RES:ACT?``).

        With `measurement` the result of that (main or additional) measurement
        is returned as a quantity in its natural unit (V, s, Hz, %, deg); without
        it the group's main result comes back as a plain number, because the
        instrument does not say which measurement it belongs to.
        """
        return self._result(group, "ACT", measurement)

    def get_average(self, group: int, measurement: Optional[MeasurementType] = None) -> Quantity | float:
        """The average over the statistics period (``MEAS<m>:RES:AVG?``)."""
        return self._result(group, "AVG", measurement)

    def get_rms(self, group: int, measurement: Optional[MeasurementType] = None) -> Quantity | float:
        return self._result(group, "RMS", measurement)

    def get_stddev(self, group: int, measurement: Optional[MeasurementType] = None) -> Quantity | float:
        return self._result(group, "STDD", measurement)

    def get_maximum(self, group: int, measurement: Optional[MeasurementType] = None) -> Quantity | float:
        """The positive peak over the statistics period (``MEAS<m>:RES:PPE?``)."""
        return self._result(group, "PPE", measurement)

    def get_minimum(self, group: int, measurement: Optional[MeasurementType] = None) -> Quantity | float:
        """The negative peak over the statistics period (``MEAS<m>:RES:NPE?``)."""
        return self._result(group, "NPE", measurement)

    def get_waveform_count(self, group: int) -> int:
        """Waveforms that went into the statistics (``MEAS<m>:RES:WFMC?``)."""
        self._check_group(group)
        return c.parse_int(self.query(f"MEAS{group}:RES:WFMC?"))

    # -- convenience ---------------------------------------------------------------
    def measure(self, measurement: MeasurementType, source: str, group: int = 1) -> Quantity | float:
        """Configure `group` for one amplitude/time `measurement` of `source` and read it.

        Enables the group, sets the category, source and main measurement,
        waits for the instrument, and returns the current result as a quantity.
        """
        self.enable(group, True)
        self.set_category(group, "AMPLITUDE_TIME")
        self.set_source(group, source)
        self.set_main(group, measurement)
        self.wait_for_instrument()
        return self.get_result(group, measurement)
