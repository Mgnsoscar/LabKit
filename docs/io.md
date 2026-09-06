# Saving data (CSV)

The CSV writer follows the same declarative style as the plotter: describe the
columns and values you want, then call [`write`][labkit.io.csv.write].

```python
from labkit.io import write, Column, Value

write(
    Value("Operator", "MSO"),          # -> "# Operator: MSO" comment
    Value("Peak", peak_freq),          # -> "# Peak [MHz]: 300.0"
    Column("Frequency", freqs),        # a quantity column -> "Frequency [MHz]"
    Column("Power", powers, unit="dBm"),
    filename="sweep",
    folder="results",                  # created if missing
)
```

A [`Column`][labkit.io.csv.Column] is a data column; a
[`Value`][labkit.io.csv.Value] is a single scalar written as a `#` comment in
the header. Columns need not be the same length — short ones are padded.
[`write`][labkit.io.csv.write] returns the absolute path it wrote.

## Units are handled — and never mislabelled

When data is a LabKit quantity, the header **and** the written values are always
in the same unit:

| `unit=` | Behaviour |
|---------|-----------|
| `""` (default) | auto: quantity written in its own unit and labelled (`"Freq [MHz]"`); a plain column gets no suffix |
| `"mW"` (explicit) | the quantity is **converted** to that unit before writing, and the header uses it |
| `None` | no unit suffix; write the raw magnitude |

!!! note "A prototype pitfall, fixed"
    In the earlier prototype, `unit="MHz"` on a column of GHz data labelled the
    header `MHz` but wrote the original GHz numbers — a silent mislabelling. Here
    an explicit unit converts the data, so the file is always self-consistent.

## API reference

::: labkit.io.csv
