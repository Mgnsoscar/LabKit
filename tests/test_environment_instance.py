"""TestEnvironment.instance(): one shared bench, built once."""

from __future__ import annotations

from labkit.instruments import BaseInstrument, TestEnvironment, registry


class _Gen(BaseInstrument):
    def _build_address(self, address: str) -> str:
        return f"TCPIP::{address}::INSTR"


class _Bench(TestEnvironment):
    built = 0
    gen: _Gen

    def _configure_instruments(self) -> None:
        type(self).built += 1
        self.gen = _Gen(self, "Generator", "192.168.0.20")


class _OtherBench(_Bench):
    pass


def setup_function() -> None:
    _Bench.discard_instance(use_dummy_instruments=True)
    _OtherBench.discard_instance(use_dummy_instruments=True)
    _Bench.built = 0
    _OtherBench.built = 0


def test_instance_is_built_once_and_shared() -> None:
    a = _Bench.instance(use_dummy_instruments=True)
    b = _Bench.instance(use_dummy_instruments=True)
    assert a is b
    assert a.gen is b.gen  # the same connected instrument, no reconnect
    assert _Bench.built == 1


def test_instances_are_keyed_by_class_and_arguments() -> None:
    a = _Bench.instance(use_dummy_instruments=True)
    other = _OtherBench.instance(use_dummy_instruments=True)
    assert a is not other
    assert isinstance(other, _OtherBench)


def test_discard_closes_and_rebuilds() -> None:
    a = _Bench.instance(use_dummy_instruments=True)
    gen = a.gen
    assert gen in registry._instruments
    _Bench.discard_instance(use_dummy_instruments=True)
    assert gen._closed
    assert gen not in registry._instruments
    b = _Bench.instance(use_dummy_instruments=True)
    assert b is not a
    assert _Bench.built == 2


def test_close_closes_every_instrument() -> None:
    bench = _Bench(use_dummy_instruments=True)
    assert bench.instruments == [bench.gen]
    bench.close()
    assert bench.gen._closed
