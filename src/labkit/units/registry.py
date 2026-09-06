"""The shared `pint` unit registry.

LabKit uses a single, process-wide :class:`pint.UnitRegistry`. Every quantity
must come from the same registry — quantities created by *different* registries
cannot be compared or combined — so this module builds exactly one and exposes
it as :data:`ureg`.

Why pint (and not astropy)?
---------------------------
The earlier prototype built on ``astropy.units`` and monkey-patched astropy's
internals so that logarithmic units (``dBm``, ``dB``) would add, subtract and
scale the way an RF engineer expects. pint gives us the same unit coverage with
a cleaner, officially-supported extension model and better static typing.

Note that pint recognises ``dBm``/``dB`` and converts them correctly
(``0 dBm`` ↔ ``1 mW``) but does **not** add them physically out of the box:
``Quantity(0, "dBm") + Quantity(3, "dBm")`` yields a nonsensical result. The
correct linear-domain arithmetic is LabKit's own contribution and is layered on
top of this registry in :mod:`labkit.units.quantity`.
"""

from __future__ import annotations

import pint

__all__ = ["ureg", "make_registry"]


def make_registry() -> pint.UnitRegistry:
    """Construct and configure a fresh LabKit unit registry.

    Exposed mainly for tests that need an isolated registry; application code
    should import the shared :data:`ureg` instead.
    """
    registry: pint.UnitRegistry = pint.UnitRegistry(
        # Keep offset units (e.g. degC) as-is rather than silently converting
        # them to base units; conversions must be explicit.
        autoconvert_offset_to_baseunit=False,
    )
    # Make this the registry that pint hands out for unpickling and for any
    # library that asks for "the" application registry.
    pint.set_application_registry(registry)  # type: ignore[no-untyped-call]
    return registry


#: The shared registry used throughout LabKit.
ureg: pint.UnitRegistry = make_registry()
