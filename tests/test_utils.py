"""Utility helpers: folders, timestamps, directory scanning."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from labkit.utils import get_timestamp_for_file, make_folder, scan_directory


def test_make_folder_creates_and_is_idempotent(tmp_path: Path) -> None:
    first = make_folder(str(tmp_path), "results")
    second = make_folder(str(tmp_path), "results")
    assert first == second
    assert os.path.isdir(first)


def test_make_folder_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        make_folder(str(tmp_path), "../escape")
    with pytest.raises(ValueError):
        make_folder(str(tmp_path), "")


def test_timestamp_formatting() -> None:
    when = datetime(2026, 9, 6, 19, 36, 12)
    assert get_timestamp_for_file(when=when) == "dmy_06_09_26_hm_19_36"
    assert get_timestamp_for_file(seconds=True, when=when) == "dmy_06_09_26_hms_19_36_12"
    assert get_timestamp_for_file(date=False, seconds=True, when=when) == "hms_19_36_12"


def test_scan_directory_filters_by_suffix(tmp_path: Path) -> None:
    (tmp_path / "a.csv").write_text("x")
    (tmp_path / "b.png").write_text("x")
    (tmp_path / "c.csv").write_text("x")

    csvs = scan_directory(str(tmp_path), suffixes="csv")
    assert {name for _path, name in csvs} == {"a.csv", "c.csv"}

    not_csv = scan_directory(str(tmp_path), suffixes="csv", include=False)
    assert {name for _path, name in not_csv} == {"b.png"}
