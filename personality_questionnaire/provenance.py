"""Runtime provenance for a collected record.

A stored record should say what produced it. This module snapshots the package
version, the git revision when running from a checkout, and whether that checkout
had uncommitted changes -- which is the difference between a record that can be
reproduced exactly and one that cannot.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from personality_questionnaire.registry import Questionnaire

__all__ = ["Provenance", "capture", "instrument_hash"]

_GIT_TIMEOUT_SECONDS = 5
"""Ceiling on any git subprocess, so a stale lock cannot hang data collection."""

_CACHED: Provenance | None = None
"""Process-wide snapshot; git state is read once, not once per record."""


@dataclass(frozen=True, slots=True)
class Provenance:
    """What produced a record.

    Attributes:
        package_version: Installed version of this package.
        git_sha: Full commit hash, or ``None`` when not running from a checkout.
            An installed wheel has no repository, and inventing a hash would be
            worse than recording its absence.
        git_dirty: Whether the checkout had uncommitted changes. A dirty tree means
            the record cannot be reproduced from any commit.
        python_version: Running interpreter version.
        captured_at: When the snapshot was taken, in UTC.
    """

    package_version: str
    git_sha: str | None
    git_dirty: bool
    python_version: str
    captured_at: datetime

    def as_dict(self) -> dict:
        """Return the snapshot as a JSON-serialisable mapping.

        Returns:
            The fields, with the timestamp rendered as an ISO-8601 string.
        """
        payload = asdict(self)
        payload["captured_at"] = self.captured_at.isoformat()
        return payload


def _git(*args: str) -> str | None:
    """Run a git command inside the package directory.

    Args:
        *args: Arguments following ``git``.

    Returns:
        Stripped stdout, or ``None`` if git is unavailable, times out, or the
        directory is not a repository.
    """
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if completed.returncode != 0:
        return None

    return completed.stdout.strip()


def capture(*, refresh: bool = False) -> Provenance:
    """Snapshot the runtime.

    Args:
        refresh: Re-read git state instead of using the cached snapshot.

    Returns:
        The provenance of the current process.
    """
    global _CACHED
    if _CACHED is not None and not refresh:
        return _CACHED

    from personality_questionnaire import __version__

    sha = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain") if sha else None

    _CACHED = Provenance(
        package_version=__version__,
        git_sha=sha,
        git_dirty=bool(status),
        python_version=platform.python_version(),
        captured_at=datetime.now(UTC),
    )
    return _CACHED


def instrument_hash(questionnaire: Questionnaire) -> str:
    """Hash an instrument's scored definition.

    Pins exactly what was administered, so a later wording fix or scale correction
    cannot retroactively change the meaning of an existing record.

    Args:
        questionnaire: The instrument to fingerprint.

    Returns:
        A ``sha256:``-prefixed hex digest.
    """
    canonical = {
        "key": questionnaire.key,
        "minimum": questionnaire.minimum,
        "maximum": questionnaire.maximum,
        "items": [[item.number, item.text] for item in questionnaire.items],
        "subscales": [
            {
                "name": subscale.name,
                "items": list(subscale.items),
                "reverse": sorted(subscale.reverse),
                "level": subscale.level,
            }
            for subscale in questionnaire.subscales
        ],
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
