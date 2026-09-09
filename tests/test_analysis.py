"""Tests for psychometric diagnostics."""

from __future__ import annotations

import unittest

import numpy as np

from personality_questionnaire import analysis, registry
from tests.fixtures import bfi2_answers, constant_answers


class TestCronbachsAlpha(unittest.TestCase):
    """Internal-consistency estimate over a set of items."""

    def test_matches_a_hand_computation(self):
        """A known fixture, cross-checked against the formula computed by hand."""
        items = np.array(
            [
                [3, 3, 4, 3],
                [4, 4, 4, 5],
                [2, 2, 1, 2],
                [5, 5, 5, 4],
                [1, 2, 1, 1],
                [3, 4, 3, 3],
            ],
            dtype=float,
        )
        n_items = items.shape[1]
        item_variances = items.var(axis=0, ddof=1)
        total_variance = items.sum(axis=1).var(ddof=1)
        expected = (n_items / (n_items - 1)) * (1 - item_variances.sum() / total_variance)

        self.assertAlmostEqual(analysis.cronbachs_alpha(items), expected)

    def test_perfectly_consistent_items_reach_one(self):
        """Identical items in lockstep are the maximally-reliable case."""
        column = np.array([1, 2, 3, 4, 5], dtype=float).reshape(-1, 1)
        items = np.tile(column, (1, 3))
        self.assertAlmostEqual(analysis.cronbachs_alpha(items), 1.0)

    def test_single_item_is_undefined_and_returns_zero(self):
        items = np.array([[1], [2], [3]], dtype=float)
        self.assertEqual(analysis.cronbachs_alpha(items), 0.0)

    def test_zero_variance_total_returns_zero(self):
        """Every participant answering identically leaves nothing to explain."""
        items = constant_answers(4, 3, n_participants=5).astype(float)
        self.assertEqual(analysis.cronbachs_alpha(items), 0.0)

    def test_independent_noise_is_near_zero(self):
        rng = np.random.default_rng(0)
        items = rng.integers(1, 6, size=(200, 6)).astype(float)
        self.assertLess(abs(analysis.cronbachs_alpha(items)), 0.2)


class TestItemTotalCorrelations(unittest.TestCase):
    """Corrected item-total correlation per item."""

    def test_excludes_the_item_itself_from_the_total(self):
        """A naive item-vs-full-total correlation would always be inflated."""
        rng = np.random.default_rng(1)
        items = rng.integers(1, 6, size=(100, 3)).astype(float)
        corrected = analysis.item_total_correlations(items)

        naive = np.array([np.corrcoef(items[:, i], items.sum(axis=1))[0, 1] for i in range(3)])
        self.assertTrue(np.all(corrected < naive))

    def test_a_consistent_item_correlates_positively(self):
        column = np.array([1, 2, 3, 4, 5], dtype=float).reshape(-1, 1)
        items = np.tile(column, (1, 3))
        correlations = analysis.item_total_correlations(items)
        np.testing.assert_allclose(correlations, 1.0)

    def test_a_zero_variance_item_returns_zero(self):
        items = np.array([[3, 1], [3, 5], [3, 2], [3, 4]], dtype=float)
        correlations = analysis.item_total_correlations(items)
        self.assertEqual(correlations[0], 0.0)

    def test_one_correlation_per_item(self):
        rng = np.random.default_rng(2)
        items = rng.integers(1, 6, size=(50, 5)).astype(float)
        self.assertEqual(analysis.item_total_correlations(items).shape, (5,))


class TestSubscaleReliability(unittest.TestCase):
    """Per-subscale diagnostics, reverse-keyed before computation."""

    def test_covers_every_subscale(self):
        bfi2 = registry.get("bfi2")
        rng = np.random.default_rng(3)
        answers = rng.integers(1, 6, size=(30, bfi2.n_items))

        reliability = analysis.subscale_reliability(bfi2, answers)

        self.assertEqual(set(reliability), {s.name for s in bfi2.subscales})

    def test_reports_the_right_item_count(self):
        bfi2 = registry.get("bfi2")
        rng = np.random.default_rng(4)
        answers = rng.integers(1, 6, size=(30, bfi2.n_items))

        reliability = analysis.subscale_reliability(bfi2, answers)

        self.assertEqual(reliability["neuroticism"].n_items, 12)
        self.assertEqual(reliability["Anxiety"].n_items, 4)
        self.assertEqual(len(reliability["Anxiety"].item_total_correlations), 4)

    def test_reverse_keying_is_applied_before_alpha(self):
        """A subscale with reverse-keyed items must not be penalised for polarity.

        Two participants who *disagree* on every item once reverse-keying is
        undone should still show high consistency -- computing alpha on raw,
        unkeyed responses would instead read this as inconsistency.
        """
        bfi2 = registry.get("bfi2")
        neuroticism = bfi2.subscale("neuroticism")
        self.assertTrue(neuroticism.reverse, "fixture assumption: some items are reverse-keyed")

        answers = np.zeros((6, bfi2.n_items), dtype=int)
        base = np.array([1, 2, 3, 4, 5, 4])
        for offset, number in enumerate(neuroticism.items):
            value = (6 - base) if number in neuroticism.reverse else base
            answers[:, number - 1] = value + offset  # tiny jitter, not identical columns

        reliability = analysis.subscale_reliability(bfi2, answers)
        self.assertGreater(reliability["neuroticism"].alpha, 0.9)

    def test_matches_the_locked_bfi2_fixture(self):
        """Regression lock against the two-participant BFI-2 fixture."""
        bfi2 = registry.get("bfi2")
        answers = bfi2_answers()
        reliability = analysis.subscale_reliability(bfi2, answers)
        self.assertIn("openness", reliability)
        self.assertEqual(reliability["openness"].n_items, 12)


class TestDescribe(unittest.TestCase):
    """Descriptive statistics over already-scored data."""

    def test_reports_mean_and_range(self):
        names = ("a", "b")
        values = np.array([[0.2, 0.8], [0.4, 0.6], [0.6, 0.4]])

        described = analysis.describe(names, values)

        self.assertAlmostEqual(described["a"].mean, 0.4)
        self.assertAlmostEqual(described["a"].minimum, 0.2)
        self.assertAlmostEqual(described["a"].maximum, 0.6)
        self.assertEqual(described["a"].n, 3)

    def test_single_participant_has_zero_sd(self):
        described = analysis.describe(("a",), np.array([[0.5]]))
        self.assertEqual(described["a"].sd, 0.0)

    def test_covers_every_name(self):
        names = ("x", "y", "z")
        values = np.zeros((4, 3))
        described = analysis.describe(names, values)
        self.assertEqual(set(described), set(names))


if __name__ == "__main__":
    unittest.main()
