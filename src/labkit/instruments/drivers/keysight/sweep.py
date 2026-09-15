"""Step and list sweeps (``[:SOURce]:LIST``, ``[:SOURce]:SWEep``, ``:TRIGger``).

The MXG sweeps frequency and/or power in one of two ways:

- **Step sweep** — equally spaced points between start and stop frequency
  and/or power, with a common dwell time.
- **List sweep** — arbitrary per-point frequency, power and dwell lists
  downloaded over the interface (up to 3201 points).

A sweep is *enabled* per parameter by putting that parameter into ``LIST`` mode
(:meth:`Sweep.set_frequency_swept`, :meth:`Sweep.set_power_swept`); ``CW`` /
``FIXED`` mode stops it. Sweeps run continuously or once
(:meth:`Sweep.set_continuous`, :meth:`Sweep.single`) and are started by a sweep
trigger with a per-point trigger for stepping through the points.

Typical step sweep::

    gen.sweep.set_type("STEP")
    gen.sweep.set_start_frequency(quantity(1, "GHz"))
    gen.sweep.set_stop_frequency(quantity(2, "GHz"))
    gen.sweep.set_points(101)
    gen.sweep.set_dwell(quantity(10, "ms"))
    gen.sweep.set_frequency_swept(True)
    gen.sweep.set_continuous(False)
    gen.sweep.single()          # arms and (with an immediate trigger) starts

Verified against the *MXG SCPI Command Reference* (N5180-90004), "List/Sweep
Subsystem ([:SOURce])", "Frequency Subsystem", "Power Subsystem" and "Trigger
Subsystem".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Literal

from ....units import Quantity, ensure_frequency, ensure_power, ensure_time
from ...base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._signal_generator import AnalogSignalGenerator

__all__ = [
    "Sweep",
    "SweepType",
    "SweepSpacing",
    "SweepDirection",
    "TriggerSource",
    "PointTriggerSource",
    "TriggerSlope",
]

#: Step (equally spaced) or list (arbitrary points) sweep.
SweepType = Literal["STEP", "LIST"]
#: Spacing of step-sweep points.
SweepSpacing = Literal["LINEAR", "LOGARITHMIC"]
#: Sweep direction.
SweepDirection = Literal["UP", "DOWN"]
#: Sweep trigger source: ``*TRG``, immediate, TRIG IN connector, front-panel key, or timer.
TriggerSource = Literal["BUS", "IMMEDIATE", "EXTERNAL", "KEY", "TIMER"]
#: Point trigger source (as :data:`TriggerSource`, plus ``MANUAL`` stepping).
PointTriggerSource = Literal["BUS", "IMMEDIATE", "EXTERNAL", "KEY", "TIMER", "MANUAL"]
#: Active edge of the external trigger input.
TriggerSlope = Literal["POSITIVE", "NEGATIVE"]

_SPACING_SCPI = {"LINEAR": "LIN", "LOGARITHMIC": "LOG"}
_TRIGGER_SCPI = {
    "BUS": "BUS", "IMMEDIATE": "IMM", "EXTERNAL": "EXT", "KEY": "KEY",
    "TIMER": "TIM", "MANUAL": "MAN",
}
_SLOPE_SCPI = {"POSITIVE": "POS", "NEGATIVE": "NEG"}

#: Operation-status-register bit set while a sweep is in progress (bit 3).
_SWEEPING_BIT = 1 << 3


class Sweep(Menu):
    """Step- and list-sweep configuration, triggering and run control."""

    def __init__(self, parent: "AnalogSignalGenerator") -> None:
        super().__init__(parent)
        self._gen = parent

    # -- what is swept -----------------------------------------------------
    def set_type(self, sweep_type: SweepType) -> None:
        """Select a step or list sweep (``LIST:TYPE``)."""
        self.write(f"LIST:TYPE {sweep_type}")

    def set_frequency_swept(self, swept: bool) -> None:
        """Enable (``FREQ:MODE LIST``) or stop (``FREQ:MODE CW``) the frequency sweep."""
        self.write(f"FREQ:MODE {'LIST' if swept else 'CW'}")

    def set_power_swept(self, swept: bool) -> None:
        """Enable (``POW:MODE LIST``) or stop (``POW:MODE FIX``) the power sweep."""
        self.write(f"POW:MODE {'LIST' if swept else 'FIX'}")

    # -- step-sweep parameters --------------------------------------------
    def _checked_frequency(self, frequency: Quantity, label: str) -> str:
        ensure_frequency(frequency)
        low, high = self._gen.frequency_range
        c.check_range(frequency, low, high, "Hz", label)
        return c.hz(frequency)

    def _checked_level(self, level: Quantity, label: str) -> str:
        ensure_power(level)
        low, high = self._gen.level_range
        c.check_range(level, low, high, "dBm", label)
        return c.dbm(level)

    def set_start_frequency(self, frequency: Quantity) -> None:
        """Set the step-sweep start frequency (``FREQ:STAR``, in Hz)."""
        self.write(f"FREQ:STAR {self._checked_frequency(frequency, 'Start frequency')}")

    def set_stop_frequency(self, frequency: Quantity) -> None:
        """Set the step-sweep stop frequency (``FREQ:STOP``, in Hz)."""
        self.write(f"FREQ:STOP {self._checked_frequency(frequency, 'Stop frequency')}")

    def set_center_frequency(self, frequency: Quantity) -> None:
        """Set the step-sweep center frequency (``FREQ:CENT``); coupled to start/stop."""
        self.write(f"FREQ:CENT {self._checked_frequency(frequency, 'Center frequency')}")

    def set_span(self, span: Quantity) -> None:
        """Set the step-sweep frequency span (``FREQ:SPAN``); coupled to start/stop."""
        ensure_frequency(span)
        self.write(f"FREQ:SPAN {c.hz(span)}")

    def set_start_level(self, level: Quantity) -> None:
        """Set the step-sweep start level (``POW:STAR``, in dBm)."""
        self.write(f"POW:STAR {self._checked_level(level, 'Start level')}")

    def set_stop_level(self, level: Quantity) -> None:
        """Set the step-sweep stop level (``POW:STOP``, in dBm)."""
        self.write(f"POW:STOP {self._checked_level(level, 'Stop level')}")

    def set_points(self, points: int) -> None:
        """Set the number of step-sweep points, 2–65535 (``SWE:POIN``)."""
        self.write(f"SWE:POIN {int(points)}")

    def get_points(self) -> int:
        """Read the number of step-sweep points (``SWE:POIN?``)."""
        return c.parse_int(self.query("SWE:POIN?"))

    def set_dwell(self, dwell: Quantity) -> None:
        """Set the step-sweep per-point dwell time (``SWE:DWEL``, in seconds).

        The dwell starts once the generator has settled at the new point.
        """
        self.write(f"SWE:DWEL {c.seconds(dwell)}")

    def get_dwell(self) -> Quantity:
        """Read the step-sweep dwell time (``SWE:DWEL?``)."""
        return c.as_seconds(self.query("SWE:DWEL?"))

    def set_spacing(self, spacing: SweepSpacing) -> None:
        """Set linear or logarithmic step spacing (``SWE:SPAC``)."""
        self.write(f"SWE:SPAC {_SPACING_SCPI[spacing]}")

    # -- list-sweep data ---------------------------------------------------
    def set_list_frequencies(self, frequencies: Iterable[Quantity]) -> None:
        """Download the list-sweep frequency points (``LIST:FREQ``, in Hz)."""
        values = [self._checked_frequency(f, "List frequency") for f in frequencies]
        self.write("LIST:FREQ " + ",".join(values))

    def set_list_levels(self, levels: Iterable[Quantity]) -> None:
        """Download the list-sweep power points (``LIST:POW``, in dBm)."""
        values = [self._checked_level(p, "List level") for p in levels]
        self.write("LIST:POW " + ",".join(values))

    def set_list_dwells(self, dwells: Iterable[Quantity]) -> None:
        """Download per-point dwell times (``LIST:DWEL``, in seconds) and select them.

        Also sets ``LIST:DWEL:TYPE LIST`` so the list dwells are used instead of
        the single step-sweep dwell.
        """
        values = [c.seconds(ensure_time(d)) for d in dwells]
        self.write("LIST:DWEL " + ",".join(values))
        self.write("LIST:DWEL:TYPE LIST")

    def use_step_dwell_for_list(self) -> None:
        """Use the single step-sweep dwell for every list point (``LIST:DWEL:TYPE STEP``)."""
        self.write("LIST:DWEL:TYPE STEP")

    def get_list_length(self) -> int:
        """Return the number of frequency points in the list (``LIST:FREQ:POIN?``)."""
        return c.parse_int(self.query("LIST:FREQ:POIN?"))

    # -- direction / retrace / manual stepping -----------------------------
    def set_direction(self, direction: SweepDirection) -> None:
        """Set the sweep direction (``LIST:DIR``)."""
        self.write(f"LIST:DIR {direction}")

    def set_retrace(self, enabled: bool) -> None:
        """Return to the first point after a single sweep (``LIST:RETR``) or stay at the last."""
        self.write(f"LIST:RETR {c.onoff(enabled)}")

    def set_manual_mode(self, enabled: bool) -> None:
        """Select manual point control (``LIST:MODE MAN``) or automatic sweeping (``AUTO``)."""
        self.write(f"LIST:MODE {'MAN' if enabled else 'AUTO'}")

    def set_manual_point(self, point: int) -> None:
        """Jump to a sweep point in manual mode (``LIST:MAN``), 1-based."""
        self.write(f"LIST:MAN {int(point)}")

    def get_current_point(self) -> int:
        """Return the current sweep point (``SWE:CPO?``)."""
        return c.parse_int(self.query("SWE:CPO?"))

    # -- triggering --------------------------------------------------------
    def set_trigger_source(self, source: TriggerSource) -> None:
        """Set the sweep trigger source (``TRIG:SOUR``)."""
        self.write(f"TRIG:SOUR {_TRIGGER_SCPI[source]}")

    def set_point_trigger_source(self, source: PointTriggerSource) -> None:
        """Set the point-to-point trigger source (``LIST:TRIG:SOUR``)."""
        self.write(f"LIST:TRIG:SOUR {_TRIGGER_SCPI[source]}")

    def set_trigger_timer(self, period: Quantity) -> None:
        """Set the trigger-timer period (``TRIG:TIM``, in seconds), 0.5 ms – 1000 s."""
        self.write(f"TRIG:TIM {c.seconds(period)}")

    def set_trigger_slope(self, slope: TriggerSlope) -> None:
        """Set the active edge of the external trigger input (``TRIG:SLOP``)."""
        self.write(f"TRIG:SLOP {_SLOPE_SCPI[slope]}")

    def trigger_now(self) -> None:
        """Start an armed sweep immediately, bypassing the selected trigger (``TRIG``)."""
        self.write("TRIG")

    # -- run control -------------------------------------------------------
    def set_continuous(self, enabled: bool) -> None:
        """Continuous (``True``) or single (``False``) sweeping (``INIT:CONT``)."""
        self.write(f"INIT:CONT {c.onoff(enabled)}")

    def initiate(self) -> None:
        """Arm a single sweep, starting it if the trigger source is immediate (``INIT``)."""
        self.write("INIT")

    def single(self) -> None:
        """Abort any running sweep, then arm/start a single sweep (``TSW``)."""
        self.write("TSW")

    def abort(self) -> None:
        """Abort the sweep in progress (``ABOR``); it restarts if continuous."""
        self.write("ABOR")

    def is_sweeping(self) -> bool:
        """Return ``True`` while a sweep is in progress (``STAT:OPER:COND?`` bit 3)."""
        return bool(c.parse_int(self.query("STAT:OPER:COND?")) & _SWEEPING_BIT)
