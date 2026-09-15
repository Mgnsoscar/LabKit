# Signal paths

A measurement is taken at the instrument's connector, but the number you want
is the level at the device under test. The cables, attenuators and couplers in
between have a loss that depends on frequency. `labkit.signal_path` models that
chain so a raw measurement can be moved to the DUT reference plane — at
measurement time or long after, from the saved raw data.

```python
from datetime import date
from labkit.signal_path import Component, LossTable, SignalPath
from labkit.units import quantity as Q

cable = Component("SMA cable A", LossTable.from_csv("components/cable_a.csv"), date(2026, 9, 1))
pad   = Component("10 dB pad SN1234", Q(10.2, "dB"), date(2026, 8, 20))

input_path = SignalPath(cable, pad)         # generator -> cable -> pad -> DUT input

f = Q(2.3, "GHz")
input_path.loss_at(f)                       # total loss at 2.3 GHz, in dB
input_path.after(Q(-10, "dBm"), f)          # what the DUT sees when the generator is at -10 dBm
output_path.before(measured, freqs)         # what the DUT delivered, given what the analyzer saw
input_path.describe()                       # "SMA cable A (2026-09-01), 10 dB pad SN1234 (2026-08-20)"
```

## Loss tables interpolate

Components are characterized at one set of frequencies and measured at
another, so [`LossTable`][labkit.signal_path.LossTable] interpolates —
linearly in dB — between its points. Asking for a frequency **outside** the
characterized range raises, because silently extending a characterization is a
classic source of error; pass `extrapolate=True` to clamp to the end values
deliberately.

A loss table is just a CSV with a frequency column and a `dB` column, as
written by [`labkit.io.csv.write`][labkit.io.csv.write]:

```
Frequency [MHz],Loss [dB]
1000.0,0.82
1500.0,0.95
2000.0,1.10
```

## Which direction is which

- `after(level, f)` is the level that comes **out** of the path when `level`
  goes in: `level - loss`. Use it on an **input** path to get the level at the
  DUT input from the generator setting.
- `before(level, f)` is the level that must have gone **in** for `level` to
  come out: `level + loss`. Use it on an **output** path to get the level at
  the DUT output from what the analyzer measured.

Both accept `dBm`/`dBW` or linear powers, scalar or array, with one frequency
per element; the dB arithmetic is the physically-correct kind from
[`labkit.units`](units.md).

## Recording which characterization was used

Every [`Component`][labkit.signal_path.Component] carries the date it was
characterized, and `SignalPath.describe()` renders the whole chain as one line
suitable for a result file's header. Save that alongside raw data so a result
can always be traced to — and re-corrected with — the characterization that
was current when it was measured.

!!! note "Noise figure is the exception"
    Path losses change the noise figure the analyzer's K30 application
    computes, so for that measurement enter them **on the instrument** with
    [`NoiseFigure.set_loss`][labkit.instruments.drivers.rohde_schwarz.noise_figure.NoiseFigure.set_loss]
    or, straight from a path,
    [`NoiseFigure.set_loss_from_path`][labkit.instruments.drivers.rohde_schwarz.noise_figure.NoiseFigure.set_loss_from_path].

## API reference

::: labkit.signal_path
