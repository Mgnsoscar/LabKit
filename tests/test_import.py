"""The package imports cleanly and exposes its public API."""

from __future__ import annotations

import importlib


def test_top_level_import() -> None:
    import labkit

    assert labkit.__version__
    assert hasattr(labkit, "quantity")
    assert hasattr(labkit, "ureg")


def test_subpackages_import_without_optional_deps() -> None:
    # These must import even when matplotlib / pyvisa are absent, because their
    # heavy dependencies are only imported lazily when used.
    for name in (
        "labkit.units",
        "labkit.plotting",
        "labkit.io",
        "labkit.instruments",
        "labkit.utils",
    ):
        assert importlib.import_module(name) is not None
