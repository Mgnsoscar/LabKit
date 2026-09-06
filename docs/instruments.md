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

## Drivers

The first concrete driver is the Rohde & Schwarz
[`FSV3007`][labkit.instruments.drivers.rohde_schwarz.fsv3007.FSV3007] spectrum
analyzer. It exposes the instrument through **menus** — grouped commands you
reach as attributes:

```python
from labkit.units import quantity
from labkit.instruments import FSV3007, TestEnvironment

sa = ...  # an FSV3007 from your TestEnvironment

sa.frequency.set_center(quantity(1, "GHz"))
sa.frequency.set_span(quantity(10, "MHz"))
sa.bandwidth.set_rbw(quantity(100, "kHz"))
sa.sweep.set_count(10)
sa.amplitude.set_ref_level(quantity(-10, "dBm"))
sa.trace.set_detector("RMS")

freqs, levels = sa.measure_trace()        # single sweep -> quantity arrays
peak = sa.marker(1, enable=True)
peak.peak_search()
print(peak.get_x().to("MHz"), peak.get_y())
```

Every setter takes a quantity and is dimensionality-checked — passing a power to
`frequency.set_center` raises rather than sending a wrong command. Getters return
quantities (`get_center()` → a frequency, `trace.get_data()` → a frequency array
and a dBm array).

### One implementation, many analyzers

The menus (`Frequency`, `Bandwidth`, `Sweep`, `Amplitude`, `Trace`, `Marker`,
`Display`, `ReferenceOscillator`) live in
`labkit.instruments.drivers.rohde_schwarz` and are **composed** by the driver.
The prototype copy-pasted byte-identical 500-line `sweep`/`trace`/`marker` files
across the FSV and FPL analyzers; here the shared logic is written once, so a
future FPL1003 driver reuses the same menus.

## Testing drivers without hardware

[`mock_instrument`][labkit.instruments.mock.mock_instrument] wires a real driver
to a [`MockBackend`][labkit.instruments.mock.MockBackend] that records every SCPI
string and answers queries from a script — so you can assert exactly what a
driver sends and feed it canned responses:

```python
from labkit.instruments import FSV3007, mock_instrument

sa, backend = mock_instrument(FSV3007, responses={"*IDN?": "R&S,FSV3007,..."})
sa.frequency.set_center(quantity(1, "GHz"))
assert "FREQ:CENT 1000000000.0" in backend.writes

backend.on("TRAC:DATA? TRACE1", "-50.0,-30.0,-55.0")
freqs, levels = sa.trace.get_data()       # parses the scripted response
```

!!! note "SCPI accuracy"
    The FSV3007 commands follow the standard R&S FSV3000 / FSW remote-control
    set. The R&S documentation site was not reachable from the build
    environment, so validate against your firmware if a command behaves
    unexpectedly. VNAs and signal generators are the next drivers.

## API reference

::: labkit.instruments.environment

::: labkit.instruments.base

::: labkit.instruments.mock

::: labkit.instruments.drivers.rohde_schwarz.fsv3007

::: labkit.instruments.registry
