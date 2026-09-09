"""The single scorer shared by every instrument.

All questionnaire arithmetic lives here. Instruments contribute data -- item counts,
response ranges, subscale membership, reverse keys -- and this module turns a cohort
of responses into scores without knowing which instrument it is holding.

The work is vectorised over the whole cohort. Reverse-keying is one masked
:func:`numpy.where`, and every subscale of every level is computed by a single
matrix multiplication against a precomputed weight matrix, so scoring ten thousand
participants costs one BLAS call rather than ten thousand Python loops.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from personality_questionnaire.registry import Aggregation

if TYPE_CHECKING:
    from collections.abc import Sequence

    from personality_questionnaire.registry import Questionnaire

__all__ = [
    "PairedScoreResult",
    "ScoreResult",
    "delta",
    "keyed_matrix",
    "reverse",
    "score",
    "subscale_means",
    "validate_responses",
]

SCORING_VERSION = 1
"""Version of the scoring arithmetic.

Stamped onto every stored record. Bump it whenever a change would give a different
number for the same responses, so historical records stay interpretable.
"""


def reverse(values: np.ndarray, minimum: int, maximum: int) -> np.ndarray:
    """Reverse-key responses on a scale bounded by ``minimum`` and ``maximum``.

    A reverse-keyed item measures its scale in the opposite direction, so the
    response is reflected about the scale's midpoint: ``minimum + maximum - value``.
    On the BFI-2's 1..5 that is the familiar ``6 - value``; on the VAS-F's 0..10 it
    is ``10 - value``. Deriving it from the range rather than hard-coding a constant
    is what lets one function serve every instrument.

    Args:
        values: Responses to reflect. Any shape.
        minimum: Lowest valid response on the scale.
        maximum: Highest valid response on the scale.

    Returns:
        The reflected responses, same shape and dtype as ``values``.
    """
    return (minimum + maximum) - values


def _as_matrix(answers: Sequence[Sequence] | np.ndarray) -> np.ndarray:
    """Coerce responses to a 2-D integer array of shape ``(n_participants, n_items)``.

    Accepts a single participant's answers as a flat sequence and promotes it to a
    one-row matrix, so callers scoring one person need not wrap it themselves.

    Args:
        answers: One participant's responses, or several participants'.

    Returns:
        A 2-D integer array.

    Raises:
        ValueError: If the responses are not rectangular, are not numeric, or have
            more than two dimensions.
    """
    try:
        matrix = np.asarray(answers, dtype=int)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"responses must be numeric and rectangular: {exc}") from exc

    if matrix.ndim == 1:
        matrix = matrix[np.newaxis, :]

    if matrix.ndim != 2:
        raise ValueError(f"responses must be 1- or 2-dimensional, got {matrix.ndim} dimensions")

    return matrix


def validate_responses(questionnaire: Questionnaire, answers: np.ndarray) -> None:
    """Check that responses match the instrument's shape and range.

    Args:
        questionnaire: The instrument the responses were collected with.
        answers: Responses of shape ``(n_participants, n_items)``.

    Raises:
        ValueError: If the item count is wrong, or any response falls outside the
            instrument's valid range. Both messages name the instrument, because a
            length mismatch is almost always a mixed-up instrument.
    """
    if answers.shape[1] != questionnaire.n_items:
        raise ValueError(
            f"{questionnaire.key} has {questionnaire.n_items} items, "
            f"got responses for {answers.shape[1]}"
        )

    low, high = questionnaire.minimum, questionnaire.maximum
    if answers.size and (answers.min() < low or answers.max() > high):
        raise ValueError(
            f"{questionnaire.key} responses must lie in [{low}..{high}], "
            f"got [{answers.min()}..{answers.max()}]"
        )


_WEIGHTS_CACHE: dict[int, tuple[np.ndarray, np.ndarray]] = {}
"""Per-instrument ``(weights, offsets)`` pairs, keyed by ``id()``.

:class:`Questionnaire` carries a ``dict`` of response labels and so is unhashable,
which rules out :func:`functools.lru_cache`. Instruments are module-level singletons
that live for the process, so identity is a sound cache key and the entries cannot
outlive what they describe.
"""


def _weight_matrix(questionnaire: Questionnaire) -> tuple[np.ndarray, np.ndarray]:
    """Build the signed item-to-subscale averaging matrix and its offsets.

    Reverse-keying belongs to the *subscale*, not the item: the VAS-F scores its
    five energy items forward in ``Energy`` and reversed in ``Fatigue (composite)``,
    so a single per-item mask cannot express both. Folding the reflection into the
    weights handles it per column.

    A forward item contributes ``value / k``. A reverse-keyed one contributes
    ``(min + max - value) / k``, which splits into a weight of ``-1 / k`` and a
    constant ``(min + max) / k`` gathered into the offset vector. Scoring is then
    ``answers @ weights + offsets``.

    A subscale declaring :attr:`Aggregation.SUM` uses ``k = 1``, so the same matrix
    multiplication produces a total instead of a mean.

    Args:
        questionnaire: The instrument to build the matrix for.

    Returns:
        A read-only ``(n_items, n_subscales)`` weight matrix and a read-only
        ``(n_subscales,)`` offset vector.
    """
    cached = _WEIGHTS_CACHE.get(id(questionnaire))
    if cached is not None:
        return cached

    reflection = questionnaire.minimum + questionnaire.maximum
    weights = np.zeros((questionnaire.n_items, len(questionnaire.subscales)), dtype=float)
    offsets = np.zeros(len(questionnaire.subscales), dtype=float)

    for column, subscale in enumerate(questionnaire.subscales):
        share = 1.0 if subscale.aggregation is Aggregation.SUM else 1.0 / len(subscale.items)
        for number in subscale.items:
            if number in subscale.reverse:
                weights[number - 1, column] = -share
                offsets[column] += reflection * share
            else:
                weights[number - 1, column] = share

    weights.flags.writeable = False
    offsets.flags.writeable = False
    _WEIGHTS_CACHE[id(questionnaire)] = (weights, offsets)
    return weights, offsets


def keyed_matrix(questionnaire: Questionnaire, answers: np.ndarray) -> np.ndarray:
    """Reflect every item that some subscale reverse-keys.

    Provided for inspection and for :attr:`ScoreResult.keyed`, which reports the
    responses as a reader of a single scale would see them. Scoring does not use it:
    an item may be reverse-keyed by one subscale and forward-keyed by another, so
    only the per-subscale weights in :func:`_weight_matrix` are authoritative.

    Args:
        questionnaire: The instrument the responses were collected with.
        answers: Responses of shape ``(n_participants, n_items)``.

    Returns:
        Responses with reverse-keyed items reflected, same shape as ``answers``.
    """
    mask = np.zeros(questionnaire.n_items, dtype=bool)
    for subscale in questionnaire.subscales:
        for number in subscale.reverse:
            mask[number - 1] = True

    if not mask.any():
        return answers.copy()

    return np.where(mask, reverse(answers, questionnaire.minimum, questionnaire.maximum), answers)


def subscale_means(questionnaire: Questionnaire, answers: np.ndarray) -> np.ndarray:
    """Compute every subscale mean for every participant in one operation.

    Args:
        questionnaire: The instrument the responses were collected with.
        answers: Raw responses of shape ``(n_participants, n_items)``. Reverse-keying
            is applied by the weights, so these must **not** be pre-keyed.

    Returns:
        Subscale means of shape ``(n_participants, n_subscales)``, in
        :attr:`Questionnaire.subscales` order.
    """
    weights, offsets = _weight_matrix(questionnaire)
    return answers.astype(float) @ weights + offsets


@dataclass(frozen=True, slots=True)
class ScoreResult:
    """Scores for a cohort on one instrument.

    Attributes:
        questionnaire: The instrument that was scored.
        raw: Responses exactly as given, shape ``(n_participants, n_items)``.
        keyed: Responses after reverse-keying, same shape as ``raw``.
        values: Subscale scores, shape ``(n_participants, n_subscales)``, aligned
            with ``names``.
        names: Subscale names, aligned with the columns of ``values``.
        normalized: Whether ``values`` is rescaled to ``[0, 1]`` or left on the
            instrument's own response scale. Subscales declaring
            :attr:`~personality_questionnaire.registry.Aggregation.SUM` are never
            rescaled, whatever this says.
    """

    questionnaire: Questionnaire
    raw: np.ndarray
    keyed: np.ndarray
    values: np.ndarray
    names: tuple[str, ...]
    normalized: bool

    @property
    def n_participants(self) -> int:
        """The number of scored participants."""
        return self.values.shape[0]

    def by_level(self, level: str) -> dict[str, np.ndarray]:
        """Return the scores for one subscale level.

        Args:
            level: One of the instrument's levels, e.g. ``"domain"``.

        Returns:
            A mapping of subscale name to its column of scores.
        """
        wanted = {s.name for s in self.questionnaire.subscales_at(level)}
        return {
            name: self.values[:, index] for index, name in enumerate(self.names) if name in wanted
        }

    def as_dict(self, row: int = 0) -> dict[str, float]:
        """Return one participant's scores as a mapping.

        Args:
            row: Index of the participant.

        Returns:
            A mapping of subscale name to score.
        """
        return {name: float(self.values[row, index]) for index, name in enumerate(self.names)}

    def to_records(self) -> list[dict[str, float]]:
        """Return every participant's scores as a list of mappings.

        Returns:
            One mapping per participant, in cohort order.
        """
        return [self.as_dict(row) for row in range(self.n_participants)]


@dataclass(frozen=True, slots=True)
class PairedScoreResult:
    """Pre/post scores and their difference, for a paired instrument.

    Attributes:
        pre: Scores from the first administration.
        post: Scores from the second administration.
        item_delta: Item-wise ``post - pre``, shape ``(n_participants, n_items)``.
        subscale_delta: Subscale-wise ``post - pre``, shape
            ``(n_participants, n_subscales)``.
    """

    pre: ScoreResult
    post: ScoreResult
    item_delta: np.ndarray
    subscale_delta: np.ndarray

    @property
    def names(self) -> tuple[str, ...]:
        """Subscale names, aligned with :attr:`subscale_delta` columns."""
        return self.pre.names


def score(
    questionnaire: Questionnaire,
    answers: Sequence[Sequence] | np.ndarray,
    *,
    normalize: bool | None = None,
) -> ScoreResult:
    """Score a cohort's responses to one instrument.

    Args:
        questionnaire: The instrument the responses were collected with.
        answers: Responses for one participant or several, shaped
            ``(n_items,)`` or ``(n_participants, n_items)``.
        normalize: Whether to rescale subscale means to ``[0, 1]``. Defaults to the
            instrument's own :attr:`~Questionnaire.normalize`.

    Returns:
        The computed scores.

    Raises:
        ValueError: If the responses do not match the instrument's item count or
            fall outside its response range.
    """
    matrix = _as_matrix(answers)
    validate_responses(questionnaire, matrix)

    values = subscale_means(questionnaire, matrix)
    keyed = keyed_matrix(questionnaire, matrix)

    should_normalize = questionnaire.normalize if normalize is None else normalize
    if should_normalize:
        # A subscale published as a total is left alone: rescaling it would destroy
        # the number the instrument's norms are stated in.
        low, high = questionnaire.minimum, questionnaire.maximum
        scalable = np.array([s.aggregation is not Aggregation.SUM for s in questionnaire.subscales])
        values = np.where(scalable, (values - low) / (high - low), values)
        # The weight/offset split accumulates rounding, so a scale sitting exactly at
        # its floor lands on -2.8e-17 rather than 0 and prints as "-0.000", which
        # reads as an error in a score report. Snap values that round-trip cleanly.
        values = np.where(scalable, np.round(values, 12) + 0.0, values)

    return ScoreResult(
        questionnaire=questionnaire,
        raw=matrix,
        keyed=keyed,
        values=values,
        names=tuple(s.name for s in questionnaire.subscales),
        normalized=should_normalize,
    )


def delta(
    questionnaire: Questionnaire,
    pre_answers: Sequence[Sequence] | np.ndarray,
    post_answers: Sequence[Sequence] | np.ndarray,
    *,
    normalize: bool | None = None,
) -> PairedScoreResult:
    """Score both administrations of a paired instrument and their difference.

    Args:
        questionnaire: The instrument, normally one with
            :attr:`~Questionnaire.paired` set.
        pre_answers: Responses from before the intervention.
        post_answers: Responses from after it.
        normalize: Whether to rescale subscale means to ``[0, 1]``. Defaults to the
            instrument's own setting.

    Returns:
        Both score sets and their item-wise and subscale-wise differences.

    Raises:
        ValueError: If either response set is invalid, or the two differ in the
            number of participants.
    """
    pre = score(questionnaire, pre_answers, normalize=normalize)
    post = score(questionnaire, post_answers, normalize=normalize)

    if pre.n_participants != post.n_participants:
        raise ValueError(
            f"pre and post must cover the same participants, "
            f"got {pre.n_participants} and {post.n_participants}"
        )

    return PairedScoreResult(
        pre=pre,
        post=post,
        item_delta=post.raw - pre.raw,
        subscale_delta=post.values - pre.values,
    )
