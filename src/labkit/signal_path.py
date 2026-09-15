"""Signal paths: the cables, attenuators and couplers between an instrument and a DUT.

A measurement is taken at the instrument's connector, but the number you want
is the level at the device under test. Everything in between — the input path
from a generator to the DUT input, the output path from the DUT output to an
analyzer — has a loss that depends on frequency. This module models that chain
so a raw measurement can be moved to the DUT reference plane, now or long after
the fact.

- :class:`LossTable` — a frequency-dependent loss measured on a VNA, loaded
  from a CSV, **interpolated** (linearly, in dB) to any frequency asked for.
  Measurements are rarely taken at exactly the frequencies a component was
  characterized at, so interpolation is the normal case, not the exception.
- :class:`Component` — one physical part with a name, a loss (a flat dB value or
  a :class:`LossTable`) and the date it was characterized, so a result can
  record exactly which characterization it was corrected with.
- :class:`SignalPath` — an ordered chain of components ending at a DUT port,
  with the total loss and the two reference-plane moves a measurement needs:
  :meth:`SignalPath.after` (the level that arrives at the far end) and
  :meth:`SignalPath.before` (the level that must have entered the near end).

Example
-------
::

    cable = Component("SMA cable A", LossTable.from_csv("cable_a.csv"), date(2026, 9, 1))
    pad = Component("10 dB pad SN1234", quantity(10.2, "dB"), date(2026, 8, 20))
    input_path = SignalPath(cable, pad)            # generator -> cable -> pad -> DUT in

    p_gen = quantity(-10, "dBm")
    p_at_dut = input_path.after(p_gen, quantity(2.3, "GHz"))    # -10 dBm minus the losses

    output_path = SignalPath(coupler, cable_b)    # DUT out -> coupler -> cable -> analyzer
    p_dut_out = output_path.before(p_measured, freqs)          # measured plus the losses
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterator, Optional, Union, cast

import numpy as np

from .io.csv import read as _read_csv
from .units import Quantity, ensure_frequency, is_dimensionless_decibel, is_frequency, quantity

__all__ = ["LossTable", "Component", "SignalPath", "Loss"]


def _ensure_db(loss: object, what: str) -> Quantity:
    """Return `loss` if it is a dB ratio quantity, else raise ``TypeError``."""
    if not is_dimensionless_decibel(loss):
        got = getattr(loss, "units", type(loss).__name__)
        raise TypeError(f"{what} must be a dB quantity, e.g. quantity(3, 'dB'). Got '{got}'.")
    return loss  # type: ignore[return-value]


class LossTable:
    """A frequency-dependent loss, interpolated between characterized points.

    Parameters
    ----------
    frequencies:
        A frequency quantity array (any unit). Need not be sorted.
    losses:
        The loss at each frequency as a ``dB`` quantity array (positive = loss).

    Interpolation is **linear in dB** between neighbouring points, which is
    the usual model for cable and attenuator loss over a modest span. Asking
    for a frequency outside the characterized range raises
    :class:`ValueError` unless `extrapolate` is ``True``, in which case the
    nearest end value is used — silently extending a characterization is a
    classic source of error, so it is opt-in.
    """

    def __init__(self, frequencies: Quantity, losses: Quantity) -> None:
        f_hz = np.atleast_1d(np.asarray(ensure_frequency(frequencies).to("Hz").magnitude, dtype=float))
        l_db = np.atleast_1d(np.asarray(_ensure_db(losses, "losses").magnitude, dtype=float))
        if f_hz.ndim != 1 or l_db.ndim != 1 or f_hz.shape != l_db.shape:
            raise ValueError(
                f"frequencies and losses must be 1-D and the same length, got shapes "
                f"{f_hz.shape} and {l_db.shape}."
            )
        if f_hz.size == 0:
            raise ValueError("A LossTable needs at least one point.")
        order = np.argsort(f_hz)
        self._f_hz = f_hz[order]
        self._l_db = l_db[order]

    # -- construction --------------------------------------------------------
    @classmethod
    def from_csv(
        cls,
        path: str,
        frequency_column: Optional[str] = None,
        loss_column: Optional[str] = None,
    ) -> "LossTable":
        """Load a table written by :func:`labkit.io.csv.write`.

        By default the first frequency column and the first ``dB`` column are
        used; name them explicitly (by their label, without the unit suffix)
        when the file has several.
        """
        table = _read_csv(path)
        f = table.column(frequency_column) if frequency_column else table.first_column(is_frequency)
        loss = table.column(loss_column) if loss_column else table.first_column(is_dimensionless_decibel)
        return cls(f, loss)

    # -- lookup --------------------------------------------------------------
    def loss_at(self, frequency: Quantity, extrapolate: bool = False) -> Quantity:
        """The loss at `frequency` (scalar or array) as a ``dB`` quantity."""
        f_hz = np.asarray(ensure_frequency(frequency).to("Hz").magnitude, dtype=float)
        lo, hi = self._f_hz[0], self._f_hz[-1]
        if not extrapolate and (np.any(f_hz < lo) or np.any(f_hz > hi)):
            raise ValueError(
                f"Frequency outside the characterized range "
                f"{quantity(lo, 'Hz').to('MHz'):~.6g} – {quantity(hi, 'Hz').to('MHz'):~.6g}; "
                "pass extrapolate=True to clamp to the end values."
            )
        interpolated = np.interp(f_hz, self._f_hz, self._l_db)
        if f_hz.ndim == 0:
            return quantity(float(interpolated), "dB")
        return quantity(interpolated, "dB")

    # -- introspection -------------------------------------------------------
    @property
    def frequencies(self) -> Quantity:
        """The characterized frequencies, ascending, in Hz."""
        return quantity(self._f_hz.copy(), "Hz")

    @property
    def losses(self) -> Quantity:
        """The characterized losses, in the order of :attr:`frequencies`, in dB."""
        return quantity(self._l_db.copy(), "dB")

    @property
    def frequency_range(self) -> tuple[Quantity, Quantity]:
        """The ``(lowest, highest)`` characterized frequency."""
        return quantity(self._f_hz[0], "Hz"), quantity(self._f_hz[-1], "Hz")

    def __len__(self) -> int:
        return int(self._f_hz.size)

    def __repr__(self) -> str:
        lo, hi = self.frequency_range
        return f"LossTable({len(self)} points, {lo.to('MHz'):~.6g} – {hi.to('MHz'):~.6g})"


#: What a component's loss may be: a flat dB quantity or a frequency table.
Loss = Union[Quantity, LossTable]


@dataclass(frozen=True)
class Component:
    """One physical part of a signal path, with its characterized loss.

    Parameters
    ----------
    name:
        A human-readable identity, ideally including a serial number.
    loss:
        Either a flat ``dB`` quantity or a :class:`LossTable`.
    characterized:
        The date the loss was measured. Recorded alongside results so a
        measurement can later be traced to the characterization it used.
    """

    name: str
    loss: Loss
    characterized: Optional[date] = None

    def __post_init__(self) -> None:
        if not isinstance(self.loss, LossTable):
            _ensure_db(self.loss, f"Component '{self.name}' loss")

    def loss_at(self, frequency: Quantity, extrapolate: bool = False) -> Quantity:
        """The loss at `frequency` as a ``dB`` quantity (broadcast for a flat loss)."""
        if isinstance(self.loss, LossTable):
            return self.loss.loss_at(frequency, extrapolate=extrapolate)
        f = np.asarray(ensure_frequency(frequency).magnitude, dtype=float)
        flat = float(self.loss.magnitude)
        if f.ndim == 0:
            return quantity(flat, "dB")
        return quantity(np.full(f.shape, flat), "dB")

    def describe(self) -> str:
        """``"SMA cable A (2026-09-01)"`` — the name plus the characterization date."""
        if self.characterized is None:
            return self.name
        return f"{self.name} ({self.characterized.isoformat()})"


class SignalPath:
    """An ordered chain of :class:`Component` objects between an instrument and a DUT port.

    ``SignalPath()`` with no components is a direct connection with zero loss.
    Levels passed to :meth:`after` and :meth:`before` may be ``dBm``/``dBW`` or
    linear power quantities, scalar or array; the loss is evaluated at the
    matching frequency (scalar, or one per element).
    """

    def __init__(self, *components: Component) -> None:
        for c in components:
            if not isinstance(c, Component):
                raise TypeError(f"SignalPath takes Component objects, got {type(c).__name__}.")
        self._components: tuple[Component, ...] = tuple(components)

    @property
    def components(self) -> tuple[Component, ...]:
        return self._components

    def __iter__(self) -> Iterator[Component]:
        return iter(self._components)

    def __len__(self) -> int:
        return len(self._components)

    def __add__(self, other: "SignalPath") -> "SignalPath":
        """Concatenate two paths (``generator_side + dut_side``)."""
        return SignalPath(*self._components, *other._components)

    def __repr__(self) -> str:
        return f"SignalPath({self.describe()})"

    # -- loss ----------------------------------------------------------------
    def loss_at(self, frequency: Quantity, extrapolate: bool = False) -> Quantity:
        """Total loss at `frequency`: the sum of every component's loss, in dB."""
        f = np.asarray(ensure_frequency(frequency).magnitude, dtype=float)
        total = np.zeros(f.shape, dtype=float)
        for c in self._components:
            total = total + np.asarray(c.loss_at(frequency, extrapolate=extrapolate).magnitude)
        if f.ndim == 0:
            return quantity(float(total), "dB")
        return quantity(total, "dB")

    def after(self, level: Quantity, frequency: Quantity, extrapolate: bool = False) -> Quantity:
        """The level that comes **out** of the path when `level` goes in.

        For an input path this is the level at the DUT input given the level
        set on the generator: ``level - loss``.
        """
        return cast(Quantity, level - self.loss_at(frequency, extrapolate=extrapolate))

    def before(self, level: Quantity, frequency: Quantity, extrapolate: bool = False) -> Quantity:
        """The level that must have gone **in** to the path for `level` to come out.

        For an output path this is the level at the DUT output given the level
        the analyzer measured: ``level + loss``.
        """
        return cast(Quantity, level + self.loss_at(frequency, extrapolate=extrapolate))

    # -- description ---------------------------------------------------------
    def describe(self) -> str:
        """``"SMA cable A (2026-09-01), 10 dB pad SN1234 (2026-08-20)"``, or ``"direct"``."""
        if not self._components:
            return "direct"
        return ", ".join(c.describe() for c in self._components)
