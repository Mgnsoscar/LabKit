"""The acquisition history: every stored acquisition with its timestamp.

The RTO keeps the acquisitions of a run in memory (up to the fast-segmentation
maximum, see :meth:`~.acquisition.Acquisition.set_fast_segmentation`). After
``STOP`` they are addressed by a history index: 0 is the newest, −1 the one
before, down to ``-(n-1)`` for the oldest of `n` available acquisitions.
Selecting an index makes it the channel's current waveform, so its data and
timestamps can be read like a live one — once the instrument has processed
the selection, which is why :meth:`History.select` waits for ``*OPC?``.

Verified against the *R&S RTO6 User Manual*, chapter 24.10.7 "History":
``CHANnel<m>[:WAVeform<n>]:HISTory[:STATe]``, ``:HISTory:CURRent``,
``:HISTory:TSDate?``, ``:HISTory:TSABsolute?``, ``:HISTory:TSRelative?`` and
``ACQuire:AVAilable?``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ....base import Menu
from . import _common as c

if TYPE_CHECKING:
    from ._oscilloscope import Oscilloscope

__all__ = ["History", "HistoryTimestamp"]

_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


@dataclass(frozen=True)
class HistoryTimestamp:
    """When one stored acquisition was taken, from the instrument's clock.

    `date` and `time` are the instrument's strings as returned (date, and time
    of day with sub-second digits); `relative` is the time in seconds relative
    to the newest acquisition (index 0), so it is zero or negative.
    """

    index: int
    date: str
    time: str
    relative: float


class History(Menu):
    """Access to the stored acquisitions of a channel after ``STOP``."""

    def __init__(self, parent: "Oscilloscope") -> None:
        super().__init__(parent)
        self._scope = parent

    def _cmd(self, channel: int, suffix: str, waveform: int = 1) -> str:
        self._scope.check_channel(channel)
        return f"CHAN{channel}:WAV{waveform}:HIST:{suffix}"

    def available(self) -> int:
        """The number of acquisitions saved in memory (``ACQ:AVA?``)."""
        return c.parse_int(self.query("ACQ:AVA?"))

    def enable(self, channel: int, enabled: bool = True, waveform: int = 1, wait: bool = True) -> None:
        """Switch the history view of the channel on or off (``CHAN<m>:WAV<n>:HIST:STAT``).

        Starting an acquisition leaves the history, so switch it on again after
        every ``STOP`` before selecting acquisitions. The command is
        asynchronous; by default this waits (``*OPC?``) until it has taken effect.
        """
        self.write(f"{self._cmd(channel, 'STAT', waveform)} {c.onoff(enabled)}")
        if wait:
            self._scope.wait_for_instrument()

    def select(self, channel: int, index: int, waveform: int = 1, wait: bool = True) -> None:
        """Make acquisition `index` (0 = newest, negative = older) the channel's current waveform.

        The command is asynchronous: without waiting (``*OPC?``, the default)
        a data or timestamp query sent right after it still answers for the
        previously selected acquisition.
        """
        if index > 0:
            raise ValueError("History index is 0 for the newest acquisition and negative for older ones.")
        self.write(f"{self._cmd(channel, 'CURR', waveform)} {int(index)}")
        if wait:
            self._scope.wait_for_instrument()

    def get_selected(self, channel: int, waveform: int = 1) -> int:
        return c.parse_int(self.query(f"{self._cmd(channel, 'CURR', waveform)}?"))

    def timestamp(self, channel: int, waveform: int = 1) -> HistoryTimestamp:
        """The date, time of day and relative time of the selected acquisition."""
        index = self.get_selected(channel, waveform)
        date = c.parse_name(self.query(f"{self._cmd(channel, 'TSD', waveform)}?"))
        time = c.parse_name(self.query(f"{self._cmd(channel, 'TSAB', waveform)}?"))
        relative = _seconds(self.query(f"{self._cmd(channel, 'TSR', waveform)}?"))
        return HistoryTimestamp(index, date, time, relative)

    def timestamps(self, channel: int, count: int, waveform: int = 1) -> list[HistoryTimestamp]:
        """The timestamps of the `count` newest acquisitions, oldest first.

        Selects each acquisition in turn, so the channel's current waveform is
        the newest one (index 0) when this returns.
        """
        if count < 0:
            raise ValueError("count must not be negative.")
        stamps: list[HistoryTimestamp] = []
        for index in range(-(count - 1), 1) if count else []:
            self.select(channel, index, waveform)
            stamps.append(self.timestamp(channel, waveform))
        return stamps


def _seconds(response: str) -> float:
    """A relative-time response as seconds: a bare number, or a number with a unit (``-1.5 ms``)."""
    text = c.parse_name(response)
    match = _NUMBER.search(text)
    if match is None:
        raise ValueError(f"Unexpected relative-time response: {response!r}")
    value = float(match.group())
    unit = text[match.end():].strip().lower()
    scale = {"": 1.0, "s": 1.0, "ms": 1e-3, "us": 1e-6, "µs": 1e-6, "ns": 1e-9, "ps": 1e-12}
    if unit not in scale:
        raise ValueError(f"Unexpected time unit in relative-time response: {response!r}")
    return value * scale[unit]
