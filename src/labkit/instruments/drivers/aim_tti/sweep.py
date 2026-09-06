"""Frequency/amplitude sweep control.

The TGR6000 sweeps between defined start and stop points. Two sweep *types* are
supported:

- **Step sweep** — start/stop frequency and level, a number of points, linear or
  logarithmic spacing, and a per-point dwell time.
- **List sweep** — up to 1000 user-defined points, each with its own frequency,
  level and dwell, downloaded over the interface.

Either type can free-run, repeat, or be triggered (manual, remote, or external),
with an optional per-point trigger. Verified against the TGR6000 Instruction
Manual (Iss 9), "Command List" → "STEP Sweep Parameters", "General Sweep
Settings and Control", and "LIST Sweep Settings".

Note on the terminology in the task brief: the TGR6000 defines a sweep by
**start/stop** (there is no centre/span command), by **number of points +
lin/log scale** (there is no explicit step-size command), and by a **per-point
dwell** (there is no single total-sweep-time command). There are no remote sweep
*markers*; the rear-panel ``SYNC`` output — whose active polarity is set with
:meth:`Sweep.set_sync_polarity` — is the only sweep position indicator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Literal

from ....units import Quantity, ensure_frequency, ensure_power
from ...base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._signal_generator import SignalGenerator

__all__ = [
    "Sweep",
    "SweepType",
    "SweepParameter",
    "SweepScale",
    "SweepDirection",
    "SyncPolarity",
    "TriggerSource",
]

#: Which sweep engine to use.
SweepType = Literal["STEP", "LIST"]
#: Which quantity(ies) the sweep varies.
SweepParameter = Literal["FREQ", "LEV", "ALL"]
#: Spacing of step-sweep points.
SweepScale = Literal["LIN", "LOG"]
#: Sweep direction.
SweepDirection = Literal["UP", "DOWN"]
#: Active polarity of the rear-panel SYNC output.
SyncPolarity = Literal["POS", "NEG"]
#: Trigger source for a sweep or an individual point.
TriggerSource = Literal["MAN", "REM", "EXT+", "EXT-"]

#: One list-sweep point: (frequency, level, dwell).
SweepPoint = tuple[Quantity, Quantity, Quantity]


class Sweep(Menu):
    """Step- and list-sweep configuration, triggering and run control."""

    def __init__(self, parent: "SignalGenerator") -> None:
        super().__init__(parent)
        self._gen = parent

    # -- step-sweep parameters --------------------------------------------
    def set_start_frequency(self, frequency: Quantity) -> None:
        """Set the step-sweep start frequency (``STARTFREQ``, in MHz)."""
        ensure_frequency(frequency)
        low, high = self._gen.frequency_range
        c.check_range(frequency, low, high, "MHz", "Start frequency")
        self.write(f"STARTFREQ {c.megahertz(frequency)}")

    def set_stop_frequency(self, frequency: Quantity) -> None:
        """Set the step-sweep stop frequency (``STOPFREQ``, in MHz)."""
        ensure_frequency(frequency)
        low, high = self._gen.frequency_range
        c.check_range(frequency, low, high, "MHz", "Stop frequency")
        self.write(f"STOPFREQ {c.megahertz(frequency)}")

    def set_start_level(self, level: Quantity) -> None:
        """Set the step-sweep start level (``STARTLEV``, in dBm)."""
        ensure_power(level)
        low, high = self._gen.level_range
        c.check_range(level, low, high, "dBm", "Start level")
        self.write(f"STARTLEV {c.dbm(level)}")

    def set_stop_level(self, level: Quantity) -> None:
        """Set the step-sweep stop level (``STOPLEV``, in dBm)."""
        ensure_power(level)
        low, high = self._gen.level_range
        c.check_range(level, low, high, "dBm", "Stop level")
        self.write(f"STOPLEV {c.dbm(level)}")

    def set_dwell(self, dwell: Quantity) -> None:
        """Set the per-point dwell time (``SWPDWELL``, in milliseconds)."""
        self.write(f"SWPDWELL {c.milliseconds(dwell)}")

    def set_points(self, points: int) -> None:
        """Set the number of points in the step sweep (``SWPNUMPTS``)."""
        self.write(f"SWPNUMPTS {int(points)}")

    def set_scale(self, scale: SweepScale) -> None:
        """Set linear or logarithmic point spacing (``SWPSCALE`` ``LIN``/``LOG``)."""
        self.write(f"SWPSCALE {scale}")

    # -- general sweep settings -------------------------------------------
    def set_type(self, sweep_type: SweepType) -> None:
        """Select the step or list sweep engine (``SWPTYPE`` ``STEP``/``LIST``)."""
        self.write(f"SWPTYPE {sweep_type}")

    def set_parameter(self, parameter: SweepParameter) -> None:
        """Select what is swept (``SWPPARAM`` ``FREQ``/``LEV``/``ALL``)."""
        self.write(f"SWPPARAM {parameter}")

    def set_repeat(self, enabled: bool) -> None:
        """Continuous (``True``) vs single (``False``) sweeping (``SWPREPEAT``)."""
        self.write(f"SWPREPEAT {c.onoff(enabled)}")

    def set_direction(self, direction: SweepDirection) -> None:
        """Set the sweep direction (``SWPDIRN`` ``UP``/``DOWN``)."""
        self.write(f"SWPDIRN {direction}")

    def set_display_update(self, enabled: bool) -> None:
        """Update the front-panel display during the sweep (``SWPDISP``)."""
        self.write(f"SWPDISP {c.onoff(enabled)}")

    def set_sync_polarity(self, polarity: SyncPolarity) -> None:
        """Set the SYNC-output active polarity (``SWPSYNC`` ``POS``/``NEG``)."""
        self.write(f"SWPSYNC {polarity}")

    # -- triggering --------------------------------------------------------
    def set_trigger_source(self, source: TriggerSource) -> None:
        """Set the sweep trigger source (``SWP_TRGSRC``)."""
        self.write(f"SWP_TRGSRC {source}")

    def set_point_trigger_source(self, source: TriggerSource) -> None:
        """Set the per-point trigger source (``SWPPT_TRGSRC``)."""
        self.write(f"SWPPT_TRGSRC {source}")

    def set_trigger_enabled(self, enabled: bool) -> None:
        """Enable/disable the sweep trigger (``SWP_TRG_EN``)."""
        self.write(f"SWP_TRG_EN {c.onoff(enabled)}")

    def set_point_trigger_enabled(self, enabled: bool) -> None:
        """Enable/disable the per-point trigger (``SWPPT_TRG_EN``)."""
        self.write(f"SWPPT_TRG_EN {c.onoff(enabled)}")

    def set_trigger_time(self, time: Quantity) -> None:
        """Set the internal trigger-timer period (``SWP_TRGTIME``, in seconds)."""
        self.write(f"SWP_TRGTIME {c.seconds(time)}")

    # -- run control -------------------------------------------------------
    def run(self) -> None:
        """Start the sweep (``SWPRUN``)."""
        self.write("SWPRUN")

    def stop(self) -> None:
        """Stop the sweep (``SWPSTOP``)."""
        self.write("SWPSTOP")

    def get_run_status(self) -> str:
        """Return the sweep run status (``SWPRUNSTAT?`` → ``RUN``/``STOP``)."""
        return c.parse_word(self.query("SWPRUNSTAT?"))

    def is_running(self) -> bool:
        """Return ``True`` if the sweep is currently running."""
        return self.get_run_status() == "RUN"

    def get_trigger_status(self) -> str:
        """Return the sweep trigger status (``SWPTRGSTAT?``)."""
        return c.parse_word(self.query("SWPTRGSTAT?"))

    def get_current_point(self) -> int:
        """Return the current sweep point number (``SWP_PT?``)."""
        return c.parse_int(self.query("SWP_PT?"))

    # -- list sweep --------------------------------------------------------
    def init_list(self) -> None:
        """Reset the sweep list to a single default point (``SWPLISTINIT``)."""
        self.write("SWPLISTINIT")

    def copy_step_to_list(self) -> None:
        """Copy the current step-sweep points into the sweep list (``SWPCOPY``)."""
        self.write("SWPCOPY")

    def set_list_point(
        self, index: int, frequency: Quantity, level: Quantity, dwell: Quantity
    ) -> None:
        """Set one point of the sweep list (``SWPPOINTSET``).

        `index` is the 1-based point number; `frequency`, `level` and `dwell` are
        quantities, sent as MHz, dBm and milliseconds respectively.
        """
        ensure_frequency(frequency)
        ensure_power(level)
        self.write(
            f"SWPPOINTSET {int(index)},{c.megahertz(frequency)},"
            f"{c.dbm(level)},{c.milliseconds(dwell)}"
        )

    def load_list(self, points: Iterable[SweepPoint]) -> None:
        """Download a complete sweep list, replacing the existing one (``SWPLISTSET``).

        `points` is an iterable of ``(frequency, level, dwell)`` quantity triples
        (max 1000). The command is ``SWPLISTSET N,f1,l1,d1,f2,l2,d2,…`` with the
        frequencies in MHz, levels in dBm and dwells in milliseconds.
        """
        triples = list(points)
        fields: list[str] = [str(len(triples))]
        for frequency, level, dwell in triples:
            ensure_frequency(frequency)
            ensure_power(level)
            fields += [c.megahertz(frequency), c.dbm(level), c.milliseconds(dwell)]
        self.write("SWPLISTSET " + ",".join(fields))
