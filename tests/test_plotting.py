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


# --- reference geometry, annotations, text panels, layout, theme ---------------

def test_report_style_figure_renders(tmp_path: Path) -> None:
    """Every new primitive in one figure: a plot panel plus a text column, themed."""
    from labkit.plotting import (
        Annotation, DEFAULT_THEME, FigureTitle, GridMajor, HLine, Layout, Span, Swatch, Text, VLine, XTicks,
    )

    f = Q(np.linspace(555, 645, 91), "MHz")
    gain = Q(20 - 0.02 * (F := np.linspace(-45, 45, 91)) ** 2 / 10, "dB")
    fig = plot(
        Layout(width_ratios=[3, 1.3], left=0.07, right=0.98, top=0.85, bottom=0.1, wspace=0.05),
        FigureTitle("Amplifier X Ch1 — S21", subtitle="4 configurations, DUT plane"),
        Panel(0, 0),
        Span(Q(580, "MHz"), Q(620, "MHz")),
        VLine(Q(580, "MHz")), VLine(Q(620, "MHz"), style="--"),
        LinePlot(f, gain, color=DEFAULT_THEME.series[0], width=2.4),
        Marker(Q(560, "MHz"), Q(-5, "dB"), color=DEFAULT_THEME.series[0], edge_color=DEFAULT_THEME.surface, edge_width=1.2),
        HLine(Q(0, "dB"), style="--", from_x=Q(556, "MHz"), to_x=Q(564, "MHz")),
        HLine(Q(-30, "dB"), color="#d03b3b"),
        Annotation("max gain", f[-1], gain[-1]),
        Annotation("cutoff limit", Q(560, "MHz"), Q(-5, "dB"), offset=(30, -20), leader=True, leader_bend=0.2),
        Annotation("placed", Q(560, "MHz"), Q(-5, "dB"), text_at=(Q(600, "MHz"), 10), leader=True),
        XTicks([560, 580, 600, 620, 640], ["560\ncutoff", "580", "600", "620", "640\ncutoff"]),
        Title("Gain over the measured range", align="left", size=10),
        XLabel("Frequency"), YLabel("S21"), GridMajor(axis="y"),
        Panel(0, 1, axes=False),
        Text("Configurations", 0.0, 0.97, weight="bold", size=10.5),
        Swatch(0.0, 0.9, DEFAULT_THEME.series[0], width=2.4),
        Text("att 0 dB, bypass off", 0.09, 0.91),
        Text("✓ PASS", 0.99, 0.85, color=DEFAULT_THEME.good, h_align="right", size=7.5, weight="bold"),
        figsize=(12, 6), save_folder=str(tmp_path), filename="report",
    )
    assert (tmp_path / "report.png").is_file()
    assert len(fig.axes) == 2
    ax, column = fig.axes
    assert ax.get_xlabel() == "Frequency [MHz]"
    assert not column.axison
    assert [t.get_text() for t in ax.get_xticklabels()][0] == "560\ncutoff"
    assert ax.get_title(loc="left") == "Gain over the measured range"
    assert fig.get_facecolor()[:3] == matplotlib.colors.to_rgb(DEFAULT_THEME.surface)
    # figure-level text: title and subtitle
    texts = [t.get_text() for t in fig.texts]
    assert "Amplifier X Ch1 — S21" in texts and "4 configurations, DUT plane" in texts


def test_span_and_lines_take_quantities_or_numbers() -> None:
    from labkit.plotting import HLine, Span, VLine

    fig = plot(LinePlot(Q([1, 2, 3], "MHz"), Q([1, 2, 3], "dB")), Span(1.5, 2.5), VLine(2), HLine(Q(2, "dB")))
    ax = fig.axes[0]
    assert len(ax.patches) == 1
    assert len(ax.lines) == 3  # data, vline, hline


def test_span_rejects_a_missing_bound() -> None:
    from labkit.plotting import Span

    with pytest.raises(PlotError):
        plot(LinePlot([1, 2], [1, 2]), Span(None, 2))


def test_panels_can_span_cells() -> None:
    fig = plot(
        Panel(0, 0), LinePlot([1, 2], [1, 2]),
        Panel(1, 0), LinePlot([1, 2], [2, 1]),
        Panel(0, 1, row_span=2, axes=False),
    )
    assert len(fig.axes) == 3
    tall = fig.axes[2].get_position()
    assert tall.height > fig.axes[0].get_position().height * 1.5


def test_custom_theme_series_and_wrap() -> None:
    from labkit.plotting import Theme

    theme = Theme(series=("#111111", "#222222"))
    assert theme.series_color(0) == "#111111" and theme.series_color(3) == "#222222"
    fig = plot(LinePlot([1, 2], [1, 2]), theme=theme)
    assert fig.get_facecolor()[:3] == matplotlib.colors.to_rgb(theme.surface)
