"""Data output helpers for LabKit.

Currently this package holds the declarative CSV writer. It mirrors the
plotting API: describe the columns you want and hand them to :func:`write`.
"""

from __future__ import annotations

from .csv import Column, Value, write

__all__ = ["Column", "Value", "write"]
