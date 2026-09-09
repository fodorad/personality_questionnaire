"""Remembering which databases an operator has recently used.

A lab operator plausibly switches between a few SQLite files across sessions --
per-study databases, or a shared-drive copy versus a local scratch copy -- so the
Setup tab's database picker offers a short most-recently-used list alongside
browsing. The list is a convenience, not a correctness requirement: a write
failure here is logged and swallowed rather than blocking a database switch.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from personality_questionnaire.db.session import default_database_path

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["MAX_ENTRIES", "load_recent", "recent_databases_path", "remember_database"]

log = logging.getLogger("personality_questionnaire")

MAX_ENTRIES = 8
"""How many recent database URLs to keep."""

_FILENAME = "recent_databases.json"
"""Name of the MRU file, alongside the default database."""


def recent_databases_path() -> Path:
    """Return where the most-recently-used database list is stored.

    Sits beside the default database file, under the same ``$PQ_HOME`` (or
    ``~/.personality_questionnaire``) directory used elsewhere in this package.

    Returns:
        The path to the MRU JSON file.
    """
    return default_database_path().parent / _FILENAME


def load_recent(path: Path | None = None) -> list[str]:
    """Return remembered database URLs, most-recently-used first.

    Args:
        path: The MRU file to read. Defaults to :func:`recent_databases_path`.

    Returns:
        The remembered URLs, or an empty list if the file is missing, unreadable,
        or not valid JSON -- a corrupt MRU file is a non-event, not an error.
    """
    target = path or recent_databases_path()
    try:
        raw = target.read_text(encoding="utf-8")
        entries = json.loads(raw)
    except (OSError, ValueError):
        return []

    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, str)][:MAX_ENTRIES]


def remember_database(url: str, path: Path | None = None) -> list[str]:
    """Move ``url`` to the front of the recent list, capped and de-duplicated.

    Args:
        url: The database URL just switched to.
        path: The MRU file to update. Defaults to :func:`recent_databases_path`.

    Returns:
        The updated list, most-recently-used first.
    """
    target = path or recent_databases_path()
    entries = load_recent(target)
    entries = [url, *[entry for entry in entries if entry != url]][:MAX_ENTRIES]

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    except OSError as exc:
        log.debug("could not write recent-databases file %s: %s", target, exc)

    return entries
