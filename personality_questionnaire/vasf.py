"""Backwards-compatible surface for the pre-2.0 VAS-F API.

:func:`vasf` keeps its exact pre-2.0 signature and return value -- an item-wise
``post - pre`` difference of shape ``(N, 18)``. Subscale scoring added in 2.0 is
reached through the registry instead, so no existing caller's indexing changes:

>>> import personality_questionnaire as pq
>>> paired = pq.delta(pq.get("vasf"), pre, post)   # doctest: +SKIP
>>> paired.subscale_delta                          # doctest: +SKIP
"""

from __future__ import annotations

import numpy as np

from personality_questionnaire.instruments.vasf import VASF, VASF_ITEM_TEXT

__all__ = ["ANSWER_DIMS", "VASF_QUESTIONNAIRE", "vasf"]

VASF_QUESTIONNAIRE: dict[int, str] = dict(VASF_ITEM_TEXT)
"""The 18 VAS-F items, keyed by item number."""

ANSWER_DIMS: dict[int, tuple[str, str]] = {
    item.number: (item.low_anchor, item.high_anchor) for item in VASF.items
}
"""Per-item low and high anchor labels."""


def vasf(
    pre_answers: list[int] | np.ndarray,
    post_answers: list[int] | np.ndarray,
) -> np.ndarray:
    """Calculate the item-wise VAS-F change across an intervention.

    Args:
        pre_answers: Answers given before the experiment.
        post_answers: Answers given after it.

    Returns:
        The item-wise ``post - pre`` difference.
    """
    return np.array(post_answers).astype(int) - np.array(pre_answers).astype(int)
