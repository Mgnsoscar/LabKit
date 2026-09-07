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

### Measurement modes

Beyond a plain frequency sweep, the analyzers expose the Spectrum application's
"Meas" functions through the `measurement` menu — verified against the R&S
FSVA3000/FSV3000 User Manual:

```python
sa.sweep.set_continuous(False)                 # results need a synchronized sweep

sa.measurement.aclr()                          # adjacent-channel power
sa.measurement.set_channel_pairs(2)
sa.measurement.set_channel_spacing(quantity(5, "MHz"))
sa.trigger(wait_for_completion=True)
tx, adj_lower, adj_upper, *_ = sa.measurement.get_power_result("ACLR")

sa.measurement.channel_power()                 # or occupied_bandwidth(), multicarrier_aclr()
sa.measurement.enable_harmonics(); pct, db = sa.measurement.get_thd()
sa.measurement.enable_toi();       toi = sa.measurement.get_toi()
sa.measurement.enable_time_domain_power(rms=True)
sa.measurement.set_mode("SEM")                 # spectrum emission mask (or "SPURIOUS")
```

Covered: channel power, ACLR / multi-carrier ACLR, occupied bandwidth, spectrum
emission mask and spurious (via `set_mode`), time-domain power, harmonic
distortion, third-order intercept, and AM modulation depth.

The analyzer can also switch **measurement application** — the `create_channel` /
`select_channel` / `list_channels` controls wrap the `INSTrument` subsystem — and
the **Noise Figure** application (R&S FSV3-K30) has its own `noise_figure` menu,
verified against the FSV3-K30 User Manual:

```python
sa.create_channel("NOISe", "Noise")            # or sa.noise_figure.create()
sa.noise_figure.set_enr(15.2)                  # constant ENR, in dB
sa.noise_figure.set_start(quantity(10, "MHz"))
sa.noise_figure.set_stop(quantity(3, "GHz"))
sa.noise_figure.set_points(101)
sa.noise_figure.set_second_stage_correction(True)
sa.trigger(wait_for_completion=True)
nf   = sa.noise_figure.get_noise_figure()      # per-point noise figure (dB)
gain = sa.noise_figure.get_gain()              # per-point gain (dB)
```

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

## Vector network analyzers

The VNA driver is the Rohde & Schwarz
[`ZNLE18`][labkit.instruments.drivers.rohde_schwarz.vna.znle18.ZNLE18] (1 MHz –
18 GHz, 2-port). It follows the same menu structure as the analyzers, built from a
shared
[`NetworkAnalyzer`][labkit.instruments.drivers.rohde_schwarz.vna._network_analyzer.NetworkAnalyzer]
base so another ZNL/ZNLE-family model reuses it:

```python
from labkit.units import quantity
from labkit.instruments import ZNLE18

vna = ...  # a ZNLE18 from your TestEnvironment

vna.trace.create("Trc1", "S21")            # define an S21 trace
vna.trace.set_format("MLOG")               # dB-magnitude display
vna.display.set_window_state(1, True)      # create a diagram
vna.display.feed_trace(1, 1, "Trc1")       # show the trace

vna.frequency.set_start(quantity(1, "GHz"))
vna.frequency.set_stop(quantity(18, "GHz"))
vna.sweep.set_points(1001)
vna.bandwidth.set_if_bandwidth(quantity(10, "kHz"))
vna.power.set_power(quantity(-10, "dBm"))
vna.average.set_state(True)
vna.average.set_count(16)

freqs, s21 = vna.measure()                 # single sweep -> (freq array, complex S21)
```

The menus cover far more than the earlier prototype's sweep/trace/display: channel
management, S-parameter trace creation and formatting (dB mag, phase, Smith, …),
stimulus frequency, sweep (type/points/time/count/dwell/trigger), IF bandwidth,
source power and RF output, sweep averaging, markers with peak/min search,
system-error correction and cal-pool load/save, and diagram/display control. Data
comes back three ways — formatted ([`get_formatted_data`][labkit.instruments.drivers.rohde_schwarz.vna.trace.Trace.get_formatted_data]),
raw complex ([`get_complex_data`][labkit.instruments.drivers.rohde_schwarz.vna.trace.Trace.get_complex_data]),
and the stimulus axis ([`get_stimulus`][labkit.instruments.drivers.rohde_schwarz.vna.trace.Trace.get_stimulus]).
Frequency setters are quantity- and range-checked against the model. The failsafe
`_shutdown_procedure` switches the RF source output off when the session ends.

!!! note "Guided calibration"
    The [`calibration`][labkit.instruments.drivers.rohde_schwarz.vna.calibration.Calibration]
    menu *manages* correction: it switches system-error correction on/off, queries
    the calibration state/date, and loads/saves correction data sets from the
    instrument's cal pool. The interactive guided-calibration sequence (measuring
    each standard to compute the error terms) is intentionally left to explicit,
    manual scripting against the cal kit in use.

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
    All command strings are taken from the manufacturers' remote-control manuals:
    the R&S analyzers from the R&S FSVA3000/FSV3000 User Manual (1178.8520.02,
    issue 16) and the FSV3-K30 Noise Figure User Manual (1178.9432.02, issue 13);
    the Aim-TTi TGR6000 from its Instruction Manual (Iss 9); and the R&S ZNLE18
    from the R&S ZNL/ZNLE User Manual (1178.5966.02, issue 23). Validate against
    your firmware version if a command behaves unexpectedly.

## API reference

::: labkit.instruments.environment

::: labkit.instruments.base

::: labkit.instruments.mock

::: labkit.instruments.drivers.rohde_schwarz._spectrum_analyzer

::: labkit.instruments.drivers.rohde_schwarz.fsv3007

::: labkit.instruments.drivers.rohde_schwarz.fpl1003

::: labkit.instruments.drivers.rohde_schwarz.measurement

::: labkit.instruments.drivers.rohde_schwarz.noise_figure

::: labkit.instruments.drivers.aim_tti._signal_generator

::: labkit.instruments.drivers.aim_tti.tgr6000

::: labkit.instruments.drivers.aim_tti.frequency

::: labkit.instruments.drivers.aim_tti.output

::: labkit.instruments.drivers.aim_tti.sweep

::: labkit.instruments.drivers.aim_tti.modulation

::: labkit.instruments.drivers.aim_tti.reference

::: labkit.instruments.drivers.aim_tti.system

::: labkit.instruments.drivers.rohde_schwarz.vna._network_analyzer

::: labkit.instruments.drivers.rohde_schwarz.vna.znle18

::: labkit.instruments.drivers.rohde_schwarz.vna.channel

::: labkit.instruments.drivers.rohde_schwarz.vna.frequency

::: labkit.instruments.drivers.rohde_schwarz.vna.trace

::: labkit.instruments.drivers.rohde_schwarz.vna.sweep

::: labkit.instruments.drivers.rohde_schwarz.vna.bandwidth

::: labkit.instruments.drivers.rohde_schwarz.vna.power

::: labkit.instruments.drivers.rohde_schwarz.vna.average

::: labkit.instruments.drivers.rohde_schwarz.vna.marker

::: labkit.instruments.drivers.rohde_schwarz.vna.calibration

::: labkit.instruments.drivers.rohde_schwarz.vna.display

::: labkit.instruments.registry
