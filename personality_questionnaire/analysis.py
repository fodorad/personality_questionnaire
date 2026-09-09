"""Psychometric diagnostics over collected records.

Scoring turns responses into subscale values; this module asks whether those
values were worth computing -- whether a subscale's items actually measure one
thing (Cronbach's alpha), which items pull their weight (item-total correlation),
and how a cohort's scores are distributed (descriptive statistics). Everything
here is read-only: it consumes responses and scores already produced by
:mod:`personality_questionnaire.scoring`, and writes nothing back.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from personality_questionnaire import scoring

if TYPE_CHECKING:
    from personality_questionnaire.registry import Questionnaire

__all__ = [
    "Descriptive",
    "SubscaleReliability",
    "cronbachs_alpha",
    "describe",
    "item_total_correlations",
    "subscale_reliability",
]


def cronbachs_alpha(items: np.ndarray) -> float:
    """Compute Cronbach's alpha for a set of items.

    Args:
        items: Keyed responses, shape ``(n_participants, n_items)``. Any item this
            subscale reverse-keys must already be reflected -- alpha assumes every
            column points the same direction, and a mixed-polarity item silently
            produces a lower (sometimes negative) value instead of an error.

    Returns:
        Alpha, unbounded above 1 and below 0 for a genuinely inconsistent scale.
        ``0.0`` for a single-item scale, where internal consistency is undefined.
    """
    n_items = items.shape[1]
    if n_items < 2:
        return 0.0

    item_variances = items.var(axis=0, ddof=1)
    total_variance = items.sum(axis=1).var(ddof=1)
    if total_variance == 0:
        return 0.0

    return (n_items / (n_items - 1)) * (1 - item_variances.sum() / total_variance)


def item_total_correlations(items: np.ndarray) -> np.ndarray:
    """Compute each item's corrected item-total correlation.

    An item is correlated against the sum of every *other* item in the same set --
    correlating it against a total that includes itself would inflate the value,
    especially for a scale with few items.

    Args:
        items: Keyed responses, shape ``(n_participants, n_items)``, reverse-keying
            already applied as in :func:`cronbachs_alpha`.

    Returns:
        One correlation per item, shape ``(n_items,)``. ``0.0`` for an item with no
        variance (every participant gave the same response), where correlation is
        undefined.
    """
    n_items = items.shape[1]
    correlations = np.zeros(n_items)
    for index in range(n_items):
        item = items[:, index]
        rest = items[:, np.arange(n_items) != index].sum(axis=1)
        if item.std() == 0 or rest.std() == 0:
            continue
        correlations[index] = np.corrcoef(item, rest)[0, 1]
    return correlations


@dataclass(frozen=True, slots=True)
class SubscaleReliability:
    """Internal-consistency diagnostics for one subscale.

    Attributes:
        name: The subscale's display name.
        n_items: How many items it comprises.
        alpha: Cronbach's alpha over this cohort.
        item_total_correlations: One correlation per item, in the subscale's own
            item order.
    """

    name: str
    n_items: int
    alpha: float
    item_total_correlations: tuple[float, ...]


def subscale_reliability(
    questionnaire: Questionnaire, answers: np.ndarray
) -> dict[str, SubscaleReliability]:
    """Compute reliability diagnostics for every subscale of an instrument.

    Args:
        questionnaire: The instrument the responses were collected with.
        answers: Raw (unkeyed) responses, shape ``(n_participants, n_items)``.

    Returns:
        Subscale name to its reliability diagnostics.
    """
    result: dict[str, SubscaleReliability] = {}
    for subscale in questionnaire.subscales:
        columns = np.array([number - 1 for number in subscale.items])
        raw = answers[:, columns]
        reverse_mask = np.array([number in subscale.reverse for number in subscale.items])
        keyed = np.where(
            reverse_mask, scoring.reverse(raw, questionnaire.minimum, questionnaire.maximum), raw
        )
        result[subscale.name] = SubscaleReliability(
            name=subscale.name,
            n_items=len(subscale.items),
            alpha=cronbachs_alpha(keyed),
            item_total_correlations=tuple(item_total_correlations(keyed).tolist()),
        )
    return result


@dataclass(frozen=True, slots=True)
class Descriptive:
    """Summary statistics for one subscale's scores.

    Attributes:
        name: The subscale's display name.
        n: Number of participants.
        mean: Sample mean.
        sd: Sample standard deviation (``ddof=1``); ``0.0`` for a single participant.
        minimum: Smallest observed value.
        maximum: Largest observed value.
    """

    name: str
    n: int
    mean: float
    sd: float
    minimum: float
    maximum: float


def describe(names: tuple[str, ...], values: np.ndarray) -> dict[str, Descriptive]:
    """Compute descriptive statistics for a cohort's subscale scores.

    Args:
        names: Subscale names, aligned with the columns of ``values`` -- typically
            :attr:`~personality_questionnaire.scoring.ScoreResult.names`.
        values: Subscale scores, shape ``(n_participants, n_subscales)`` --
            typically :attr:`~personality_questionnaire.scoring.ScoreResult.values`.

    Returns:
        Subscale name to its descriptive statistics.
    """
    n = values.shape[0]
    result: dict[str, Descriptive] = {}
    for index, name in enumerate(names):
        column = values[:, index]
        result[name] = Descriptive(
            name=name,
            n=n,
            mean=float(column.mean()),
            sd=float(column.std(ddof=1)) if n > 1 else 0.0,
            minimum=float(column.min()),
            maximum=float(column.max()),
        )
    return result
