"""Pure filesystem helpers behind the database picker.

Scoped deliberately narrow: this package has exactly one picker call site and one
target file type (SQLite databases), so a general folder/file browser -- the kind a
video-annotation tool needs -- would buy nothing here. Kept separate from the picker
dialog itself (in ``pages/db_picker.py``) so the logic is covered directly rather
than through the UI layer, matching every other module under ``core/``.
"""

from __future__ import annotations

from pathlib import Path

from personality_questionnaire.db.session import default_database_path

__all__ = ["is_valid_sqlite_url", "parent_of", "resolve_start_dir", "scan_databases"]

_DATABASE_SUFFIXES = frozenset({".db", ".sqlite", ".sqlite3"})
"""File extensions the picker treats as a database."""


def scan_databases(directory: Path) -> tuple[list[Path], list[Path]]:
    """List a directory's subdirectories and database files, for a picker to show.

    Args:
        directory: The directory to list.

    Returns:
        Subdirectories and database files, each sorted by name. Both are empty if
        the directory cannot be read -- browsing is best-effort, not guaranteed.
    """
    try:
        entries = list(directory.iterdir())
    except OSError:
        return [], []

    subdirs = sorted((e for e in entries if e.is_dir()), key=lambda p: p.name.lower())
    files = sorted(
        (e for e in entries if e.is_file() and e.suffix.lower() in _DATABASE_SUFFIXES),
        key=lambda p: p.name.lower(),
    )
    return subdirs, files


def parent_of(directory: Path) -> Path | None:
    """Return a directory's parent, or ``None`` if already at the filesystem root.

    Args:
        directory: The directory to find the parent of.

    Returns:
        The parent directory, or ``None``.
    """
    parent = directory.parent
    return None if parent == directory else parent


def resolve_start_dir(current_url: str | None) -> Path:
    """Choose where the database picker should open.

    Args:
        current_url: The active ``sqlite:///...`` URL, or ``None``.

    Returns:
        The current database's directory if it names a local SQLite file, else the
        default database's directory.
    """
    if current_url and current_url.startswith("sqlite:///") and ":memory:" not in current_url:
        candidate = Path(current_url.removeprefix("sqlite:///")).parent
        if candidate.exists():
            return candidate
    return default_database_path().parent


def is_valid_sqlite_url(url: str) -> bool:
    """Whether ``url`` is a plausible local SQLite URL this app could open.

    Not a guarantee the file is a valid database -- SQLAlchemy discovers that on
    first use -- only that the URL is shaped correctly and points somewhere this
    process could plausibly read or create a file.

    Args:
        url: The candidate database URL.

    Returns:
        True if the URL looks like a usable local SQLite target.
    """
    if not url.startswith("sqlite:///"):
        return False
    if ":memory:" in url:
        return True
    path = Path(url.removeprefix("sqlite:///"))
    return path.parent.exists() or path.exists()
