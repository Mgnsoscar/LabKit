"""The R&S FPL1003 driver.

Because the FPL1003 and FSV3007 share one implementation, these tests
parametrize over both to show they behave identically — that shared behaviour is
the point of the menu/base structure.
"""

from __future__ import annotations

import numpy as np
import pytest

from labkit.instruments import FPL1003, FSV3007, mock_instrument
from labkit.instruments.drivers.rohde_schwarz import SpectrumAnalyzer
from labkit.units import quantity as Q

ANALYZERS = [FSV3007, FPL1003]


@pytest.mark.parametrize("cls", ANALYZERS)
def test_is_spectrum_analyzer(cls: type) -> None:
    assert issubclass(cls, SpectrumAnalyzer)


def test_fpl_and_fsv_are_sibling_classes() -> None:
    # Independent models sharing a base, not one extending the other.
    assert not issubclass(FPL1003, FSV3007)
    assert not issubclass(FSV3007, FPL1003)


@pytest.mark.parametrize("cls", ANALYZERS)
def test_shared_scpi_is_identical(cls: type) -> None:
    sa, be = mock_instrument(cls, responses={"*IDN?": "R&S,model,1,2"})
    sa.frequency.set_center(Q(1, "GHz"))
    sa.bandwidth.set_rbw(Q(100, "kHz"))
    sa.sweep.set_points(1001)
    sa.amplitude.set_ref_level(Q(-10, "dBm"))
    assert be.writes == [
        "FREQ:CENT 1000000000.0",
        "BAND 100000.0",
        "SWE:POIN 1001",
        "DISP:TRAC:Y:SCAL:RLEV -10.0",
    ]


@pytest.mark.parametrize("cls", ANALYZERS)
def test_address_and_shutdown(cls: type) -> None:
    sa, be = mock_instrument(cls)
    assert sa._address == "TCPIP::0.0.0.0::INSTR"
    sa.close()
    assert "INIT:CONT ON" in be.writes


@pytest.mark.parametrize("cls", ANALYZERS)
def test_measure_trace_roundtrip(cls: type) -> None:
    sa, be = mock_instrument(cls)
    be.on("*OPC?", "1")
    be.on("FREQ:STAR?", "9.9e8").on("FREQ:STOP?", "1.01e9").on("SWE:POIN?", "3")
    be.on("TRAC:DATA? TRACE1", "-50.0,-30.0,-55.0")
    x, y = sa.measure_trace()
    np.testing.assert_allclose(x.to("MHz").magnitude, [990.0, 1000.0, 1010.0])
    np.testing.assert_allclose(y.magnitude, [-50.0, -30.0, -55.0])
