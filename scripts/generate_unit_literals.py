"""Generate ``src/labkit/units/_literals.py``.

Builds the :data:`UnitName` literal from LabKit's `pint` registry so the list of
autocompletion suggestions always matches the units the library can parse. The
list is scoped to the unit categories relevant to lab work (frequency, power,
time, electrical, angle, ratio) rather than every unit pint ships.

Every generated name is validated by round-tripping it through the registry, so
the emitted literal cannot contain a name pint would reject.

Run from the repository root::

    python scripts/generate_unit_literals.py
"""

from __future__ import annotations

import pathlib

import pint

OUTPUT = pathlib.Path(__file__).resolve().parent.parent / "src" / "labkit" / "units" / "_literals.py"

# Metric prefixes we care about for lab work (symbol forms).
_PREFIXES = ["", "n", "u", "m", "k", "M", "G", "T"]

# Base unit symbols grouped by category. Prefixes are applied to these.
_PREFIXABLE = {
    "Frequency": ["Hz"],
    "Power (linear)": ["W"],
    "Time": ["s"],
    "Electrical": ["V", "A", "ohm"],
}

# Names included verbatim (no prefixing): long names, logarithmic units, angles,
# ratios, and a few durations that have their own names.
_VERBATIM = {
    "Frequency": ["hertz"],
    "Power (linear)": ["watt"],
    "Power (logarithmic)": ["dBm", "dBW", "dB", "decibel"],
    "Time": ["second", "min", "minute", "hour", "day"],
    "Electrical": ["volt", "ampere", "ohm"],
    "Angle": ["deg", "degree", "rad", "radian"],
    "Ratio": ["percent", "dimensionless"],
}


def _validated_names(registry: pint.UnitRegistry) -> dict[str, list[str]]:
    """Return {category: [names]} keeping only names the registry accepts."""
    categories: dict[str, list[str]] = {}

    def keep(name: str) -> bool:
        try:
            registry.Unit(name)
            return True
        except Exception:
            return False

    for category, symbols in _PREFIXABLE.items():
        names = [f"{p}{s}" for s in symbols for p in _PREFIXES]
        categories.setdefault(category, []).extend(n for n in names if keep(n))

    for category, names in _VERBATIM.items():
        categories.setdefault(category, []).extend(n for n in names if keep(n))

    # De-duplicate within each category, preserving order.
    for category, names in categories.items():
        seen: set[str] = set()
        categories[category] = [n for n in names if not (n in seen or seen.add(n))]
    return categories


def render(categories: dict[str, list[str]]) -> str:
    lines = [
        '"""Auto-generated unit-name literals for editor autocompletion.',
        "",
        "The :data:`UnitName` literal lets editors suggest every known unit name",
        'when you type ``Unit("...")``.',
        "",
        "This file is GENERATED. Do not edit by hand. Regenerate it with::",
        "",
        "    python scripts/generate_unit_literals.py",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Literal",
        "",
        '__all__ = ["UnitName"]',
        "",
        "UnitName = Literal[",
    ]
    for category, names in categories.items():
        if not names:
            continue
        lines.append(f"    # {category}")
        lines.append("    " + ", ".join(f'"{n}"' for n in names) + ",")
    lines.append("]")
    lines.append('"""Every unit name LabKit understands, as a ``Literal`` for autocompletion."""')
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    registry = pint.UnitRegistry()
    categories = _validated_names(registry)
    OUTPUT.write_text(render(categories), encoding="utf-8")
    total = sum(len(v) for v in categories.values())
    print(f"Wrote {total} unit names to {OUTPUT}")


if __name__ == "__main__":
    main()
