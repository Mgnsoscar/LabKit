# Design & rationale

LabKit is a ground-up rebuild of an earlier prototype. The prototype proved out
the ideas; this rebuild keeps the good ideas and fixes the things that made it
hard to grow. This page records *why* the current design is the way it is.

## Goals

- **Correctness you can trust.** Units and logarithmic-unit arithmetic should be
  right, and provably so via tests.
- **Well documented.** Every public class and function carries a docstring; the
  docs site is generated from them.
- **Scalable.** Adding a new instrument or plot element should not mean copying
  a 500-line file.

## Package shape

A `src/` layout (`src/labkit/...`) so tests run against the installed package,
not against whatever happens to be on the path. The library is split into small
sub-packages — `units`, `plotting`, `io`, `instruments`, `utils` — each usable
on its own.

Only `pint` and `numpy` are hard dependencies. `matplotlib` (plotting) and
`pyvisa` (instruments) are **optional extras**, and their imports are deferred
until the relevant feature is used, so `import labkit` is cheap and a
units-only user need not install a plotting or VISA stack.

## Units: pint, not monkey-patched astropy

The prototype built on `astropy.units` and monkey-patched astropy's internals
(replacing `LogQuantity.__add__`, popping registry entries, and so on) to make
`dBm`/`dB` behave the way an RF engineer expects. That worked but was fragile:
it reached into another library's internals and applied process-wide side
effects that could break with any astropy update.

LabKit uses [pint](https://pint.readthedocs.io/) instead. pint has the same
breadth of units, first-class support for offset and logarithmic units, a
supported extension model, and better static typing.

### The logarithmic-unit problem is real either way

Neither library adds `dBm` correctly out of the box. pint parses and converts
`dBm` fine (`0 dBm` ↔ `1 mW`), but:

```python
>>> quantity(0, "dBm") + quantity(3, "dBm")
1.99e-06 kilogram ** 2 * meter ** 4 / second ** 6   # nonsense
```

The physically-correct answer combines the powers in the **linear** domain
(1 mW + 2 mW = 3 mW ≈ 4.77 dBm). That behaviour — the prototype's real
contribution — is implemented on top of pint in `labkit.units._logarithmic`
and covered by `tests/test_logarithmic.py`:

- `dBm + dBm` → add in the linear domain, return `dBm`
- `dBm + dB` → apply a gain, return `dBm`
- `dBm − dBm` → a dimensionless `dB` ratio
- `dB ± dB` → cascade/difference of gains, return `dB`
- everything else involving a log operand (adding a bare number, multiplying,
  dividing) → `LogArithmeticError` with guidance

### How, without a global monkey-patch

A pint registry owns its own `Quantity` class, so LabKit installs a log-aware
`Quantity` subclass onto **its** registry (`install_log_arithmetic`). Only
quantities from LabKit's registry get the behaviour; other pint users in the
same process are untouched. This is the key improvement over the prototype's
astropy monkey-patching, which changed global state.

### Multiplication is deliberately rejected, not guessed

pint routes `n * unit(X)` through `Quantity(1, X) * n`, so there is no way to
make `n * unit("dBm")` *construct* `n dBm` while also giving `dBm * n` a
sensible scaling meaning — the two collide. Rather than pick a silent behaviour
that surprises half the time, LabKit rejects multiplication/division on
logarithmic operands and directs the user to construct with
`quantity(value, "dBm")` and to scale via a linear unit. Correct-by-refusal
beats convenient-but-wrong.

## Plotting: declarative objects

Plots are described as small dataclasses (`LinePlot`, `Marker`, `Title`,
`Legend`, `Panel`, ...) passed to a single `plot()` call. This keeps figure
descriptions composable and serialisable, and keeps matplotlib specifics in one
renderer instead of scattered through measurement scripts.

The renderer's job is **quantity handling**, which is where the prototype's
plotter had trouble. matplotlib does not understand physical quantities, so the
renderer resolves one unit per axis (x, left-y, right-y), converts every series
and limit on that axis to it, and hands matplotlib bare magnitudes. Two concrete
prototype bugs this fixes:

- Limits (`min_x`, `XLimits`, ...) were compared against quantity data with a
  bare `x < min_x`, which raises for a quantity-vs-number comparison. Limits are
  now converted to the axis unit first, and may themselves be quantities.
- Series in different units (MHz and GHz) were plotted as raw magnitudes on a
  shared axis, so they misaligned. They are now converted to a common unit, and
  that unit is appended to the axis label automatically.

No global matplotlib unit support (`pint.setup_matplotlib()`) is installed; the
renderer extracts magnitudes itself, keeping behaviour local — the same
no-global-state principle as the units layer.

## Instruments: one base, no copy-paste

The prototype had byte-identical 500-line files copy-pasted across instruments
(the FSV and FPL analyzers shared the same `sweep`/`marker`/`trace`; the PNA and
ZNLE18 shared the same `sweep`/`trace`). That is the single biggest scalability
problem to avoid.

The rebuild puts all shared behaviour in
[`BaseInstrument`][labkit.instruments.base.BaseInstrument] and groups related
commands with [`Menu`][labkit.instruments.base.Menu]. Shared measurement modes
(a sweep, a trace) will be written **once** as reusable mixins/menus and shared
by the drivers that support them, rather than duplicated per instrument.

Two things the prototype got right are kept and fixed:

- **Failsafe shutdown.** A registry closes every instrument at interpreter exit.
  (The prototype's `shutdown()` had an indentation bug that closed resource
  managers inside the per-instrument loop; fixed in
  [`labkit.instruments.registry`][labkit.instruments.registry].)
- **Dummy mode.** A [`DummyBackend`][labkit.instruments.base.DummyBackend] prints
  SCPI instead of sending it, so drivers and tests run without hardware.

## Autocompletion literals, generated not pasted

The prototype's nicest DX touch was typing `Unit("")` and getting every unit as
an editor suggestion, via a giant `Literal[...]`. LabKit keeps this, but the
literal files are **generated by committed scripts**
(`scripts/generate_unit_literals.py`, `scripts/generate_style_literals.py`) that
introspect the pint registry and matplotlib, and validate every entry. This
fixes two prototype problems: a hand-pasted, machine-specific font list, and
lists that could drift out of sync with what the library actually understands.
Unit names are also scoped to lab-relevant categories rather than every unit
pint ships.

## Quality bar

- **pytest** — the test suite covers unit conversions, dimensionality guards,
  the full logarithmic-arithmetic matrix, dummy-mode instruments, failsafe
  shutdown ordering, and the utilities.
- **mypy (strict)** — the package ships `py.typed` and type-checks under strict
  mode (with `disallow_any_generics` relaxed only for pint's generic types).
- **mkdocs** — this site, generated from the docstrings.

## Roadmap

1. ~~Physically-correct `dBm`/`dB` arithmetic.~~ **Done** — see
   `labkit.units._logarithmic` and the [units guide](../units.md).
2. ~~The plotting renderer (quantity-aware).~~ **Done** — see
   `labkit.plotting.plot` and the [plotting guide](../plotting.md).
3. ~~The CSV writer (quantity-aware).~~ **Done** — see `labkit.io.csv` and the
   [saving-data guide](../io.md).
4. Concrete instrument drivers, with shared measurement modes factored out.
   **In progress** — the R&S `FSV3007` and `FPL1003` spectrum analyzers share
   one `SpectrumAnalyzer` base built from reusable menus
   (`labkit.instruments.drivers.rohde_schwarz`), including the Spectrum
   measurement functions (channel power, ACLR, OBW, SEM/spurious, time-domain
   power, harmonics, TOI, AM depth) and the Noise Figure (K30) application
   reached through the `INSTrument` channel controls; the R&S `ZNLE18` vector network
   analyzer shares a `NetworkAnalyzer` base built the same way
   (`labkit.instruments.drivers.rohde_schwarz.vna`); and the Aim-TTi `TGR6000` RF
   signal generator shares a `SignalGenerator` base
   (`labkit.instruments.drivers.aim_tti`). No command logic is duplicated
   between models — where the prototype shipped byte-identical files per
   instrument. Every driver is tested with a scriptable `MockBackend` (no
   hardware), and its commands are verified against the manufacturer's
   remote-control manual.
