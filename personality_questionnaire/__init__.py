"""Administer, score and record validated personality and affect questionnaires.

The package is organised around a registry of instruments. Each instrument is data
-- items, response range, subscale membership, reverse keys -- and a single
vectorised scorer turns responses into scores:

>>> import personality_questionnaire as pq
>>> bfi2 = pq.get("bfi2")
>>> result = pq.score(bfi2, [[3] * 60])
>>> round(result.as_dict()["extraversion"], 3)
0.5

The pre-2.0 functional API (:func:`personality_questionnaire.bfi2.bfi2` and
:func:`personality_questionnaire.vasf.vasf`) is still supported; see those modules.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any

from personality_questionnaire import instruments as instruments
from personality_questionnaire.registry import (
    REGISTRY,
    Item,
    Questionnaire,
    ScaleType,
    Subscale,
    get,
    keys,
    register,
)
from personality_questionnaire.scoring import (
    PairedScoreResult,
    ScoreResult,
    delta,
    score,
)

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable

__version__ = "2.6.0"
"""The installed package version.

Managed by release-please; do not edit by hand.
"""

__all__ = [
    "REGISTRY",
    "Item",
    "PairedScoreResult",
    "Questionnaire",
    "ScaleType",
    "ScoreResult",
    "Subscale",
    "__version__",
    "asset",
    "delta",
    "get",
    "keys",
    "register",
    "score",
]

_DEPRECATED_PATHS = frozenset({"PROJECT_DIR", "DATA_DIR"})
"""Module attributes kept only for pre-2.0 compatibility."""


def asset(name: str) -> Traversable:
    """Return a data file shipped inside the package.

    Works from a wheel, an sdist and a source checkout alike, which the pre-2.0
    ``DATA_DIR`` did not: it resolved relative to the repository root, so an
    installed wheel pointed at a ``data`` directory beside ``site-packages`` that
    had never been shipped.

    Args:
        name: File name relative to the package's ``assets`` directory.

    Returns:
        A traversable handle supporting ``.read_text()`` and ``.open()``.
    """
    return files("personality_questionnaire") / "assets" / name


def __getattr__(name: str) -> Any:
    """Serve the deprecated path constants with a warning.

    Args:
        name: The attribute being looked up.

    Returns:
        The requested path.

    Raises:
        AttributeError: If ``name`` is not a module attribute.
    """
    if name in _DEPRECATED_PATHS:
        import warnings

        warnings.warn(
            f"personality_questionnaire.{name} is deprecated and does not resolve "
            "from an installed wheel; use personality_questionnaire.asset() to read "
            "shipped data files.",
            DeprecationWarning,
            stacklevel=2,
        )
        project_dir = Path(__file__).resolve().parents[1]
        return project_dir if name == "PROJECT_DIR" else project_dir / "data"

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
