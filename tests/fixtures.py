"""Shared test data and helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np

FIXTURE_DIR = Path(__file__).resolve().parent / "data"
"""Directory holding the checked-in response fixtures."""

PUBLISHED_OCEAN = np.array(
    [
        [0.521, 0.646, 0.417, 0.604, 0.250],
        [0.583, 0.208, 0.729, 0.438, 0.604],
    ]
)
"""Domain scores this package has returned since 1.0.0, in OCEAN order.

Locked here so any refactor that changes a published number fails loudly.
"""


def bfi2_answers() -> np.ndarray:
    """Load the two-participant BFI-2 response fixture.

    Returns:
        Responses of shape ``(2, 60)``.
    """
    return np.load(FIXTURE_DIR / "test_bfi2_answers.npy")


def constant_answers(n_items: int, value: int, n_participants: int = 1) -> np.ndarray:
    """Build a cohort answering every item identically.

    Args:
        n_items: Items per participant.
        value: The response to repeat.
        n_participants: Number of participants.

    Returns:
        Responses of shape ``(n_participants, n_items)``.
    """
    return np.full((n_participants, n_items), value, dtype=int)
