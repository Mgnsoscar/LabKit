"""Auto-generated style literals for editor autocompletion.

These ``Literal`` types make line styles, marker styles, legend locations,
fonts and colours discoverable in an editor: start typing and the valid options
appear.

Line styles, marker styles and legend locations are fixed by matplotlib and are
listed in full. Fonts and colours depend on what is installed on the machine
running matplotlib, so the :data:`FontName` and :data:`ColorName` literals below
are a small curated seed. Regenerate the machine-specific lists with::

    python scripts/generate_style_literals.py

The generator queries matplotlib's font manager and named-colour tables, so the
result reflects the fonts and colours actually available. It writes a committed
file rather than embedding one machine's font list in source, which was a flaw
in the earlier prototype.
"""

from __future__ import annotations

from typing import Literal

__all__ = ["LineStyle", "MarkerStyle", "LegendLoc", "FontName", "ColorName"]

LineStyle = Literal["-", "--", "-.", ":"]

MarkerStyle = Literal[
    ".", ",", "o", "v", "^", "<", ">", "1", "2", "3", "4", "s",
    "p", "*", "h", "H", "+", "x", "D", "d", "|", "_",
]

LegendLoc = Literal[
    "best", "upper left", "upper center", "upper right", "center left",
    "center", "center right", "lower left", "lower center", "lower right",
]

# Curated seed; replaced by scripts/generate_style_literals.py with the fonts
# actually installed.
FontName = Literal[
    "DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono",
    "sans-serif", "serif", "monospace",
]

# Curated seed of matplotlib's base named colours.
ColorName = Literal[
    "black", "white", "red", "green", "blue", "cyan", "magenta", "yellow",
    "orange", "purple", "brown", "pink", "gray", "grey",
    "tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple",
]
