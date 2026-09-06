"""The declarative plot renderer, with emphasis on quantity handling.

These tests need matplotlib; they are skipped if the plotting extra is not
installed. The Agg backend is forced so nothing tries to open a window.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import numpy as np
import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

from labkit.units import quantity as Q  # noqa: E402
from labkit.plotting import (  # noqa: E402
    LinePlot,
    Marker,
    MarkerLine,
    Legend,
    Panel,
    Title,
    XLabel,
    XLimits,
    YLabel,
    YLimits,
    YTicks,
)
from labkit.plotting.plot import PlotError, plot  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figures() -> Iterator[None]:
    import matplotlib.pyplot as plt

    yield
    plt.close("all")


F = np.linspace(0, 100, 51)


def test_empty_call_raises() -> None:
    with pytest.raises(PlotError):
        plot()


def test_plain_line_saves_png(tmp_path: Path) -> None:
    fig = plot(
        LinePlot([1, 2, 3], [4, 5, 6]),
        XLabel("i"),
        YLabel("v"),
        save_folder=str(tmp_path),
        filename="plain",
    )
    assert (tmp_path / "plain.png").is_file()
    assert fig.axes[0].get_xlabel() == "i"  # no unit suffix for bare numbers


def test_quantity_units_appear_in_labels() -> None:
    fig = plot(
        LinePlot(Q(F, "MHz"), Q(F, "mW")),
        XLabel("Frequency"),
        YLabel("Power"),
    )
    ax = fig.axes[0]
    assert ax.get_xlabel() == "Frequency [MHz]"
    assert ax.get_ylabel() == "Power [mW]"


def test_series_are_converted_to_a_common_axis_unit() -> None:
    # One line in MHz, one in GHz on the same x-axis: both must land on 0..100 MHz.
    fig = plot(
        LinePlot(Q(F, "MHz"), Q(F, "mW")),
        LinePlot(Q(F / 1000, "GHz"), Q(F, "mW")),
    )
    lines = fig.axes[0].get_lines()
    x0 = np.asarray(lines[0].get_xdata(), dtype=float)
    x1 = np.asarray(lines[1].get_xdata(), dtype=float)
    assert float(x0.max()) == pytest.approx(100.0)
    assert float(x1.max()) == pytest.approx(100.0)


def test_dbm_axis_label() -> None:
    fig = plot(LinePlot(Q(F, "MHz"), Q(F - 50, "dBm")), YLabel("Level"))
    assert fig.axes[0].get_ylabel() == "Level [dBm]"


def test_mixing_quantity_and_plain_on_axis_raises() -> None:
    with pytest.raises(PlotError):
        plot(LinePlot(Q(F, "MHz"), Q(F, "mW")), LinePlot(F, F))


def test_incompatible_units_on_axis_raises() -> None:
    with pytest.raises(PlotError):
        plot(LinePlot(Q(F, "MHz"), Q(F, "mW")), LinePlot(Q(F, "MHz"), Q(F, "Hz")))


def test_quantity_limits_are_converted() -> None:
    fig = plot(
        LinePlot(Q(F, "MHz"), Q(F, "mW")),
        XLimits(Q(10, "MHz"), Q(0.09, "GHz")),  # 10 MHz .. 90 MHz
    )
    lo, hi = fig.axes[0].get_xlim()
    assert (lo, hi) == pytest.approx((10.0, 90.0))


def test_numeric_limit_is_interpreted_in_axis_unit() -> None:
    fig = plot(
        LinePlot(Q(F, "MHz"), Q(F, "mW")),
        XLimits(10, 90),  # bare numbers -> already in the axis unit (MHz)
    )
    assert fig.axes[0].get_xlim() == pytest.approx((10.0, 90.0))


def test_dual_y_axis_creates_second_axis() -> None:
    fig = plot(
        LinePlot(Q(F, "MHz"), Q(F, "mW"), color="blue"),
        LinePlot(Q(F, "MHz"), Q(F, "uW"), y_axis="right", color="red"),
        YLabel("Left", y_axis="left"),
        YLabel("Right", y_axis="right"),
        YTicks(color="red", y_axis="right"),
    )
    assert len(fig.axes) == 2
    assert fig.axes[0].get_ylabel() == "Left [mW]"
    assert fig.axes[1].get_ylabel() == "Right [µW]"


def test_multi_panel_grid() -> None:
    fig = plot(
        Panel(0, 0),
        LinePlot(Q(F, "MHz"), Q(F, "mW")),
        Title("top"),
        Panel(1, 0),
        LinePlot(Q(F, "MHz"), Q(F, "mW")),
        Title("bottom"),
    )
    assert len(fig.axes) == 2


def test_markers_and_crosshair_render() -> None:
    fig = plot(
        LinePlot(Q(F, "MHz"), Q(F, "mW")),
        Marker(Q(50, "MHz"), Q(50, "mW"), label="peak"),
        MarkerLine(Q(70, "MHz"), Q(70, "mW"), line_color="green"),
        Legend(),
    )
    # marker + crosshair produced extra artists beyond the single line
    assert len(fig.axes[0].get_lines()) >= 3
