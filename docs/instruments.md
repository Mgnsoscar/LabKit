# Instruments

Subclass [`TestEnvironment`][labkit.instruments.environment.TestEnvironment] to
declare your bench, and [`BaseInstrument`][labkit.instruments.base.BaseInstrument]
to write a driver.

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

## Dummy mode

Passing `use_dummy_instruments=True` gives every instrument a
[`DummyBackend`][labkit.instruments.base.DummyBackend] that prints and records
SCPI instead of sending it. This lets you develop and test driver logic — and
run LabKit's own test suite — with neither `pyvisa` nor a physical instrument.

## Failsafe shutdown

Every instrument is registered on creation and closed at interpreter exit, no
matter how a script ends. Each driver's `_shutdown_procedure` runs first (to
leave hardware safe — e.g. RF output off), then the VISA session is closed. See
[`labkit.instruments.registry`][labkit.instruments.registry].

!!! note "Status"
    The base layer, dummy mode and failsafe shutdown work today. Concrete
    drivers (spectrum analyzers, VNAs, signal generators) will live under
    `labkit.instruments.drivers` and are the next milestone.

## API reference

::: labkit.instruments.environment

::: labkit.instruments.base

::: labkit.instruments.registry
