# LabKit

A well-typed, scalable Python framework for automated laboratory measurement
over SCPI/VISA.

LabKit gives you three things that work together:

- **Physical quantities** (`labkit.units`) built on [pint], so a frequency is a
  frequency and a power is a power — you can add `500 * unit("MHz")` to
  `2e8 * unit("Hz")` without thinking about conversions, and logarithmic units
  like `dBm`/`dB` are first-class.
- **Declarative plotting** (`labkit.plotting`) over matplotlib: describe a
  figure as objects (`LinePlot`, `Title`, `Legend`, `Panel`, ...) and render it
  in one call.
- **Instrument control** (`labkit.instruments`): a clean SCPI/VISA base class
  with a *failsafe* shutdown that always leaves hardware in a safe state, plus a
  dummy mode for developing without an instrument attached.

> **Status: early rebuild.** This is a ground-up, better-documented rewrite of
> an earlier prototype. In place: the package skeleton, the units foundation
> **including physically-correct `dBm`/`dB` arithmetic**, the **quantity-aware
> plot renderer**, the **quantity-aware CSV writer**, the instrument base layer
> (with dummy mode), and the utility helpers. Next milestone: the concrete
> instrument drivers. Public APIs may still change before 1.0.

## Install

```bash
pip install -e ".[dev]"      # library + test/type-check tooling
pip install -e ".[all]"      # library + plotting (matplotlib) + instruments (pyvisa)
pip install -e ".[docs]"     # documentation site tooling
```

Only `pint` and `numpy` are required for the core; `matplotlib` and `pyvisa`
are optional extras, imported lazily so `import labkit` stays light.

## Quick taste

```python
from labkit.units import quantity, unit, ensure_power

span = 10 * unit("MHz")
level = quantity(-20, "dBm")
print(level.to("uW"))            # 10.0 microwatt
ensure_power(level)              # raises if it isn't a power

# dBm/dB arithmetic is physically correct:
quantity(0, "dBm") + quantity(3, "dBm")   # 4.76 dBm  (combine powers)
quantity(0, "dBm") + quantity(3, "dB")    # 3 dBm     (apply a gain)
quantity(3, "dBm") - quantity(0, "dBm")   # 3 dB      (power ratio)
```

```python
from labkit.instruments import TestEnvironment, BaseInstrument

class Analyzer(BaseInstrument):
    def _build_address(self, address: str) -> str:
        return f"TCPIP::{address}::INSTR"

class Bench(TestEnvironment):
    analyzer: Analyzer
    def _configure_instruments(self) -> None:
        self.analyzer = Analyzer(self, "Analyzer", "192.168.0.10")

bench = Bench(use_dummy_instruments=True)   # no hardware needed
bench.analyzer.reset_instrument()           # prints the SCPI it would send
```

```python
from labkit.units import quantity
from labkit.plotting import plot, LinePlot, Title, XLabel, YLabel

freqs = quantity(range(0, 1000), "MHz")
plot(
    LinePlot(freqs, power_trace),      # power_trace can be a dBm quantity
    Title("Spectrum"),
    XLabel("Frequency"),               # rendered as "Frequency [MHz]"
    YLabel("Power"),
    show=True,
)
```

## Development

```bash
pytest        # run the test suite
mypy          # strict type-checking
mkdocs serve  # preview the docs (needs the [docs] extra)
```

The autocompletion literals (unit names, fonts, colours) are generated, not
hand-written:

```bash
python scripts/generate_unit_literals.py
python scripts/generate_style_literals.py   # needs matplotlib
```

See [`docs/design/architecture.md`](docs/design/architecture.md) for the
rationale behind the design.

## License

MIT — see [LICENSE](LICENSE).

[pint]: https://pint.readthedocs.io/
