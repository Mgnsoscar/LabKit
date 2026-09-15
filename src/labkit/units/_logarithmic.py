"""Physically-correct arithmetic for logarithmic units (dBm, dBW, dB).

pint parses and converts logarithmic units correctly (``0 dBm`` ↔ ``1 mW``) but
its default arithmetic on them is not physical: ``Quantity(0, "dBm") +
Quantity(3, "dBm")`` yields a nonsensical ``kg**2 m**4 / s**6`` value. This
module makes the operators behave the way an RF engineer expects.

The mechanism is a :class:`~pint.Quantity` subclass installed onto LabKit's
*own* registry by :func:`install_log_arithmetic`. Because a pint registry has
its own Quantity class, this is **not** a global monkey-patch: only quantities
created from LabKit's registry get the behaviour; other pint users in the same
process are unaffected.

Operand kinds
-------------
- **log-power** — a power expressed logarithmically: ``dBm`` (ref 1 mW),
  ``dBW`` (ref 1 W). Has power dimensionality.
- **ratio** — a dimensionless logarithmic ratio: ``dB``. Treated as a *power*
  ratio (``10·log10``), consistent with ``dBm``.
- **linear-power** — ``mW``, ``W``, ... (ordinary power).
- **scalar** — a plain number or a dimensionless non-``dB`` quantity.

Rules (the reverse operand order behaves symmetrically where meaningful):

============================  ==========================  =================================
Operation                     Result                      Meaning
============================  ==========================  =================================
power ``+`` power             log-power                   add powers in the linear domain
power ``+`` ratio             log-power                   apply a gain
ratio ``+`` ratio             ratio                       cascade gains (add in dB)
power ``-`` power             ratio (dB)                  ratio of two power levels
power ``-`` ratio             log-power                   apply a loss
ratio ``-`` ratio             ratio                       difference of gains
============================  ==========================  =================================

Adding a bare number to a level, subtracting a level from a ratio, and **any**
multiplication or division involving a logarithmic operand all raise
:class:`LogArithmeticError` with guidance, rather than silently doing something
surprising. When neither operand is logarithmic, the operation falls through to
pint's normal behaviour unchanged.

Two consequences worth stating plainly:

- **Construct logarithmic quantities with** ``quantity(value, "dBm")``, not
  ``value * unit("dBm")``. The ``n * unit(...)`` idiom relies on multiplication,
  which is undefined for logarithmic units (pint routes ``n * unit`` through
  ``Quantity(1, unit) * n``), so it is not supported for ``dBm``/``dBW``/``dB``.
- **To scale a power or take a raw power ratio, convert to a linear unit
  first**, e.g. ``(p.to("mW") * 2).to("dBm")`` or ``a.to("mW") / b.to("mW")``.

Array reductions
----------------
Reductions over a **log-power array** follow the same physics. Both the numpy
function form (``np.sum(levels)``) and the method form (``levels.sum()``) are
covered:

- ``sum``, ``nansum``, ``cumsum``, ``nancumsum``, ``mean``, ``nanmean``,
  ``average``, ``median``, ``nanmedian`` — reduce in the **linear** domain and
  return the result in the array's own log unit. ``[0, 3, 6] dBm`` sums to
  ``8.44 dBm`` (≈ 7 mW), not ``9 dBm``.
- ``max``, ``min`` and their ``nan``/``arg`` variants are order-preserving, so
  pint's log-domain result is already correct and is left alone.
- ``diff``, ``ptp``, ``std``, ``nanstd`` — differences between levels are
  ratios, so these return **dB**.
- ``prod``, ``cumprod``, ``var`` (and ``nan`` variants) — not physically
  meaningful on logarithmic values; raise :class:`LogArithmeticError`.

A **ratio array** (``dB``) reduces in the dB domain as pint already does
(``sum`` cascades gains, ``mean`` is the average gain); only the rejected
operations above are changed for it.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

__all__ = ["install_log_arithmetic", "LogArithmeticError"]


class LogArithmeticError(TypeError):
    """Raised for an arithmetic operation on logarithmic units that is not
    physically meaningful (or is too ambiguous to guess at)."""


def install_log_arithmetic(registry: Any) -> type:
    """Replace ``registry.Quantity`` with a log-aware subclass and return it.

    Idempotent-ish: call once, right after the registry is created.
    """
    base = registry.Quantity
    power_dim = registry.Quantity(1, "W").dimensionality

    # --- operand classification --------------------------------------------
    SCALAR, RATIO, LOGPOWER, LINPOWER, OTHER = (
        "scalar",
        "ratio",
        "logpower",
        "linpower",
        "other",
    )
    _LOG = (RATIO, LOGPOWER)

    def _is_log_unit(q: Any) -> bool:
        try:
            (name, exp), = q._units.items()
        except (ValueError, AttributeError):
            return False
        if exp != 1:
            return False
        converter = registry._units[name].converter
        return type(converter).__name__ == "LogarithmicConverter"

    def _classify(x: Any) -> str:
        if not isinstance(x, base):
            return SCALAR  # plain number or ndarray
        dimensionless = x.dimensionality == {}
        if _is_log_unit(x):
            if dimensionless:
                return RATIO
            if x.dimensionality == power_dim:
                return LOGPOWER
            return OTHER
        if dimensionless:
            return SCALAR
        if x.dimensionality == power_dim:
            return LINPOWER
        return OTHER

    # --- helpers ------------------------------------------------------------
    def _linear_power(q: Any) -> Any:
        """A power quantity (log or linear) as linear base units (W)."""
        return q.to_base_units()

    def _ratio_factor(q: Any) -> Any:
        """A dB ratio as a linear multiplicative factor (10**(dB/10))."""
        return 10.0 ** (q.magnitude / 10.0)

    def _preferred_log_unit(*operands: Any) -> Any:
        """Pick the output log unit: an existing log-power unit, else dBm."""
        for op in operands:
            if _classify(op) == LOGPOWER:
                return op.units
        return "dBm"

    def _make(value: Any, unit: Any) -> Any:
        return registry.Quantity(value, unit)

    def _both_power(a_kind: str, b_kind: str) -> bool:
        return a_kind in (LOGPOWER, LINPOWER) and b_kind in (LOGPOWER, LINPOWER)

    # --- the arithmetic -----------------------------------------------------
    def _add(a: Any, b: Any, ak: str, bk: str) -> Any:
        if ak == RATIO and bk == RATIO:
            return _make(a.magnitude + b.magnitude, "dB")
        if _both_power(ak, bk):
            total = _linear_power(a) + _linear_power(b)
            return total.to(_preferred_log_unit(a, b))
        # exactly one ratio, one power -> apply gain
        if ak == RATIO and bk in (LOGPOWER, LINPOWER):
            ratio, power = a, b
        elif bk == RATIO and ak in (LOGPOWER, LINPOWER):
            ratio, power = b, a
        else:
            _reject("add", ak, bk)
        scaled = _linear_power(power) * _ratio_factor(ratio)
        return scaled.to(_preferred_log_unit(power))

    def _sub(a: Any, b: Any, ak: str, bk: str) -> Any:
        if ak == RATIO and bk == RATIO:
            return _make(a.magnitude - b.magnitude, "dB")
        if _both_power(ak, bk):
            ratio = (_linear_power(a) / _linear_power(b)).to("dimensionless").magnitude
            return _make(10.0 * np.log10(ratio), "dB")
        if ak in (LOGPOWER, LINPOWER) and bk == RATIO:  # apply a loss
            scaled = _linear_power(a) / _ratio_factor(b)
            return scaled.to(_preferred_log_unit(a))
        _reject("subtract", ak, bk)

    def _reject(op: str, ak: str, bk: str) -> Any:
        raise LogArithmeticError(
            f"Cannot {op} operands of kind '{ak}' and '{bk}'. This is not a "
            "physically meaningful operation on logarithmic units; convert to a "
            "linear unit (e.g. `.to('mW')`) first if that is what you intend."
        )

    def _reject_muldiv(op: str) -> Any:
        raise LogArithmeticError(
            f"Cannot {op} a logarithmic quantity (dBm, dBW, dB). "
            "To create one use quantity(value, 'dBm'); to scale a power or take "
            "a raw ratio, convert to a linear unit first, e.g. "
            "`(p.to('mW') * 2).to('dBm')` or `a.to('mW') / b.to('mW')`."
        )

    # --- array reductions ---------------------------------------------------
    # Reductions that combine levels: done in the linear domain, result in the
    # array's own log unit. (max/min are order-preserving and need no change.)
    _linear_reductions = {
        np.sum, np.nansum, np.cumsum, np.nancumsum,
        np.mean, np.nanmean, np.average, np.median, np.nanmedian,
    }
    # Reductions that express differences between levels: those are ratios, so
    # they are computed on the dB magnitudes and returned in dB.
    _db_reductions = {np.diff, np.ptp, np.std, np.nanstd}
    # Reductions with no physical meaning on logarithmic values.
    _rejected_reductions = {
        np.prod, np.nanprod, np.cumprod, np.nancumprod, np.var, np.nanvar,
    }

    def _linearize(x: Any) -> Any:
        """A log-power quantity as linear base units; anything else unchanged."""
        return _linear_power(x) if _classify(x) == LOGPOWER else x

    def _relog(result: Any, unit: Any) -> Any:
        """Express a linear-power result (or tuple of them) back in `unit`."""
        if isinstance(result, tuple):
            return tuple(_relog(r, unit) for r in result)
        if isinstance(result, base) and result.dimensionality == power_dim:
            return result.to(unit)
        return result

    def _reduce_log(self: Any, func: Any, args: tuple, kwargs: dict) -> Any:
        """Apply `func` (a numpy reduction) to a logarithmic array per the rules above."""
        kind = _classify(self)
        if func in _rejected_reductions:
            raise LogArithmeticError(
                f"numpy.{func.__name__} is not physically meaningful on a "
                "logarithmic quantity (dBm, dBW, dB). Convert to a linear unit "
                "first (e.g. `.to('mW')`) if that is what you intend."
            )
        if func in _db_reductions:
            magnitudes = tuple(a.magnitude if isinstance(a, base) else a for a in args)
            return _make(func(*magnitudes, **kwargs), "dB")
        if func in _linear_reductions and kind == LOGPOWER:
            linear_args = tuple(_linearize(a) for a in args)
            linear_kwargs = {k: _linearize(v) for k, v in kwargs.items()}
            return _relog(func(*linear_args, **linear_kwargs), self.units)
        return NotImplemented

    def _method(name: str, func: Any) -> Callable[..., Any]:
        """Build the method form of a reduction (``q.sum()`` alongside ``np.sum(q)``).

        Logarithmic quantities go through the numpy function so the rules above
        apply; everything else keeps pint's own method behaviour.
        """

        def method(self: Any, *args: Any, **kwargs: Any) -> Any:
            if _classify(self) in _LOG:
                return func(self, *args, **kwargs)
            return base.__getattr__(self, name)(*args, **kwargs)

        method.__name__ = name
        method.__doc__ = f"``numpy.{name}`` of the quantity; see :mod:`labkit.units._logarithmic`."
        return method

    class LogAwareQuantity(base):  # type: ignore[valid-type, misc]
        """A pint quantity with physically-correct logarithmic-unit arithmetic.

        See :mod:`labkit.units._logarithmic` for the full rules.
        """

        __slots__ = ()

        def __array_function__(self, func: Any, types: Any, args: Any, kwargs: Any) -> Any:
            if _classify(self) in _LOG:
                result = _reduce_log(self, func, args, kwargs)
                if result is not NotImplemented:
                    return result
            return base.__array_function__(self, func, types, args, kwargs)

        sum = _method("sum", np.sum)
        mean = _method("mean", np.mean)
        cumsum = _method("cumsum", np.cumsum)
        std = _method("std", np.std)
        var = _method("var", np.var)
        ptp = _method("ptp", np.ptp)
        cumprod = _method("cumprod", np.cumprod)

        def __add__(self, other: Any) -> Any:
            ak, bk = _classify(self), _classify(other)
            if ak not in _LOG and bk not in _LOG:
                return base.__add__(self, other)
            return _add(self, other, ak, bk)

        def __radd__(self, other: Any) -> Any:
            return self.__add__(other)

        def __sub__(self, other: Any) -> Any:
            ak, bk = _classify(self), _classify(other)
            if ak not in _LOG and bk not in _LOG:
                return base.__sub__(self, other)
            return _sub(self, other, ak, bk)

        def __rsub__(self, other: Any) -> Any:
            ak, bk = _classify(other), _classify(self)
            if ak not in _LOG and bk not in _LOG:
                return base.__rsub__(self, other)
            return _sub(other, self, ak, bk)

        def __mul__(self, other: Any) -> Any:
            ak, bk = _classify(self), _classify(other)
            if ak not in _LOG and bk not in _LOG:
                return base.__mul__(self, other)
            return _reject_muldiv("multiply")

        def __rmul__(self, other: Any) -> Any:
            ak, bk = _classify(self), _classify(other)
            if ak not in _LOG and bk not in _LOG:
                return base.__rmul__(self, other)
            return _reject_muldiv("multiply")

        def __truediv__(self, other: Any) -> Any:
            ak, bk = _classify(self), _classify(other)
            if ak not in _LOG and bk not in _LOG:
                return base.__truediv__(self, other)
            return _reject_muldiv("divide")

        def __rtruediv__(self, other: Any) -> Any:
            ak, bk = _classify(self), _classify(other)
            if ak not in _LOG and bk not in _LOG:
                return base.__rtruediv__(self, other)
            return _reject_muldiv("divide")

    registry.Quantity = LogAwareQuantity
    return LogAwareQuantity
