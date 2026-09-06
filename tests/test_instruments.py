"""Instruments: dummy-mode driver behaviour and failsafe shutdown."""

from __future__ import annotations

from labkit.instruments import BaseInstrument, DummyBackend, TestEnvironment
from labkit.instruments import registry


class _Analyzer(BaseInstrument):
    def _build_address(self, address: str) -> str:
        return f"TCPIP::{address}::INSTR"


class _Bench(TestEnvironment):
    analyzer: _Analyzer

    def _configure_instruments(self) -> None:
        self.analyzer = _Analyzer(self, "Analyzer", "192.168.0.10")


def test_dummy_mode_builds_address_and_records_scpi() -> None:
    bench = _Bench(use_dummy_instruments=True)
    assert bench.resource_manager is None
    assert bench.analyzer._address == "TCPIP::192.168.0.10::INSTR"

    bench.analyzer.reset_instrument()
    backend = bench.analyzer._backend
    assert isinstance(backend, DummyBackend)
    assert "WRITE: *RST" in backend.log
    assert "WRITE: *CLS" in backend.log


def test_close_is_idempotent_and_unregisters() -> None:
    bench = _Bench(use_dummy_instruments=True)
    instrument = bench.analyzer
    assert instrument in registry._instruments

    instrument.close()
    instrument.close()  # second call is a no-op, must not raise
    assert instrument not in registry._instruments


def test_shutdown_closes_all_registered_instruments() -> None:
    bench = _Bench(use_dummy_instruments=True)
    instrument = bench.analyzer

    registry.shutdown()
    assert instrument._closed
    assert instrument not in registry._instruments
