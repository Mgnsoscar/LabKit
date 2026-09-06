# LabKit

A well-typed, scalable Python framework for automated laboratory measurement
over SCPI/VISA.

LabKit is organised into small, independently useful pieces:

- **[Units & quantities](units.md)** — physical quantities built on
  [pint](https://pint.readthedocs.io/), including logarithmic units (`dBm`,
  `dB`).
- **[Plotting](plotting.md)** — a declarative layer over matplotlib.
- **[Instruments](instruments.md)** — SCPI/VISA control with a failsafe
  shutdown and an offline dummy mode.

!!! warning "Early rebuild"
    LabKit is a ground-up, better-documented rewrite of an earlier prototype.
    The skeleton, the units foundation, the instrument base layer (with dummy
    mode) and the utilities are in place; physically-correct `dBm`/`dB`
    arithmetic, the plot renderer, the CSV writer and the concrete instrument
    drivers are the next milestones. See
    [Design & rationale](design/architecture.md) for the roadmap.

## Install

```bash
pip install -e ".[dev]"      # library + test/type-check tooling
pip install -e ".[all]"      # + plotting (matplotlib) + instruments (pyvisa)
pip install -e ".[docs]"     # documentation site tooling
```

Only `pint` and `numpy` are required for the core. `matplotlib` and `pyvisa`
are optional and imported lazily, so `import labkit` stays light.
