"""Reading and writing questionnaire responses and scores.

The readers accept the formats the pre-2.0 CLI wrote -- headerless CSV of integers
or of response labels, and tab-separated item tables -- and the writers produce them.
Every file is opened with an explicit encoding and, for CSV, ``newline=""`` as the
:mod:`csv` module requires, so output is byte-identical across platforms.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

__all__ = [
    "PathType",
    "load_csv",
    "load_csv_int",
    "load_csv_str",
    "load_json",
    "load_tsv",
    "save_csv",
    "save_csv_int",
    "save_json",
]

PathType = str | os.PathLike
"""Anything acceptable as a filesystem path."""

_ENCODING = "utf-8"
"""Encoding used for every file this module reads or writes."""


def load_csv(
    csv_path: PathType,
    n_values: int,
    conversion_fn: Callable[[str], Any],
) -> np.ndarray:
    """Load a headerless CSV, converting each cell.

    Args:
        csv_path: File to read.
        n_values: Number of values expected per row.
        conversion_fn: Applied to every cell.

    Returns:
        An array of shape ``(n_rows, n_values)``.

    Raises:
        ValueError: If a row does not hold exactly ``n_values`` cells, or a cell
            cannot be converted. Both messages name the offending line.
    """
    rows: list[list[Any]] = []
    with open(csv_path, encoding=_ENCODING, newline="") as handle:
        for line_number, row in enumerate(csv.reader(handle), start=1):
            if not row or all(cell.strip() == "" for cell in row):
                continue

            if len(row) != n_values:
                raise ValueError(
                    f"{csv_path}: line {line_number} has {len(row)} values, expected {n_values}"
                )

            try:
                rows.append([conversion_fn(cell.strip()) for cell in row])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"{csv_path}: line {line_number} is not convertible: {exc}"
                ) from exc

    if not rows:
        return np.zeros((0, n_values))

    return np.array(rows)


def load_csv_int(csv_path: PathType, n_values: int) -> np.ndarray:
    """Load a headerless CSV of integer responses.

    Args:
        csv_path: File to read.
        n_values: Number of values expected per row.

    Returns:
        An integer array of shape ``(n_rows, n_values)``.
    """
    return load_csv(csv_path, n_values, int).astype(int)


def load_csv_str(csv_path: PathType, n_values: int) -> np.ndarray:
    """Load a headerless CSV of BFI-2 response labels.

    Args:
        csv_path: File to read.
        n_values: Number of values expected per row.

    Returns:
        An integer array of shape ``(n_rows, n_values)``.
    """
    from personality_questionnaire.instruments.bfi2 import BFI2_LABELS

    return load_csv(csv_path, n_values, lambda cell: BFI2_LABELS[cell]).astype(int)


def load_tsv(tsv_path: PathType) -> dict[int, str]:
    """Load a tab-separated item table with an ``ID``/``ITEM`` header.

    Args:
        tsv_path: File to read.

    Returns:
        A mapping of item number to item text.
    """
    with open(tsv_path, encoding=_ENCODING, newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        next(reader, None)
        return {int(row[0]): row[1] for row in reader if row}


def _write_rows(csv_path: PathType, rows: Iterable[Iterable]) -> None:
    """Write rows to a headerless CSV, creating parent directories.

    Args:
        csv_path: File to write. Parent directories are created as needed.
        rows: Rows to write. Any iterable of iterables, so a numpy array and a
            list of lists are both accepted.
    """
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding=_ENCODING, newline="") as handle:
        csv.writer(handle).writerows(rows)


def save_csv_int(csv_path: PathType, data: Sequence[Sequence]) -> None:
    """Write integer responses to a headerless CSV.

    Args:
        csv_path: File to write.
        data: Rows of integer responses.
    """
    _write_rows(csv_path, [[int(value) for value in row] for row in data])


def save_csv(csv_path: PathType, data: np.ndarray) -> None:
    """Write scores to a headerless CSV.

    Args:
        csv_path: File to write.
        data: Rows of scores.
    """
    _write_rows(csv_path, np.atleast_2d(data))


def save_json(json_path: PathType, payload: dict) -> Path:
    """Write a mapping as indented JSON.

    Args:
        json_path: File to write.
        payload: The mapping to serialise.

    Returns:
        The path written, so a caller can report it.
    """
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding=_ENCODING)
    return path


def load_json(json_path: PathType) -> dict:
    """Read a JSON mapping.

    Args:
        json_path: File to read.

    Returns:
        The parsed mapping.
    """
    return json.loads(Path(json_path).read_text(encoding=_ENCODING))
