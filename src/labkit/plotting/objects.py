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

Quantities
----------
``x``/``y`` data and axis limits/ticks may be plain numbers/arrays **or** LabKit
quantities. When any series on an axis carries a unit, that axis becomes a
"quantity axis": every series and limit on it is converted to one common unit
(the first series' unit) before plotting, and the unit is appended to the axis
label automatically. Mixing quantities with bare numbers on the same axis is an
error, because the intended unit would be ambiguous. See
:func:`labkit.plotting.plot` for the details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

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
    "YAxis",
    "Axis",
]

#: Which y-axis a series or label belongs to.
YAxis = str  # Literal["left", "right"]
#: Which axis a scale applies to.
Axis = str  # Literal["x", "y"]

# ``x``/``y`` data: a sequence, a numpy array, or a LabKit quantity (scalar or
# array). A limit: a number or a quantity. Kept as ``Any`` because the accepted
# runtime types are deliberately broad.
ArrayLike = Any
LimitValue = Any


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
    range instead of dropping them, so the line breaks cleanly; each may be a
    number (in the axis unit) or a quantity.
    """

    x: ArrayLike
    y: ArrayLike
    label: Optional[str] = None
    y_axis: YAxis = "left"
    color: Optional[ColorName] = None
    width: Optional[float] = None
    style: Optional[LineStyle] = None
    alpha: Optional[float] = None
    min_x: LimitValue = None
    max_x: LimitValue = None
    min_y: LimitValue = None
    max_y: LimitValue = None


@dataclass
class Marker(PlotObject):
    """A single marked point at ``(x, y)``. `x`/`y` may be numbers or quantities."""

    x: LimitValue
    y: LimitValue
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
    """The x-axis label. The axis unit is appended automatically when present."""

    text: str
    font: Optional[str] = None
    size: Optional[float] = None
    show_unit: bool = True


@dataclass
class YLabel(PlotObject):
    """The y-axis label (left axis unless ``y_axis="right"``)."""

    text: str
    y_axis: YAxis = "left"
    font: Optional[str] = None
    size: Optional[float] = None
    show_unit: bool = True


@dataclass
class XTicks(PlotObject):
    """Explicit x-axis tick positions and/or labels.

    `positions` may be numbers or quantities; quantities are converted to the
    axis unit.
    """

    positions: Optional[ArrayLike] = None
    labels: Optional[Iterable[str]] = None
    rotation: Optional[float] = None
    color: Optional[ColorName] = None


@dataclass
class YTicks(PlotObject):
    """Explicit y-axis tick positions and/or labels."""

    positions: Optional[ArrayLike] = None
    labels: Optional[Iterable[str]] = None
    rotation: Optional[float] = None
    color: Optional[ColorName] = None
    y_axis: YAxis = "left"


@dataclass
class Legend(PlotObject):
    """Add a legend to the panel (collects labels from both y-axes)."""

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
    """Fix the x-axis range. Bounds may be numbers or quantities."""

    lower: LimitValue = None
    upper: LimitValue = None


@dataclass
class YLimits(PlotObject):
    """Fix the y-axis range. Bounds may be numbers or quantities."""

    lower: LimitValue = None
    upper: LimitValue = None
    y_axis: YAxis = "left"


@dataclass
class LogScale(PlotObject):
    """Set an axis to a logarithmic scale."""

    axis: Axis = "x"
    base: float = 10.0


@dataclass
class LinScale(PlotObject):
    """Set an axis to a linear scale."""

    axis: Axis = "x"
