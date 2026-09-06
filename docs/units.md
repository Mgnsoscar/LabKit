# Units & quantities

A **quantity** is a number (or array) with a physical unit attached. Working
with quantities instead of bare floats removes a whole class of silent errors:
you can add a frequency in MHz to one in Hz without converting by hand, and a
value measured in one unit compares equal to the same value in another.

```python
from labkit.units import quantity, unit

quantity("500 MHz") == quantity(0.5, "GHz")   # True
5 * unit("MHz") == quantity(5, "MHz")          # True
quantity(-20, "dBm").to("uW")                  # 10.0 microwatt
```

## Dimensionality guards

When a value only makes sense as a particular kind of quantity, guard it:

```python
from labkit.units import ensure_frequency, ensure_power, is_power

ensure_frequency(quantity(1, "GHz"))   # returns it unchanged
ensure_power(quantity(1, "Hz"))        # raises DimensionalityError
is_power(quantity(3, "dBm"))           # True
```

## Logarithmic units (dBm, dBW, dB)

pint recognises `dBm`/`dB` and converts them correctly (`0 dBm` ↔ `1 mW`), but
its default *arithmetic* on them is not physical. LabKit fixes that: the
operators behave the way an RF engineer expects.

```python
from labkit.units import quantity as Q

Q(0, "dBm") + Q(3, "dBm")     # combine powers ->  4.76 dBm  (1 mW + ~2 mW)
Q(0, "dBm") + Q(3, "dB")      # apply a gain   ->  3 dBm
Q(3, "dBm") - Q(0, "dBm")     # power ratio    ->  3 dB
Q(3, "dB")  + Q(3, "dB")      # cascade gains  ->  6 dB
```

| Operation | Result | Meaning |
|-----------|--------|---------|
| power `+` power | log-power | add powers in the linear domain |
| power `+` ratio | log-power | apply a gain |
| ratio `+` ratio | ratio | cascade gains |
| power `-` power | ratio (dB) | ratio of two levels |
| power `-` ratio | log-power | apply a loss |
| ratio `-` ratio | ratio | difference of gains |

!!! warning "Construction and scaling"
    Build logarithmic quantities with `quantity(value, "dBm")`, **not**
    `value * unit("dBm")` — multiplication is undefined for logarithmic units.
    Any operation that isn't physically meaningful (adding a bare number to a
    level, multiplying or dividing a `dBm`/`dB` value, ...) raises
    `LogArithmeticError`. To scale a power or take a raw ratio, convert to a
    linear unit first: `(p.to("mW") * 2).to("dBm")`.

`dB` is treated as a **power** ratio (`10·log10`), consistent with `dBm`.

## API reference

::: labkit.units.quantity

::: labkit.units.kinds

::: labkit.units._logarithmic

::: labkit.units.registry
