"""The figure theme: one quiet, consistent look for every LabKit figure.

A :class:`Theme` holds the chart chrome (surface, inks, hairline grid and
axes), a fixed categorical palette for data series, and the two status
colours. :func:`labkit.plotting.plot` renders every figure inside the
theme's matplotlib settings, so figures read as one system without any
per-figure styling.

The default palette is a validated set: adjacent hues stay distinguishable
for colour-vision-deficient readers, and every hue clears the surface. Assign
series colours **in order** (``theme.series[0]`` for the first series, and so
on) and keep a series' colour when the set of series changes — colour
identifies the entity, not its rank. Two lighter hues (aqua, yellow) sit
below 3:1 contrast on the light surface, which is why a legend or a results
table beside the plot must name what they are.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Theme", "DEFAULT_THEME", "rc_params"]


@dataclass(frozen=True)
class Theme:
    """Colours and type for a figure. Values are matplotlib colour strings."""

    #: Chart surface (figure and panel background).
    surface: str = "#fcfcfb"
    #: Primary ink: titles, headline numbers.
    ink: str = "#0b0b0b"
    #: Secondary ink: axis labels, notes, subtitles.
    ink_secondary: str = "#52514e"
    #: Muted ink: tick marks, table headers.
    muted: str = "#898781"
    #: Hairline gridlines.
    grid: str = "#e1e0d9"
    #: Axis spines and band edges.
    axis: str = "#c3c2b7"
    #: A light wash for a shaded :class:`~labkit.plotting.objects.Span`.
    wash: str = "#e1e0d9"
    #: Categorical palette, in order: blue, orange, aqua, yellow, magenta, green, violet, red.
    series: tuple[str, ...] = (
        "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948",
    )
    #: Status colours — only for a verdict, never for a data series.
    good: str = "#0ca30c"
    critical: str = "#d03b3b"
    font: str = "DejaVu Sans"
    font_size: float = 12.0
    #: The alpha a :class:`~labkit.plotting.objects.Span` is washed with unless it says otherwise.
    span_alpha: float = 0.45
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)

    def series_color(self, index: int) -> str:
        """The palette colour of series `index`; past the palette it wraps, so fold the tail into fewer series."""
        return self.series[index % len(self.series)]


DEFAULT_THEME = Theme()


def rc_params(theme: Theme) -> dict[str, Any]:
    """The matplotlib rc settings that realise `theme` (used as an ``rc_context`` by ``plot``)."""
    return {
        "font.family": theme.font,
        "font.size": theme.font_size,
        "figure.facecolor": theme.surface,
        "savefig.facecolor": theme.surface,
        "axes.facecolor": theme.surface,
        "axes.edgecolor": theme.axis,
        "axes.linewidth": 0.8,
        "axes.labelcolor": theme.ink_secondary,
        "axes.titlecolor": theme.ink,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": _cycler(theme.series),
        "xtick.color": theme.muted,
        "ytick.color": theme.muted,
        "xtick.labelcolor": theme.ink_secondary,
        "ytick.labelcolor": theme.ink_secondary,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "grid.color": theme.grid,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "lines.linewidth": 1.6,
        "lines.solid_capstyle": "round",
        "legend.frameon": False,
        "legend.labelcolor": theme.ink_secondary,
        "text.color": theme.ink,
    }


def _cycler(colors: tuple[str, ...]) -> Any:
    from cycler import cycler  # ships with matplotlib

    return cycler(color=list(colors))
