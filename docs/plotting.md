# Plotting

LabKit's plotting layer is **declarative**: instead of a sequence of imperative
matplotlib calls, you describe a figure as objects and render it in one call.

```python
from labkit.plotting import plot, LinePlot, Title, XLabel, YLabel, Legend

plot(
    LinePlot(freqs, powers, label="trace 1"),
    Title("Measured spectrum"),
    XLabel("Frequency"),
    YLabel("Power"),
    Legend(),
    show=True,
)
```

A [`Panel`][labkit.plotting.objects.Panel] starts a new sub-plot; every object
after it belongs to that panel, which is how multi-panel figures compose.
[`plot`][labkit.plotting.plot.plot] returns the matplotlib `Figure` so you can
tweak or save it further.

## Quantities on axes

The renderer understands LabKit quantities, which matplotlib does not. It
resolves **one unit per axis** and converts everything on that axis to it:

```python
plot(
    LinePlot(freqs_in_mhz, power),      # x in MHz
    LinePlot(freqs_in_ghz, power2),     # x in GHz -> converted to MHz
    XLabel("Frequency"),                 # rendered as "Frequency [MHz]"
    YLabel("Power"),
)
```

- The unit is taken from the first series that carries one; other series are
  converted, and the unit is appended to the axis label automatically.
- **Limits, marker coordinates and tick positions** may be quantities *or* bare
  numbers (interpreted as already in the axis unit) — so
  `XLimits(quantity(10, "MHz"), quantity(90, "MHz"))` and `XLimits(10, 90)` both
  work. (In the old prototype, comparing quantity data against a unitless limit
  raised; here it does not.)
- Mixing quantities with bare numbers on the same axis, or incompatible units,
  raises a clear `PlotError` instead of silently mis-plotting.

Logarithmic quantities work too: a `dBm` series plots its dB values against a
`[dBm]` axis, and because axis conversion uses the unit machinery, `dBm`↔`dBW`
and `mW`↔`dBm` conversions between series are handled correctly.

## Reference geometry, annotations and text panels

Beyond lines and markers, a panel can carry a shaded
[`Span`][labkit.plotting.objects.Span] (a passband, a window), a
[`VLine`][labkit.plotting.objects.VLine]/[`HLine`][labkit.plotting.objects.HLine]
reference or limit, and sparing [`Annotation`][labkit.plotting.objects.Annotation]s
anchored to a data point, with an optional leader line. A panel with
`axes=False` is a blank canvas for [`Text`][labkit.plotting.objects.Text] and
[`Swatch`][labkit.plotting.objects.Swatch] objects placed in panel fractions —
the way to put a results table or a hand-made legend *beside* the plot instead
of on top of the data. [`Layout`][labkit.plotting.objects.Layout] sets the
grid's ratios and margins; [`FigureTitle`][labkit.plotting.objects.FigureTitle]
puts a title and subtitle line over the whole figure; panels may span cells.

```python
plot(
    Layout(width_ratios=[3, 1.3], left=0.07, right=0.98, top=0.85, bottom=0.1),
    FigureTitle("Amplifier X Ch1 — S21", subtitle="4 configurations, DUT plane"),
    Panel(0, 0),
    Span(Q(580, "MHz"), Q(620, "MHz")),                    # the passband
    LinePlot(f, gain, color=DEFAULT_THEME.series[0], width=2.4),
    Annotation("max gain", f[-1], gain[-1]),               # direct label at the line end
    HLine(Q(-30, "dB"), style="--"),                       # a limit
    XTicks([560, 580, 600, 620, 640], ["560\ncutoff", "580", "600", "620", "640\ncutoff"]),
    Title("Gain over the measured range", align="left", size=10),
    XLabel("Frequency"), YLabel("S21"), GridMajor(axis="y"),
    Panel(0, 1, axes=False),                               # the results column
    Text("Configurations", 0.0, 0.97, weight="bold"),
    Swatch(0.0, 0.9, DEFAULT_THEME.series[0], width=2.4),
    Text("att 0 dB, bypass off", 0.09, 0.91),
    figsize=(12, 6),
)
```

## Theme

Every figure is drawn in a [`Theme`][labkit.plotting.theme.Theme]: a light
surface, hairline grid and axes, secondary ink for labels, and a fixed
categorical palette (`theme.series[i]`) whose neighbouring hues stay apart for
colour-vision-deficient readers. Give series their colours **in order** and
keep them when the set of series changes. `theme.good` and `theme.critical`
are for verdicts only. Pass `plot(..., theme=Theme(...))` to restyle.

Importing `labkit.plotting` does not import matplotlib; only calling `plot()`
does. Install the extra with `pip install "labkit[plotting]"`. No global
matplotlib unit support is installed — the renderer extracts magnitudes itself.

## API reference

::: labkit.plotting.plot

::: labkit.plotting.objects

::: labkit.plotting.theme
