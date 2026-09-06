"""The :func:`plot` entry point and its rendering pipeline.

:func:`plot` takes the declarative objects from :mod:`labkit.plotting.objects`
and renders them into a single matplotlib figure, optionally showing and/or
saving it, and returns the figure.

Quantity handling
-----------------
This is where the renderer earns its keep. matplotlib does not understand
physical quantities, so the renderer resolves **one unit per axis** and converts
everything on that axis to it before handing bare magnitudes to matplotlib:

- The x-axis, the left y-axis and the right y-axis are each resolved
  independently. The unit is taken from the first series on that axis that
  carries one; every other series and every limit/tick on that axis is
  converted to it (raising a clear error if the dimensionality is incompatible).
- Axis limits, marker coordinates and explicit tick positions may be given as
  quantities *or* as bare numbers (interpreted as already being in the axis
  unit). This avoids the classic bug of comparing a quantity against a unitless
  limit.
- Mixing quantities and bare numbers on the *same* axis is rejected, because the
  intended unit would be ambiguous.
- The resolved unit is appended to the axis label automatically (``"Frequency
  [MHz]"``).

No global matplotlib unit support is installed; the renderer extracts magnitudes
itself, keeping the behaviour local and predictable.

`matplotlib` is imported lazily so ``import labkit`` does not require it. Install
it with ``pip install "labkit[plotting]"``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import numpy as np

from ..units import is_quantity, ureg
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

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

__all__ = ["plot", "set_default_font"]


class PlotError(ValueError):
    """Raised for an inconsistent plot description (e.g. mixed units on an axis)."""


def _require_matplotlib() -> Any:
    try:
        import matplotlib
    except ModuleNotFoundError as exc:  # pragma: no cover - trivial guard
        raise ModuleNotFoundError(
            "labkit.plotting requires matplotlib. Install it with "
            '`pip install "labkit[plotting]"`.'
        ) from exc
    return matplotlib


# --- quantity <-> magnitude helpers ----------------------------------------

def _normalize(data: Any) -> Any:
    """Turn a list/tuple of quantity scalars into a single quantity array."""
    if isinstance(data, (list, tuple)) and len(data) > 0 and is_quantity(data[0]):
        base = data[0].units
        values = [q.to(base).magnitude for q in data]
        return ureg.Quantity(np.asarray(values, dtype=float), base)
    return data


def _resolve_unit(datas: list[Any], axis_name: str) -> Any:
    """Pick the common unit for an axis, or ``None`` if it carries bare numbers."""
    quantity_units = [d.units for d in datas if is_quantity(d)]
    plain_present = any(not is_quantity(d) for d in datas)
    if not quantity_units:
        return None
    if plain_present:
        raise PlotError(
            f"The {axis_name}-axis mixes quantities with bare numbers. Give every "
            f"{axis_name} value a unit, or none of them."
        )
    return quantity_units[0]


def _magnitude(data: Any, unit: Any, axis_name: str) -> np.ndarray:
    """Magnitudes of `data` expressed in `unit` (or as-is if `unit` is None)."""
    if unit is None:
        if is_quantity(data):
            raise PlotError(f"Unexpected unit on the {axis_name}-axis.")
        return np.asarray(data, dtype=float)
    if not is_quantity(data):
        raise PlotError(
            f"The {axis_name}-axis has unit '{unit:~}', but a value has no unit. "
            "Wrap it with a unit (e.g. quantity(...))."
        )
    try:
        converted = data.to(unit)
    except Exception as exc:
        raise PlotError(
            f"Cannot plot a value with unit '{data.units:~}' on the "
            f"{axis_name}-axis whose unit is '{unit:~}'."
        ) from exc
    return np.asarray(converted.magnitude, dtype=float)


def _scalar(data: Any, unit: Any, axis_name: str) -> float:
    return float(_magnitude(data, unit, axis_name).reshape(-1)[0])


def _limit(value: Any, unit: Any, axis_name: str) -> Optional[float]:
    """A limit value as a magnitude in the axis unit (number = already in it)."""
    if value is None:
        return None
    if is_quantity(value):
        return _scalar(value, unit, axis_name)
    return float(value)


def _unit_suffix(unit: Any) -> str:
    return "" if unit is None else f" [{unit:~}]"


# --- clipping ---------------------------------------------------------------

def _clip(
    x: np.ndarray,
    y: np.ndarray,
    min_x: Optional[float],
    max_x: Optional[float],
    min_y: Optional[float],
    max_y: Optional[float],
) -> tuple[np.ndarray, np.ndarray]:
    """Blank (NaN) points outside the given bounds so the line breaks there."""
    if all(v is None for v in (min_x, max_x, min_y, max_y)):
        return x, y
    x, y = x.astype(float).copy(), y.astype(float).copy()
    lo_x = -np.inf if min_x is None else min_x
    hi_x = np.inf if max_x is None else max_x
    lo_y = -np.inf if min_y is None else min_y
    hi_y = np.inf if max_y is None else max_y
    bad = (x < lo_x) | (x > hi_x) | (y < lo_y) | (y > hi_y)
    x[bad] = np.nan
    y[bad] = np.nan
    return x, y


# --- panel grouping ---------------------------------------------------------

def _group_panels(objects: list[PlotObject]) -> list[tuple[Panel, list[PlotObject]]]:
    groups: list[tuple[Panel, list[PlotObject]]] = []
    current: tuple[Panel, list[PlotObject]] = (Panel(), [])
    started = False
    for obj in objects:
        if isinstance(obj, Panel):
            if started:
                groups.append(current)
            current = (obj, [])
            started = True
        else:
            current[1].append(obj)
    groups.append(current)
    return groups


# --- rendering one panel ----------------------------------------------------

def _render_panel(fig: "Figure", ax: "Axes", objs: list[PlotObject]) -> None:
    # Draw order: later objects sit on top of earlier ones.
    order = {id(o): i for i, o in enumerate(objs)}

    def _z(obj: PlotObject) -> int:
        return 2 + order.get(id(obj), 0)

    series = [o for o in objs if isinstance(o, (LinePlot, Marker))]

    # Resolve one unit per axis (x is shared; y split left/right).
    x_datas = [_normalize(s.x) for s in series]
    for s, xd in zip(series, x_datas):
        s.x = xd
    left = [s for s in series if s.y_axis != "right"]
    right = [s for s in series if s.y_axis == "right"]
    for s in series:
        s.y = _normalize(s.y)

    x_unit = _resolve_unit(x_datas, "x")
    left_unit = _resolve_unit([s.y for s in left], "left y")
    right_unit = _resolve_unit([s.y for s in right], "right y")

    needs_right = bool(right) or any(
        getattr(o, "y_axis", "left") == "right"
        for o in objs
        if isinstance(o, (YLabel, YTicks, YLimits))
    )
    ax2 = ax.twinx() if needs_right else None

    def axis_for(y_axis: str) -> tuple["Axes", Any, str]:
        if y_axis == "right":
            assert ax2 is not None
            return ax2, right_unit, "right y"
        return ax, left_unit, "left y"

    # --- data
    for s in series:
        target, y_unit, y_name = axis_for(s.y_axis)
        if isinstance(s, LinePlot):
            xm = _magnitude(s.x, x_unit, "x")
            ym = _magnitude(s.y, y_unit, y_name)
            if xm.shape != ym.shape:
                raise PlotError("x and y must have the same length.")
            xm, ym = _clip(
                xm, ym,
                _limit(s.min_x, x_unit, "x"), _limit(s.max_x, x_unit, "x"),
                _limit(s.min_y, y_unit, y_name), _limit(s.max_y, y_unit, y_name),
            )
            kwargs = _drop_none(
                color=s.color, linewidth=s.width, linestyle=s.style,
                alpha=s.alpha, label=s.label,
            )
            target.plot(xm, ym, zorder=_z(s), **kwargs)
        else:  # Marker / MarkerLine
            xp = _scalar(s.x, x_unit, "x")
            yp = _scalar(s.y, y_unit, y_name)
            kwargs = _drop_none(
                color=s.color, markersize=s.size, alpha=s.alpha, label=s.label,
            )
            target.plot([xp], [yp], marker=s.style, linestyle="None",
                        zorder=_z(s), **kwargs)

    # --- scales (before limits)
    for obj in objs:
        if isinstance(obj, LogScale):
            (ax.set_xscale if obj.axis == "x" else ax.set_yscale)("log", base=obj.base)
        elif isinstance(obj, LinScale):
            (ax.set_xscale if obj.axis == "x" else ax.set_yscale)("linear")

    # --- limits
    for obj in objs:
        if isinstance(obj, XLimits):
            ax.set_xlim(_limit(obj.lower, x_unit, "x"), _limit(obj.upper, x_unit, "x"))
        elif isinstance(obj, YLimits):
            target, y_unit, y_name = axis_for(obj.y_axis)
            target.set_ylim(
                _limit(obj.lower, y_unit, y_name), _limit(obj.upper, y_unit, y_name)
            )

    # --- marker crosshairs (need finalized limits)
    for ml in objs:
        if isinstance(ml, MarkerLine):
            target, y_unit, y_name = axis_for(ml.y_axis)
            xp = _scalar(ml.x, x_unit, "x")
            yp = _scalar(ml.y, y_unit, y_name)
            x0 = ax.get_xlim()[0]
            y0 = target.get_ylim()[0]
            line_kwargs = _drop_none(
                color=ml.line_color, linestyle=ml.line_style, linewidth=ml.line_width,
            )
            target.plot([x0, xp], [yp, yp], zorder=_z(ml), **line_kwargs)
            target.plot([xp, xp], [y0, yp], zorder=_z(ml), **line_kwargs)

    # --- grids
    for obj in objs:
        if isinstance(obj, GridMinor):
            ax.minorticks_on()
            ax.grid(True, which="minor", **_drop_none(
                color=obj.color, linestyle=obj.style, linewidth=obj.width, alpha=obj.alpha,
            ))
        elif isinstance(obj, GridMajor):
            ax.grid(True, which="major", **_drop_none(
                color=obj.color, linestyle=obj.style, linewidth=obj.width, alpha=obj.alpha,
            ))

    # --- ticks
    for obj in objs:
        if isinstance(obj, XTicks):
            if obj.positions is not None:
                ax.set_xticks(_magnitude(_normalize(obj.positions), x_unit, "x"))
            if obj.labels is not None:
                ax.set_xticklabels(list(obj.labels))
            ax.tick_params(axis="x", **_drop_none(
                labelrotation=obj.rotation, colors=obj.color,
            ))
        elif isinstance(obj, YTicks):
            target, y_unit, y_name = axis_for(obj.y_axis)
            if obj.positions is not None:
                target.set_yticks(_magnitude(_normalize(obj.positions), y_unit, y_name))
            if obj.labels is not None:
                target.set_yticklabels(list(obj.labels))
            target.tick_params(axis="y", **_drop_none(
                labelrotation=obj.rotation, colors=obj.color,
            ))

    # --- labels & title
    for obj in objs:
        if isinstance(obj, XLabel):
            suffix = _unit_suffix(x_unit) if obj.show_unit else ""
            ax.set_xlabel(obj.text + suffix, **_font_kwargs(obj.font, obj.size))
        elif isinstance(obj, YLabel):
            target, y_unit, _ = axis_for(obj.y_axis)
            suffix = _unit_suffix(y_unit) if obj.show_unit else ""
            target.set_ylabel(obj.text + suffix, **_font_kwargs(obj.font, obj.size))
        elif isinstance(obj, Title):
            ax.set_title(obj.text, **_font_kwargs(obj.font, obj.size))

    # --- legend (collect from both axes)
    legend = next((o for o in objs if isinstance(o, Legend)), None)
    if legend is not None:
        handles, labels = ax.get_legend_handles_labels()
        if ax2 is not None:
            h2, l2 = ax2.get_legend_handles_labels()
            handles += h2
            labels += l2
        if handles:
            ax.legend(handles, labels, **_drop_none(loc=legend.location, title=legend.title))


def _drop_none(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}


def _font_kwargs(font: Optional[str], size: Optional[float]) -> dict[str, Any]:
    return _drop_none(fontfamily=font, fontsize=size)


# --- public API -------------------------------------------------------------

def plot(
    *objects: PlotObject,
    figsize: Optional[tuple[float, float]] = None,
    show: bool = False,
    save_folder: Optional[str] = None,
    filename: Optional[str] = None,
) -> "Figure":
    """Render declarative plot objects into a matplotlib figure.

    Parameters
    ----------
    *objects:
        Plot elements from :mod:`labkit.plotting.objects`. A :class:`Panel`
        begins a new sub-plot; elements after it belong to that panel.
    figsize:
        Figure size in inches, ``(width, height)``. Defaults to ``(8, 5)`` for a
        single panel and grows with the grid.
    show:
        If ``True``, display the figure interactively.
    save_folder, filename:
        If both are given, save the figure as a PNG at that location.

    Returns
    -------
    matplotlib.figure.Figure
        The rendered figure, so callers can tweak or save it further.
    """
    _require_matplotlib()
    import os

    import matplotlib.pyplot as plt

    if not objects:
        raise PlotError("plot() requires at least one plot object.")

    panels = _group_panels(list(objects))
    n_rows = max((p.row for p, _ in panels), default=0) + 1
    n_cols = max((p.column for p, _ in panels), default=0) + 1

    if figsize is None:
        figsize = (8 * n_cols, 5 * n_rows)

    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(n_rows, n_cols)

    for panel, panel_objs in panels:
        ax = fig.add_subplot(gs[panel.row, panel.column])
        _render_panel(fig, ax, panel_objs)

    fig.tight_layout()

    if save_folder is not None and filename is not None:
        os.makedirs(save_folder, exist_ok=True)
        if not filename.lower().endswith(".png"):
            filename += ".png"
        fig.savefig(os.path.join(save_folder, filename), dpi=320)

    if show:
        plt.show()

    return fig


def set_default_font(font: str) -> None:
    """Set the default font family used for new figures."""
    _require_matplotlib()
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = font
