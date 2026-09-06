"""Assorted helpers: folders, timestamps, directory scanning.

The pure, low-risk helpers are implemented; a couple of others are stubbed and
noted as such. Everything here is dependency-free.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

__all__ = [
    "make_folder",
    "get_date_as_string",
    "get_timestamp_for_file",
    "scan_directory",
]


def make_folder(parent_folder: str, folder_name: str) -> str:
    """Create ``parent_folder/folder_name`` if needed and return its path.

    Existing folders are left untouched. Rejects empty, absolute, or
    path-traversing names so a folder cannot be created outside `parent_folder`.

    Raises
    ------
    ValueError
        If `folder_name` is empty, absolute, or contains ``..`` traversal.
    """
    if not folder_name:
        raise ValueError("folder_name must not be empty.")
    if os.path.isabs(folder_name):
        raise ValueError(f"folder_name must be relative, got '{folder_name}'.")

    path = os.path.normpath(os.path.join(parent_folder, folder_name))
    parent = os.path.normpath(parent_folder)
    if os.path.commonpath([parent, path]) != parent:
        raise ValueError(f"folder_name must not escape the parent folder: '{folder_name}'.")

    os.makedirs(path, exist_ok=True)
    return path


def get_date_as_string(when: Optional[datetime] = None) -> str:
    """Return a human-readable date string, e.g. ``"06.09.2026 - Sunday"``."""
    when = when or datetime.now()
    return when.strftime("%d.%m.%Y - %A")


def get_timestamp_for_file(
    date: bool = True,
    time: bool = True,
    seconds: bool = False,
    when: Optional[datetime] = None,
) -> str:
    """Return a filename-safe timestamp.

    Examples: ``"dmy_06_09_26_hm_19_36"``, ``"hms_19_36_12"``.

    Parameters
    ----------
    date, time:
        Include the date and/or time-of-day components.
    seconds:
        Include seconds in the time component.
    when:
        The moment to format; defaults to now (mainly for testing).
    """
    when = when or datetime.now()
    parts: list[str] = []
    if date:
        parts.append(when.strftime("dmy_%d_%m_%y"))
    if time:
        parts.append(when.strftime("hms_%H_%M_%S" if seconds else "hm_%H_%M"))
    return "_".join(parts)


def scan_directory(
    directory: str,
    suffixes: Optional[str | list[str]] = None,
    include: bool = True,
) -> list[tuple[str, str]]:
    """Recursively list files under `directory`.

    Returns ``(full_path, filename)`` tuples. If `suffixes` is given, keep only
    files with those suffixes when `include` is ``True``, or exclude them when
    ``False``.
    """
    if isinstance(suffixes, str):
        suffixes = [suffixes]
    normalized = (
        tuple(s.lower().lstrip(".") for s in suffixes) if suffixes is not None else None
    )

    results: list[tuple[str, str]] = []
    for root, _dirs, files in os.walk(directory):
        for name in files:
            if normalized is not None:
                matches = name.lower().rsplit(".", 1)[-1] in normalized
                if matches != include:
                    continue
            results.append((os.path.join(root, name), name))
    return results
