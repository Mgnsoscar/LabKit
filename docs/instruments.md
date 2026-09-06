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

The spectrum-analyzer drivers are the Rohde & Schwarz
[`FSV3007`][labkit.instruments.drivers.rohde_schwarz.fsv3007.FSV3007] (7.5 GHz)
and [`FPL1003`][labkit.instruments.drivers.rohde_schwarz.fpl1003.FPL1003]
(3 GHz). Both expose the instrument through **menus** — grouped commands you
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
`Display`, `ReferenceOscillator`) and the measurement control (trigger, marker,
`measure_trace`) live in a shared
[`SpectrumAnalyzer`][labkit.instruments.drivers.rohde_schwarz._spectrum_analyzer.SpectrumAnalyzer]
base. `FSV3007` and `FPL1003` are just that base with their own identity — no
command logic is duplicated between them. The prototype copy-pasted
byte-identical 500-line `sweep`/`trace`/`marker` files across the FSV and FPL;
here they share one implementation, and adding another FSV-family analyzer is a
few lines.

## Signal generators

The RF signal-generator driver is the Aim-TTi
[`TGR6000`][labkit.instruments.drivers.aim_tti.tgr6000.TGR6000] (6 GHz). It
follows the same menu structure as the analyzers, built from a shared
[`SignalGenerator`][labkit.instruments.drivers.aim_tti._signal_generator.SignalGenerator]
base so a future TGR-family generator reuses it:

```python
from labkit.units import quantity
from labkit.instruments import TGR6000

gen = ...  # a TGR6000 from your TestEnvironment

gen.frequency.set_frequency(quantity(2.45, "GHz"))   # FREQ, in MHz
gen.output.set_level(quantity(-10, "dBm"))           # DBMLEV
gen.output.set_rf_enabled(True)                       # RFON

gen.sweep.set_type("STEP")
gen.sweep.set_start_frequency(quantity(1, "GHz"))
gen.sweep.set_stop_frequency(quantity(2, "GHz"))
gen.sweep.set_points(101)
gen.sweep.set_dwell(quantity(10, "ms"))
gen.sweep.run()
```

Menus: `frequency`, `output` (level + RF on/off), `sweep` (step and list
sweeps, triggering, run control), `reference` (10 MHz socket), `system`
(self-test, error queues, stores). Setters are quantity-checked and
range-checked against the model (10 MHz – 6 GHz, −110 dBm – +7 dBm). The
failsafe `_shutdown_procedure` forces the RF output **off** when the session
ends.

!!! warning "TGR6000 remote-command limitations"
    Everything above is taken from the *TGR6000 Instruction Manual, Iss 9*.
    Two limitations are inherent to the instrument, not the driver:

    - **No modulation.** The TGR6000 is a CW/sweep generator; its command set
      has no AM/FM/ΦM/pulse commands. The
      [`modulation`][labkit.instruments.drivers.aim_tti.modulation.Modulation]
      menu exists only to report this — its setters raise
      `ModulationNotSupportedError`.
    - **No read-back of frequency/level.** The remote language has no query
      form for `FREQ` or the level commands, so those settings are set-only.
      Sweep status, error queues, self-test and `*IDN?` *can* be queried.

    The TGR6000 is a raw-socket instrument: it is addressed as
    `TCPIP0::<ip>::9221::SOCKET`, takes line-feed command terminators, and
    replies with `CR`/`LF`.

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
    The R&S analyzer commands follow the standard R&S FSV3000 / FSW
    remote-control set; validate against your firmware if a command behaves
    unexpectedly. The Aim-TTi TGR6000 commands are taken directly from its
    Instruction Manual (Iss 9). VNAs are the next drivers.

## API reference

::: labkit.instruments.environment

::: labkit.instruments.base

::: labkit.instruments.mock

::: labkit.instruments.drivers.rohde_schwarz._spectrum_analyzer

::: labkit.instruments.drivers.rohde_schwarz.fsv3007

::: labkit.instruments.drivers.rohde_schwarz.fpl1003

::: labkit.instruments.drivers.aim_tti._signal_generator

::: labkit.instruments.drivers.aim_tti.tgr6000

::: labkit.instruments.drivers.aim_tti.frequency

::: labkit.instruments.drivers.aim_tti.output

::: labkit.instruments.drivers.aim_tti.sweep

::: labkit.instruments.drivers.aim_tti.modulation

::: labkit.instruments.drivers.aim_tti.reference

::: labkit.instruments.drivers.aim_tti.system

::: labkit.instruments.registry
