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

!!! note "Status"
    The object model (the classes and their fields) is defined and stable. The
    renderer that turns these objects into a matplotlib figure is the next piece
    to build — calling [`plot`][labkit.plotting.plot.plot] currently raises
    `NotImplementedError`.

Importing `labkit.plotting` does not import matplotlib; only calling `plot()`
does. Install the extra with `pip install "labkit[plotting]"`.

## API reference

::: labkit.plotting.plot

::: labkit.plotting.objects
