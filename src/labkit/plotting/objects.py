"""Declarative plot-description objects.

Rather than issuing imperative matplotlib calls, you *describe* a figure as a
sequence of small objects and hand them to :func:`labkit.plotting.plot`. Each
class here is a plain dataclass carrying the configuration for one element of a
figure — a line, a marker, an axis label, a legend, and so on.

    plot(
        LinePlot(freqs, powers, label="trace 1"),
        Title("Measured spectrum"),
        XLabel("Frequency"),
        YLabel("Power"),
        Legend(),
    )

A :class:`Panel` starts a new sub-plot; every object after it belongs to that
panel, which is what makes multi-panel figures composable.

Status
------
This module defines the public *shape* of the plotting API — the classes and
their fields. The rendering logic that turns these objects into a matplotlib
figure lives in :mod:`labkit.plotting.plot` and is not implemented yet; see the
note there.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from ._literals import ColorName, LegendLoc, LineStyle, MarkerStyle

__all__ = [
    "PlotObject",
    "Panel",
    "LinePlot",
    "Marker",
    "MarkerLine",
    "Title",
    "XLabel",
    "YLabel",
    "XTicks",
    "YTicks",
    "Legend",
    "GridMajor",
    "GridMinor",
    "XLimits",
    "YLimits",
    "LogScale",
    "LinScale",
]

# A y-axis selector: the left (default) or the twinned right axis.
YAxis = str  # Literal["left", "right"]; kept loose until rendering lands.


@dataclass
class PlotObject:
    """Base class for every declarative plot element."""


@dataclass
class Panel(PlotObject):
    """Start a new sub-plot at grid position ``(row, column)``.

    Objects passed to :func:`plot` after a ``Panel`` are drawn in that panel.
    If no ``Panel`` is given, everything goes into a single default panel.
    """

    row: int = 0
    column: int = 0


@dataclass
class LinePlot(PlotObject):
    """A line: `x` values against `y` values, optionally styled.

    `x` and `y` may be plain sequences, numpy arrays, or LabKit quantities.
    The ``min_*``/``max_*`` bounds blank out (set to NaN) points outside the
    range instead of dropping them, so the line breaks cleanly.
    """

    x: Iterable[float]
    y: Iterable[float]
    label: Optional[str] = None
    y_axis: YAxis = "left"
    color: Optional[ColorName] = None
    width: Optional[float] = None
    style: Optional[LineStyle] = None
    alpha: Optional[float] = None
    min_x: Optional[float] = None
    max_x: Optional[float] = None
    min_y: Optional[float] = None
    max_y: Optional[float] = None


@dataclass
class Marker(PlotObject):
    """A single marked point at ``(x, y)``."""

    x: float
    y: float
    label: Optional[str] = None
    y_axis: YAxis = "left"
    color: Optional[ColorName] = None
    style: MarkerStyle = "o"
    size: Optional[float] = None
    alpha: Optional[float] = None


@dataclass
class MarkerLine(Marker):
    """A marked point with guide lines dropped to each axis."""

    line_color: Optional[ColorName] = None
    line_style: LineStyle = "--"
    line_width: Optional[float] = None


@dataclass
class Title(PlotObject):
    """The panel title."""

    text: str
    font: Optional[str] = None
    size: Optional[float] = None


@dataclass
class XLabel(PlotObject):
    """The x-axis label."""

    text: str
    font: Optional[str] = None
    size: Optional[float] = None


@dataclass
class YLabel(PlotObject):
    """The y-axis label (left axis unless ``y_axis="right"``)."""

    text: str
    y_axis: YAxis = "left"
    font: Optional[str] = None
    size: Optional[float] = None


@dataclass
class XTicks(PlotObject):
    """Explicit x-axis tick positions and/or labels."""

    positions: Optional[Iterable[float]] = None
    labels: Optional[Iterable[str]] = None
    rotation: Optional[float] = None


@dataclass
class YTicks(PlotObject):
    """Explicit y-axis tick positions and/or labels."""

    positions: Optional[Iterable[float]] = None
    labels: Optional[Iterable[str]] = None
    rotation: Optional[float] = None
    y_axis: YAxis = "left"


@dataclass
class Legend(PlotObject):
    """Add a legend to the panel."""

    location: LegendLoc = "best"
    title: Optional[str] = None


@dataclass
class GridMajor(PlotObject):
    """Major grid lines."""

    color: Optional[ColorName] = None
    style: LineStyle = "-"
    width: Optional[float] = None
    alpha: Optional[float] = None


@dataclass
class GridMinor(GridMajor):
    """Minor grid lines."""


@dataclass
class XLimits(PlotObject):
    """Fix the x-axis range."""

    lower: Optional[float] = None
    upper: Optional[float] = None


@dataclass
class YLimits(PlotObject):
    """Fix the y-axis range."""

    lower: Optional[float] = None
    upper: Optional[float] = None
    y_axis: YAxis = "left"


@dataclass
class LogScale(PlotObject):
    """Set an axis to a logarithmic scale."""

    axis: str = "x"  # Literal["x", "y"]
    base: float = 10.0


@dataclass
class LinScale(PlotObject):
    """Set an axis to a linear scale."""

    axis: str = "x"  # Literal["x", "y"]
