"""Declarative plotting for LabKit, layered over `matplotlib`.

Describe a figure as objects and render it in one call::

    from labkit.plotting import plot, LinePlot, Title, XLabel, YLabel, Legend

    plot(
        LinePlot(freqs, powers, label="trace 1"),
        Title("Measured spectrum"),
        XLabel("Frequency"),
        YLabel("Power"),
        Legend(),
        show=True,
    )

Importing this package does not import matplotlib; only calling :func:`plot`
does. Install the plotting extra with ``pip install "labkit[plotting]"``.
"""

from __future__ import annotations

from ._literals import ColorName, FontName, LegendLoc, LineStyle, MarkerStyle
from .objects import (
    GridMajor,
    GridMinor,
    Legend,
    LinePlot,
    LinScale,
    LogScale,
    Marker,
    MarkerLine,
    Panel,
    PlotObject,
    Title,
    XLabel,
    XLimits,
    XTicks,
    YLabel,
    YLimits,
    YTicks,
)
from .plot import plot, set_default_font

__all__ = [
    "plot",
    "set_default_font",
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
    "LineStyle",
    "MarkerStyle",
    "LegendLoc",
    "FontName",
    "ColorName",
]
