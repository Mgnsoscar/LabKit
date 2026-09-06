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

## Logarithmic units

pint recognises `dBm`/`dB` and converts them correctly (`0 dBm` ↔ `1 mW`).
Physically-correct *arithmetic* on logarithmic units — adding two `dBm` powers
by combining them in the linear domain — is LabKit's own contribution and is
the next milestone; see [Design & rationale](design/architecture.md).

## API reference

::: labkit.units.quantity

::: labkit.units.kinds

::: labkit.units.registry
