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
panel, which is what makes multi-panel figures composable. A panel may span
several grid cells, and a panel with ``axes=False`` is a blank canvas for
:class:`Text` and :class:`Swatch` objects — a results column or a hand-made
legend next to the plots. :class:`Layout` and :class:`FigureTitle` describe
the figure as a whole and may appear anywhere in the object list.

Besides the data (:class:`LinePlot`, :class:`Marker`), a panel can carry
reference geometry — a shaded :class:`Span`, a :class:`VLine`/:class:`HLine`
limit — and sparing direct labels (:class:`Annotation`, with an optional
leader line to the point it names).

Colours
-------
Every ``color`` accepts a matplotlib colour: one of the :data:`ColorName`
literals (for completion) or any hex string. :mod:`labkit.plotting.theme`
holds the default palette; ``theme.series[i]`` gives series *i* its fixed hue.

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
from typing import Any, Iterable, Optional, Union

from ._literals import ColorName, LegendLoc, LineStyle, MarkerStyle

__all__ = [
    "PlotObject",
    "Panel",
    "Layout",
    "FigureTitle",
    "LinePlot",
    "Marker",
    "MarkerLine",
    "Span",
    "VLine",
    "HLine",
    "Annotation",
    "Text",
    "Swatch",
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
    "ColorLike",
    "TextWeight",
    "HAlign",
    "VAlign",
]

#: Which y-axis a series or label belongs to.
YAxis = str  # Literal["left", "right"]
#: Which axis a scale applies to.
Axis = str  # Literal["x", "y"]
#: A colour: a :data:`ColorName` literal or any matplotlib colour string (``"#2a78d6"``).
ColorLike = Union[ColorName, str]
#: Text weight.
TextWeight = str  # Literal["normal", "bold"]
#: Horizontal / vertical text alignment.
HAlign = str  # Literal["left", "center", "right"]
VAlign = str  # Literal["top", "center", "bottom", "baseline"]

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
    A panel may span several cells (``row_span``/``column_span``); with
    ``axes=False`` it is a blank canvas (no axes drawn) for :class:`Text` and
    :class:`Swatch` objects placed in panel fractions.
    """

    row: int = 0
    column: int = 0
    row_span: int = 1
    column_span: int = 1
    axes: bool = True


@dataclass
class Layout(PlotObject):
    """The figure grid: relative panel sizes and the margins, all optional.

    Ratios are per grid column/row; margins and gaps are figure fractions.
    Without a ``Layout`` the panels are equal-sized and matplotlib's tight
    layout places them.
    """

    width_ratios: Optional[list[float]] = None
    height_ratios: Optional[list[float]] = None
    left: Optional[float] = None
    right: Optional[float] = None
    top: Optional[float] = None
    bottom: Optional[float] = None
    #: Gap between rows / columns, as a fraction of the average panel height / width.
    hspace: Optional[float] = None
    wspace: Optional[float] = None


@dataclass
class FigureTitle(PlotObject):
    """A title (and optional subtitle line) for the whole figure, top left."""

    text: str
    subtitle: Optional[str] = None
    size: Optional[float] = None
    subtitle_size: Optional[float] = None


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
    color: Optional[ColorLike] = None
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
    color: Optional[ColorLike] = None
    style: MarkerStyle = "o"
    size: Optional[float] = None
    alpha: Optional[float] = None
    #: Edge (ring) colour and width, e.g. the surface colour so the marker stays legible on a line.
    edge_color: Optional[ColorLike] = None
    edge_width: Optional[float] = None


@dataclass
class MarkerLine(Marker):
    """A marked point with guide lines dropped to each axis."""

    line_color: Optional[ColorLike] = None
    line_style: LineStyle = "--"
    line_width: Optional[float] = None


@dataclass
class Span(PlotObject):
    """A shaded band between two values across the panel — the passband, a window.

    ``axis="x"`` shades between two x values over the panel's full height;
    ``axis="y"`` between two y values over its full width. Bounds may be
    numbers (in the axis unit) or quantities.
    """

    lower: LimitValue
    upper: LimitValue
    axis: Axis = "x"
    color: Optional[ColorLike] = None
    alpha: Optional[float] = None
    label: Optional[str] = None


@dataclass
class VLine(PlotObject):
    """A vertical reference line across the panel at `x` (a number or quantity)."""

    x: LimitValue
    color: Optional[ColorLike] = None
    style: LineStyle = "-"
    width: Optional[float] = None
    alpha: Optional[float] = None
    label: Optional[str] = None


@dataclass
class HLine(PlotObject):
    """A horizontal reference line across the panel at `y` (a number or quantity)."""

    y: LimitValue
    color: Optional[ColorLike] = None
    style: LineStyle = "-"
    width: Optional[float] = None
    alpha: Optional[float] = None
    label: Optional[str] = None
    y_axis: YAxis = "left"
    #: Restrict the line to a range of x (numbers or quantities); the full width if omitted.
    from_x: LimitValue = None
    to_x: LimitValue = None


@dataclass
class Annotation(PlotObject):
    """A short text anchored to a data point, offset by `offset` points.

    With ``leader=True`` a thin line connects the text to the point. Use it
    sparingly — the end of a line, the one extreme the story is about.
    """

    text: str
    x: LimitValue
    y: LimitValue
    offset: tuple[float, float] = (6.0, 0.0)
    #: Put the text at this data position instead of at `offset` from the point
    #: (numbers in the axis units or quantities); with a leader, the line runs from here to the point.
    text_at: Optional[tuple[LimitValue, LimitValue]] = None
    y_axis: YAxis = "left"
    color: Optional[ColorLike] = None
    size: Optional[float] = None
    weight: Optional[TextWeight] = None
    h_align: HAlign = "left"
    v_align: VAlign = "center"
    leader: bool = False
    leader_color: Optional[ColorLike] = None
    #: Curvature of the leader (0 = straight; positive bends one way, negative the other).
    leader_bend: float = 0.0


@dataclass
class Text(PlotObject):
    """Free text placed in panel fractions (``0..1`` from the bottom left).

    The building block of a text panel (``Panel(axes=False)``): headings,
    table rows, notes. Multi-line strings are allowed.
    """

    text: str
    x: float
    y: float
    color: Optional[ColorLike] = None
    size: Optional[float] = None
    weight: Optional[TextWeight] = None
    h_align: HAlign = "left"
    v_align: VAlign = "top"
    line_spacing: Optional[float] = None


@dataclass
class Swatch(PlotObject):
    """A short line key in panel fractions — a legend entry drawn by hand next to a :class:`Text`."""

    x: float
    y: float
    color: ColorLike
    length: float = 0.06
    width: Optional[float] = None
    style: LineStyle = "-"
    alpha: Optional[float] = None


@dataclass
class Title(PlotObject):
    """The panel title."""

    text: str
    font: Optional[str] = None
    size: Optional[float] = None
    align: HAlign = "center"
    color: Optional[ColorLike] = None
    weight: Optional[TextWeight] = None


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
    color: Optional[ColorLike] = None


@dataclass
class YTicks(PlotObject):
    """Explicit y-axis tick positions and/or labels."""

    positions: Optional[ArrayLike] = None
    labels: Optional[Iterable[str]] = None
    rotation: Optional[float] = None
    color: Optional[ColorLike] = None
    y_axis: YAxis = "left"


@dataclass
class Legend(PlotObject):
    """Add a legend to the panel (collects labels from both y-axes)."""

    location: LegendLoc = "best"
    title: Optional[str] = None


@dataclass
class GridMajor(PlotObject):
    """Major grid lines (``axis="y"`` for horizontal lines only)."""

    color: Optional[ColorLike] = None
    style: LineStyle = "-"
    width: Optional[float] = None
    alpha: Optional[float] = None
    axis: str = "both"  # Literal["both", "x", "y"]


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
