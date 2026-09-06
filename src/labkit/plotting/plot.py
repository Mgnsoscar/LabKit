"""The :func:`plot` entry point.

:func:`plot` takes the declarative objects from :mod:`labkit.plotting.objects`
and renders them into a single matplotlib figure, optionally showing and/or
saving it.

Status
------
Skeleton. The rendering pipeline (grid/panel layout, dual y-axes, z-ordering,
limit clipping, absolute-point margins) is the next piece to build. The
signature and contract below are stable; the body raises
:class:`NotImplementedError` for now.

`matplotlib` is imported lazily inside this function so that ``import labkit``
does not require it — only calling :func:`plot` does. Install it with
``pip install "labkit[plotting]"``.
"""

from __future__ import annotations

from typing import Optional

from .objects import PlotObject

__all__ = ["plot", "set_default_font"]


def _require_matplotlib() -> None:
    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError as exc:  # pragma: no cover - trivial guard
        raise ModuleNotFoundError(
            "labkit.plotting requires matplotlib. Install it with "
            '`pip install "labkit[plotting]"`.'
        ) from exc


def plot(
    *objects: PlotObject,
    figsize: Optional[tuple[float, float]] = None,
    show: bool = False,
    save_folder: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    """Render declarative plot objects into a matplotlib figure.

    Parameters
    ----------
    *objects:
        Plot elements from :mod:`labkit.plotting.objects`. A :class:`Panel`
        begins a new sub-plot; elements after it belong to that panel.
    figsize:
        Figure size in inches, ``(width, height)``.
    show:
        If ``True``, display the figure interactively.
    save_folder, filename:
        If both are given, save the figure as a PNG at that location.
    """
    _require_matplotlib()
    if not objects:
        raise ValueError("plot() requires at least one plot object.")
    raise NotImplementedError(
        "The rendering pipeline is not implemented yet. This is the next "
        "milestone of the LabKit rebuild."
    )


def set_default_font(font: str) -> None:
    """Set the default font used for new figures.

    Status: skeleton — not implemented yet.
    """
    _require_matplotlib()
    raise NotImplementedError
