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

Importing `labkit.plotting` does not import matplotlib; only calling `plot()`
does. Install the extra with `pip install "labkit[plotting]"`. No global
matplotlib unit support is installed — the renderer extracts magnitudes itself.

## API reference

::: labkit.plotting.plot

::: labkit.plotting.objects
