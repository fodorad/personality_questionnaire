"""Backwards-compatible surface for the pre-2.0 BFI-2 API.

Every name here has been published since 1.0.0 and keeps its exact signature. The
data is derived from :data:`personality_questionnaire.instruments.bfi2.BFI2` rather
than duplicated, so the registry stays the single source of truth.

New code should prefer the registry:

>>> import personality_questionnaire as pq
>>> result = pq.score(pq.get("bfi2"), answers)   # doctest: +SKIP

.. note::
   **Changed in 2.0.** The three Negative Emotionality facets are now scored in the
   direction their names describe. Before 2.0 they were flipped unconditionally
   while the ``neuroticism`` domain was not, so the two levels of the returned dict
   disagreed on polarity whenever ``flip_neuroticism`` was left at its default. Pass
   ``legacy_facet_polarity=True`` to reproduce pre-2.0 numbers exactly.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import numpy as np

from personality_questionnaire import scoring
from personality_questionnaire.instruments.bfi2 import BFI2, BFI2_ITEM_TEXT, BFI2_LABELS

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "ANSWER",
    "BFI2_QUESTIONNAIRE",
    "DOMAIN_SCALES",
    "FACET_SCALES",
    "bfi2",
    "bfi2_trait",
    "flip_trait_dimension",
]

BFI2_QUESTIONNAIRE: dict[int, str] = dict(BFI2_ITEM_TEXT)
"""The 60 BFI-2 items, keyed by item number."""

ANSWER: dict[str, int] = dict(BFI2_LABELS)
"""The five response labels mapped to their values."""

_NEUROTICISM_FACETS = ("Anxiety", "Depression", "Emotional Volatility")
"""Facets of Negative Emotionality, flipped unconditionally before 2.0."""


def _scale_keys(level: str) -> dict[str, list[str]]:
    """Render a subscale level in the pre-2.0 ``"5R"`` item-key notation.

    Args:
        level: The subscale level to render.

    Returns:
        A mapping of subscale name to its item keys, reverse-keyed items suffixed
        with ``"R"``.
    """
    return {
        subscale.name: [
            f"{number}R" if number in subscale.reverse else str(number) for number in subscale.items
        ]
        for subscale in BFI2.subscales_at(level)
    }


DOMAIN_SCALES: dict[str, list[str]] = _scale_keys("domain")
"""The five domain scales in ``"5R"`` item-key notation."""

FACET_SCALES: dict[str, list[str]] = _scale_keys("facet")
"""The fifteen facet scales in ``"5R"`` item-key notation."""


def _R(value: int) -> int:
    """Reverse a Big Five score.

    Args:
        value: A score between 1 and 5.

    Returns:
        The reversed score.

    Raises:
        ValueError: If ``value`` is outside 1..5.
    """
    if value not in set(range(1, 6)):
        raise ValueError("Invalid rating, value must be in the range of [1..5].")
    return int(scoring.reverse(np.asarray(value), BFI2.minimum, BFI2.maximum))


def flip_trait_dimension(single_trait_values: np.ndarray) -> np.ndarray:
    """Flip trait values within a scaled dimension.

    Every OCEAN trait except Neuroticism attaches its positive connotation to the
    high end of the dimension; Neuroticism runs the other way. Flipping it yields
    Emotional Stability, which is more convenient downstream.

    Args:
        single_trait_values: Trait values of shape ``(N,)`` in ``[0, 1]``.

    Returns:
        The flipped values.

    Raises:
        ValueError: If the input is not one-dimensional or falls outside ``[0, 1]``.
    """
    if single_trait_values.ndim > 1:
        raise ValueError(
            f"Tensor shape expected to be (N,), got instead {single_trait_values.shape}."
        )

    if single_trait_values.min() < 0 or single_trait_values.max() > 1:
        raise ValueError(
            "Tensor values are expected to be in range [0..1], got instead "
            f"[{single_trait_values.min()}..{single_trait_values.max()}]"
        )

    return 1 - single_trait_values


def bfi2_trait(answers: Sequence[Sequence], questions: list[str]) -> np.ndarray:
    """Calculate one BFI-2 trait for every answer.

    Args:
        answers: Participants' answers to the 60-item questionnaire.
        questions: Item keys for the trait, in ``"5R"`` notation.

    Returns:
        One trait value per answer, scaled to ``[0, 1]``.
    """
    matrix = np.asarray(answers, dtype=int)
    if matrix.ndim == 1:
        matrix = matrix[np.newaxis, :]

    scoring.validate_responses(BFI2, matrix)

    numbers = [int(key.rstrip("R")) for key in questions]
    reverse_flags = np.array([key.endswith("R") for key in questions])
    selected = matrix[:, [n - 1 for n in numbers]]
    reflected = scoring.reverse(selected, BFI2.minimum, BFI2.maximum)
    keyed = np.where(reverse_flags, reflected, selected)

    means = keyed.mean(axis=1)
    return (means - BFI2.minimum) / (BFI2.maximum - BFI2.minimum)


def bfi2(
    answers: Sequence[Sequence],
    flip_neuroticism: bool = False,
    *,
    legacy_facet_polarity: bool = False,
) -> dict[str, np.ndarray]:
    """Calculate BFI-2 domain and facet scale values.

    Args:
        answers: Participants' answers to the 60-item questionnaire.
        flip_neuroticism: If True, Neuroticism is converted to Emotional Stability.
            Since 2.0 this flips the domain *and* its three facets together, so both
            levels describe the same construct.
        legacy_facet_polarity: If True, reproduce the pre-2.0 behaviour in which the
            three Negative Emotionality facets were flipped regardless of
            ``flip_neuroticism``. Deprecated; provided so published results can be
            reproduced.

    Returns:
        A mapping with ``"OCEAN"`` of shape ``(N, 5)`` and ``"FACET"`` of shape
        ``(N, 15)``.
    """
    if legacy_facet_polarity:
        warnings.warn(
            "legacy_facet_polarity=True reproduces a pre-2.0 inconsistency in which "
            "the Negative Emotionality facets were scored opposite to the "
            "neuroticism domain. It will be removed in 3.0.",
            DeprecationWarning,
            stacklevel=2,
        )

    result = scoring.score(BFI2, answers)
    domains = result.by_level("domain")
    facets = result.by_level("facet")

    ocean = np.stack([domains[s.name] for s in BFI2.subscales_at("domain")], axis=1)
    if flip_neuroticism:
        index = [s.name for s in BFI2.subscales_at("domain")].index("neuroticism")
        ocean[:, index] = flip_trait_dimension(ocean[:, index])

    facet_names = [s.name for s in BFI2.subscales_at("facet")]
    facet_values = np.stack([facets[name] for name in facet_names], axis=1)

    flip_facets = legacy_facet_polarity or flip_neuroticism
    if flip_facets:
        for name in _NEUROTICISM_FACETS:
            index = facet_names.index(name)
            facet_values[:, index] = flip_trait_dimension(facet_values[:, index])

    return {"OCEAN": ocean, "FACET": facet_values}
