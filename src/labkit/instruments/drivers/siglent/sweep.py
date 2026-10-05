"""Sweep configuration (``[:SENSe]:SWEep`` and ``:INITiate`` subsystems).

Verified against the *SHA850A User Manual* (EN01D) §3.3.1–§3.3.4.

Two points the manual leaves open:

- **Sweep mode.** The command list (§10.6.1) names ``[:SENSe]:SWEep:MODE`` and
  ``[:SENSe]:SWEep:MODE:AUTO`` but the manual documents neither. The sister
  SSA3000X Plus programming guide (PG0703P_E02B) has ``:SWEep:MODE
  AUTO|FFT|SWEep``; :meth:`Sweep.set_mode` follows the SHA's split (a mode, plus
  a separate auto switch) and is **unverified on the SHA850A**. The analyzer
  chooses FFT on its own for small RBWs, so the calibration flow does not need it.
- **Sweep time in FFT mode.** "When the sweep type is FFT, the sweep time can
  only be calculated by the instrument itself, and any modification related to
  the sweep time cannot take effect" (§3.3.2); :meth:`Sweep.set_time` is then
  ignored (the instrument shows ``SWT_CCOFM``). :meth:`Sweep.get_time` still
  reports the time the instrument uses.

The single-sweep sequence with its ``*OPC?`` timeout and fallback lives on the
analyzer itself, :meth:`~labkit.instruments.drivers.siglent._spectrum_analyzer.SHA850A.single_sweep`.
"""

from __future__ import annotations

from typing import Literal

from ....units import Quantity, ensure_time
from ...base import Menu
from . import _common as c

__all__ = ["Sweep", "SweepSpeed", "SweepMode"]

#: Sweep-time rule: ``NORMal`` (speed, k = 3) or ``ACCUracy`` (k = 12), §3.3.2.
SweepSpeed = Literal["NORMal", "ACCUracy"]
#: Acquisition: swept or FFT (see the module note — unverified on the SHA850A).
SweepMode = Literal["SWEep", "FFT"]

#: Manual sweep-time limits of the command table (§3.3.2: 1 ms … 4 ks with a
#: span, 1 µs … 6 ks in zero span; the datasheet says 1 ms … 4000 s).
_TIME_RANGE_S = (1e-6, 6000.0)
#: Sweep points (§3.3.1).
_POINTS_RANGE = (201, 10001)


class Sweep(Menu):
    """Number of points, sweep time and its rule, and continuous/single sweeping."""

    def set_points(self, points: int) -> None:
        """Set the number of sweep points, 201 … 10001 (``:SWE:POIN``).

        In FFT mode the analyzer may return fewer points than set (§3.3.1);
        :meth:`~labkit.instruments.drivers.siglent.trace.Trace.get_data` sizes the
        trace from the data it receives.
        """
        if not _POINTS_RANGE[0] <= int(points) <= _POINTS_RANGE[1]:
            raise ValueError(f"Sweep points must be {_POINTS_RANGE[0]}–{_POINTS_RANGE[1]}, got {points}.")
        self.write(f":SWE:POIN {int(points)}")

    def get_points(self) -> int:
        return c.parse_int(self.query(":SWE:POIN?"))

    def set_time(self, time: Quantity) -> None:
        """Set the sweep time (``:SWE:TIME``); no effect in FFT mode (see the module note)."""
        value = ensure_time(time).to("s").magnitude
        c.check_range(value, *_TIME_RANGE_S, "Sweep time", "s")
        self.write(f":SWE:TIME {c.seconds(time)}")

    def get_time(self) -> Quantity:
        """The sweep time the analyzer uses (``:SWE:TIME?``), set or computed."""
        return c.as_seconds(self.query(":SWE:TIME?"))

    def set_time_auto(self, enabled: bool) -> None:
        """Couple the sweep time to span/RBW/VBW (``:SWE:TIME:AUTO``)."""
        self.write(f":SWE:TIME:AUTO {c.onoff(enabled)}")

    def set_speed(self, speed: SweepSpeed) -> None:
        """Select the sweep-time rule, speed or accuracy (``:SWE:SPE``)."""
        self.write(f":SWE:SPE {speed}")

    def set_mode(self, mode: SweepMode) -> None:
        """Select swept or FFT acquisition (``:SWE:MODE``) — unverified, see the module note."""
        self.write(f":SWE:MODE {mode}")

    def set_mode_auto(self, enabled: bool) -> None:
        """Let the analyzer choose swept or FFT (``:SWE:MODE:AUTO``) — unverified."""
        self.write(f":SWE:MODE:AUTO {c.onoff(enabled)}")

    def set_continuous(self, enabled: bool) -> None:
        """Continuous (``True``) vs single (``False``) sweeping (``:INIT:CONT``)."""
        self.write(f":INIT:CONT {c.onoff(enabled)}")

    def is_continuous(self) -> bool:
        return c.parse_bool(self.query(":INIT:CONT?"))

    def restart(self) -> None:
        """Restart the current sweep or measurement (``:INIT:REST``)."""
        self.write(":INIT:REST")
