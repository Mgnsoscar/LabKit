"""The trigger: mode, source, type, edge, level, holdoff.

The RTO has three trigger events, A (1), B (2) and R (3); everything here
addresses the A-trigger unless another `event` is given. Trigger levels are
per source: ``TRIGger<m>:LEVel<n>`` where ``<n>`` is the channel number
(1–4) or 5 for the external trigger input.

Verified against the *R&S RTO6 User Manual*, chapter 24.9 "Trigger":
``TRIGger<m>:SOURce``, ``TRIGger<m>:TYPE``, ``TRIGger<m>:LEVel<n>[:VALue]``,
``TRIGger<m>:FINDlevel``, ``TRIGger<m>:EDGE:SLOPe``, ``TRIGger<m>:MODE``,
``TRIGger<m>:FORCe``, ``TRIGger<m>:HOLDoff:MODE`` / ``:TIME`` / ``:EVENts``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

from .....units import Quantity, ensure_time
from ....base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._oscilloscope import Oscilloscope

__all__ = ["Trigger", "TriggerMode", "TriggerType", "Slope", "HoldoffMode"]

#: What the instrument does when no trigger occurs.
TriggerMode = Literal["AUTO", "NORMAL", "FREERUN"]
_MODE_SCPI = {"AUTO": "AUTO", "NORMAL": "NORM", "FREERUN": "FRE"}

#: The trigger types available for analog channels and the external input.
TriggerType = Literal[
    "EDGE", "GLITCH", "WIDTH", "RUNT", "WINDOW", "TIMEOUT", "INTERVAL", "SLEWRATE",
    "STATE", "PATTERN", "SETHOLD",
]
_TYPE_SCPI = {
    "EDGE": "EDGE", "GLITCH": "GLIT", "WIDTH": "WIDT", "RUNT": "RUNT", "WINDOW": "WIND",
    "TIMEOUT": "TIM", "INTERVAL": "INT", "SLEWRATE": "SLEW", "STATE": "STAT",
    "PATTERN": "PATT", "SETHOLD": "SETH",
}

Slope = Literal["POSITIVE", "NEGATIVE", "EITHER"]
_SLOPE_SCPI = {"POSITIVE": "POS", "NEGATIVE": "NEG", "EITHER": "EITH"}

HoldoffMode = Literal["OFF", "TIME", "EVENTS", "RANDOM", "AUTO"]
_HOLDOFF_SCPI = {"OFF": "OFF", "TIME": "TIME", "EVENTS": "EVEN", "RANDOM": "RAND", "AUTO": "AUTO"}

#: The level suffix of the external trigger input.
_EXTERNAL_LEVEL_INDEX = 5


class Trigger(Menu):
    """Trigger settings; `event` 1 = A (default), 2 = B, 3 = R."""

    def __init__(self, parent: "Oscilloscope") -> None:
        super().__init__(parent)
        self._scope = parent

    @staticmethod
    def _check_event(event: int) -> None:
        if event not in (1, 2, 3):
            raise ValueError("Trigger event must be 1 (A), 2 (B) or 3 (R).")

    def _source_scpi(self, source: str) -> tuple[str, int]:
        """``("CHAN2", 2)`` for channel 2, ``("EXT", 5)`` for the external input."""
        text = str(source).strip().upper()
        if text in ("EXT", "EXTERNAL", "EXTERNANALOG"):
            return "EXT", _EXTERNAL_LEVEL_INDEX
        digits = text[2:] if text.startswith("CH") else text[4:] if text.startswith("CHAN") else text
        if not digits.isdigit():
            raise ValueError(f"Unknown trigger source {source!r}; use 'CH1'..'CH4' or 'EXT'.")
        number = int(digits)
        self._scope.check_channel(number)
        return f"CHAN{number}", number

    # -- mode / source / type ----------------------------------------------
    def set_mode(self, mode: TriggerMode, event: int = 1) -> None:
        """Set the trigger mode (``TRIG<m>:MODE``): ``AUTO``, ``NORMAL`` or ``FREERUN``."""
        self._check_event(event)
        self.write(f"TRIG{event}:MODE {_MODE_SCPI[mode]}")

    def get_mode(self, event: int = 1) -> str:
        return self.query(f"TRIG{event}:MODE?").strip()

    def set_source(self, source: str, event: int = 1) -> None:
        """Set the trigger source (``TRIG<m>:SOUR``): ``"CH1"``..``"CH4"`` or ``"EXT"``."""
        self._check_event(event)
        scpi, _ = self._source_scpi(source)
        self.write(f"TRIG{event}:SOUR {scpi}")

    def get_source(self, event: int = 1) -> str:
        return self.query(f"TRIG{event}:SOUR?").strip()

    def set_type(self, trigger_type: TriggerType, event: int = 1) -> None:
        """Set the trigger type (``TRIG<m>:TYPE``), e.g. ``EDGE`` or ``WIDTH``."""
        self._check_event(event)
        self.write(f"TRIG{event}:TYPE {_TYPE_SCPI[trigger_type]}")

    def get_type(self, event: int = 1) -> str:
        return self.query(f"TRIG{event}:TYPE?").strip()

    # -- edge --------------------------------------------------------------
    def set_edge_slope(self, slope: Slope, event: int = 1) -> None:
        """Set the edge for the edge trigger (``TRIG<m>:EDGE:SLOP``)."""
        self._check_event(event)
        self.write(f"TRIG{event}:EDGE:SLOP {_SLOPE_SCPI[slope]}")

    def get_edge_slope(self, event: int = 1) -> str:
        return self.query(f"TRIG{event}:EDGE:SLOP?").strip()

    # -- level -------------------------------------------------------------
    def set_level(self, level: Quantity, source: str, event: int = 1) -> None:
        """Set the trigger level for `source` (``TRIG<m>:LEV<n>``), a voltage quantity."""
        self._check_event(event)
        _, index = self._source_scpi(source)
        self.write(f"TRIG{event}:LEV{index} {c.volts(level)}")

    def get_level(self, source: str, event: int = 1) -> Quantity:
        _, index = self._source_scpi(source)
        return c.as_volts(self.query(f"TRIG{event}:LEV{index}?"))

    def find_level(self, event: int = 1) -> None:
        """Let the instrument set the level from the signal (``TRIG<m>:FIND``); analog sources only."""
        self._check_event(event)
        self.write(f"TRIG{event}:FIND")

    def force(self, event: int = 1) -> None:
        """Provoke one acquisition now, in normal mode without a valid trigger (``TRIG<m>:FORC``)."""
        self._check_event(event)
        self.write(f"TRIG{event}:FORC")

    # -- holdoff -----------------------------------------------------------
    def set_holdoff(self, mode: HoldoffMode, time: Optional[Quantity] = None, events: Optional[int] = None) -> None:
        """Set the holdoff (``TRIG:HOLD:MODE``) and its time (``:TIME``) or event count (``:EVEN``).

        Holdoff exists for the A-trigger only.
        """
        self.write(f"TRIG:HOLD:MODE {_HOLDOFF_SCPI[mode]}")
        if time is not None:
            ensure_time(time)
            self.write(f"TRIG:HOLD:TIME {c.seconds(time)}")
        if events is not None:
            if events < 1:
                raise ValueError("Holdoff events must be at least 1.")
            self.write(f"TRIG:HOLD:EVEN {int(events)}")

    def get_holdoff_mode(self) -> str:
        return self.query("TRIG:HOLD:MODE?").strip()

    # -- convenience ---------------------------------------------------------
    def edge(
        self,
        source: str,
        level: Quantity,
        slope: Slope = "POSITIVE",
        mode: TriggerMode = "NORMAL",
        event: int = 1,
    ) -> None:
        """Set up an edge trigger in one call: source, type, slope, level and mode."""
        self.set_source(source, event)
        self.set_type("EDGE", event)
        self.set_edge_slope(slope, event)
        self.set_level(level, source, event)
        self.set_mode(mode, event)
