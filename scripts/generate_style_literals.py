"""Generate ``src/labkit/plotting/_literals.py``.

Fills the :data:`FontName` and :data:`ColorName` literals from what matplotlib
reports as available on this machine, and writes the fixed line-style, marker
and legend-location literals. Unlike the earlier prototype, the font list is
produced by a committed script rather than hand-pasted from one machine.

Requires the plotting extra (``pip install "labkit[plotting]"``). Run from the
repository root::

    python scripts/generate_style_literals.py
"""

from __future__ import annotations

import pathlib

OUTPUT = (
    pathlib.Path(__file__).resolve().parent.parent
    / "src"
    / "labkit"
    / "plotting"
    / "_literals.py"
)


def _fonts() -> list[str]:
    from matplotlib import font_manager

    names = sorted({f.name for f in font_manager.fontManager.ttflist})
    # Always offer the generic families too.
    return ["sans-serif", "serif", "monospace", *names]


def _colors() -> list[str]:
    import matplotlib.colors as mcolors

    base = list(mcolors.BASE_COLORS)
    tab = [c for c in mcolors.TABLEAU_COLORS]
    css = sorted(mcolors.CSS4_COLORS)
    # De-duplicate, preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for name in [*base, *tab, *css]:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def render(fonts: list[str], colors: list[str]) -> str:
    def literal(name: str, values: list[str]) -> str:
        body = ", ".join(f'"{v}"' for v in values)
        return f"{name} = Literal[{body}]"

    return "\n".join(
        [
            '"""Auto-generated style literals for editor autocompletion.',
            "",
            "This file is GENERATED. Do not edit by hand. Regenerate it with::",
            "",
            "    python scripts/generate_style_literals.py",
            '"""',
            "",
            "from __future__ import annotations",
            "",
            "from typing import Literal",
            "",
            '__all__ = ["LineStyle", "MarkerStyle", "LegendLoc", "FontName", "ColorName"]',
            "",
            'LineStyle = Literal["-", "--", "-.", ":"]',
            "",
            "MarkerStyle = Literal["
            '".", ",", "o", "v", "^", "<", ">", "1", "2", "3", "4", "s", '
            '"p", "*", "h", "H", "+", "x", "D", "d", "|", "_"]',
            "",
            "LegendLoc = Literal["
            '"best", "upper left", "upper center", "upper right", "center left", '
            '"center", "center right", "lower left", "lower center", "lower right"]',
            "",
            literal("FontName", fonts),
            "",
            literal("ColorName", colors),
            "",
        ]
    )


def main() -> None:
    OUTPUT.write_text(render(_fonts(), _colors()), encoding="utf-8")
    print(f"Wrote font/colour literals to {OUTPUT}")


if __name__ == "__main__":
    main()
