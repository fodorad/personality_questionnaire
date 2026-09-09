"""Tests for the Positive and Negative Affect Schedule.

The PANAS is the first shipped instrument with no reverse-keyed items and the first
to report a published total alongside a normalised mean, so these tests cover both
of those paths as well as the item key itself.
"""

from __future__ import annotations

import unittest

import numpy as np

import personality_questionnaire as pq
from personality_questionnaire.instruments.panas import PANAS, PANAS_ITEM_TEXT, PANAS_LABELS
from personality_questionnaire.registry import Aggregation

PUBLISHED_POSITIVE = (1, 3, 5, 9, 10, 12, 14, 16, 17, 19)
"""Positive Affect items, from the published scoring key."""

PUBLISHED_NEGATIVE = (2, 4, 6, 7, 8, 11, 13, 15, 18, 20)
"""Negative Affect items, from the published scoring key."""

PUBLISHED_ITEMS = {
    1: "Interested",
    2: "Distressed",
    3: "Excited",
    4: "Upset",
    5: "Strong",
    6: "Guilty",
    7: "Scared",
    8: "Hostile",
    9: "Enthusiastic",
    10: "Proud",
    11: "Irritable",
    12: "Alert",
    13: "Ashamed",
    14: "Inspired",
    15: "Nervous",
    16: "Determined",
    17: "Attentive",
    18: "Jittery",
    19: "Active",
    20: "Afraid",
}
"""The adjectives as printed, in administration order."""


class TestPublishedKey(unittest.TestCase):
    """Membership and wording must match the published form."""

    def test_item_text_matches(self):
        self.assertEqual(PANAS_ITEM_TEXT, PUBLISHED_ITEMS)

    def test_twenty_items(self):
        self.assertEqual(PANAS.n_items, 20)

    def test_positive_scale_matches(self):
        self.assertEqual(PANAS.subscale("Positive Affect").items, PUBLISHED_POSITIVE)

    def test_negative_scale_matches(self):
        self.assertEqual(PANAS.subscale("Negative Affect").items, PUBLISHED_NEGATIVE)

    def test_the_two_scales_partition_the_items(self):
        """Every adjective belongs to exactly one scale."""
        positive, negative = set(PUBLISHED_POSITIVE), set(PUBLISHED_NEGATIVE)
        self.assertEqual(positive | negative, set(range(1, 21)))
        self.assertEqual(positive & negative, set())

    def test_ten_items_per_scale(self):
        self.assertEqual(len(PUBLISHED_POSITIVE), 10)
        self.assertEqual(len(PUBLISHED_NEGATIVE), 10)

    def test_response_labels_describe_intensity(self):
        self.assertEqual(PANAS_LABELS["Very slightly or not at all"], 1)
        self.assertEqual(PANAS_LABELS["Extremely"], 5)


class TestNoReverseKeying(unittest.TestCase):
    """Every adjective scores in the direction it is worded."""

    def test_no_subscale_reverses_anything(self):
        for subscale in PANAS.subscales:
            with self.subTest(subscale=subscale.name):
                self.assertEqual(subscale.reverse, frozenset())

    def test_keyed_matrix_is_a_no_op(self):
        """With an empty reverse mask the keying pass must leave answers untouched."""
        from personality_questionnaire import scoring

        answers = np.array([[1, 2, 3, 4, 5] * 4])
        np.testing.assert_array_equal(scoring.keyed_matrix(PANAS, answers), answers)

    def test_a_negative_adjective_does_not_lower_positive_affect(self):
        """The scales are near-independent, not two ends of one dimension."""
        calm = [1] * 20
        distressed = list(calm)
        for item in PUBLISHED_NEGATIVE:
            distressed[item - 1] = 5

        before = pq.score(PANAS, [calm]).as_dict()
        after = pq.score(PANAS, [distressed]).as_dict()
        self.assertEqual(before["Positive Affect"], after["Positive Affect"])
        self.assertGreater(after["Negative Affect"], before["Negative Affect"])


class TestScoring(unittest.TestCase):
    """Means and published totals are reported side by side."""

    def test_midpoint_answers_score_one_half(self):
        scores = pq.score(PANAS, [[3] * 20]).as_dict()
        self.assertAlmostEqual(scores["Positive Affect"], 0.5)
        self.assertAlmostEqual(scores["Negative Affect"], 0.5)

    def test_totals_span_the_published_range(self):
        """Watson et al. state each scale runs 10-50."""
        floor = pq.score(PANAS, [[1] * 20]).as_dict()
        ceiling = pq.score(PANAS, [[5] * 20]).as_dict()
        self.assertAlmostEqual(floor["Positive Affect (sum)"], 10)
        self.assertAlmostEqual(ceiling["Positive Affect (sum)"], 50)
        self.assertAlmostEqual(floor["Negative Affect (sum)"], 10)
        self.assertAlmostEqual(ceiling["Negative Affect (sum)"], 50)

    def test_totals_are_not_normalised(self):
        """Rescaling a published total would destroy the number its norms use."""
        for name in ("Positive Affect (sum)", "Negative Affect (sum)"):
            with self.subTest(subscale=name):
                self.assertIs(PANAS.subscale(name).aggregation, Aggregation.SUM)

    def test_total_is_ten_times_the_mean(self):
        rng = np.random.default_rng(20260909)
        answers = rng.integers(1, 6, size=(20, 20))
        scores = pq.score(PANAS, answers, normalize=False)
        by_name = dict(zip(scores.names, scores.values.T, strict=True))
        np.testing.assert_allclose(
            by_name["Positive Affect (sum)"], by_name["Positive Affect"] * 10
        )

    def test_scores_match_a_hand_computation(self):
        answers = np.zeros((1, 20), dtype=int)
        for item in PUBLISHED_POSITIVE:
            answers[0, item - 1] = 4
        for item in PUBLISHED_NEGATIVE:
            answers[0, item - 1] = 2

        scores = pq.score(PANAS, answers).as_dict()
        self.assertAlmostEqual(scores["Positive Affect (sum)"], 40)
        self.assertAlmostEqual(scores["Negative Affect (sum)"], 20)
        self.assertAlmostEqual(scores["Positive Affect"], 0.75)
        self.assertAlmostEqual(scores["Negative Affect"], 0.25)

    def test_the_floor_reports_a_clean_zero(self):
        """Rounding residue must not surface as "-0.000" in a score report."""
        values = pq.score(PANAS, [[1] * 20]).values
        self.assertFalse(any(np.signbit(v) and v == 0 for v in values.ravel()))
        self.assertNotIn("-0.000", "".join(f"{v:.3f}" for v in values.ravel()))

    def test_rejects_a_wrong_length_response(self):
        with self.assertRaisesRegex(ValueError, "panas has 20 items"):
            pq.score(PANAS, [[3] * 10])


class TestPairedUse(unittest.TestCase):
    """The PANAS suits pre/post administration, like the VAS-F."""

    def test_delta_reports_change_in_both_scales(self):
        before = [[2] * 20]
        after = [[4] * 20]
        paired = pq.delta(PANAS, before, after)
        by_name = dict(zip(paired.names, paired.subscale_delta.T, strict=True))
        self.assertAlmostEqual(float(by_name["Positive Affect"][0]), 0.5)
        self.assertAlmostEqual(float(by_name["Positive Affect (sum)"][0]), 20)


class TestRegistration(unittest.TestCase):
    """The instrument is discoverable and self-describing."""

    def test_registered_under_its_key(self):
        self.assertIs(pq.get("panas"), PANAS)

    def test_cites_watson_clark_and_tellegen(self):
        self.assertIn("Watson", PANAS.citation)
        self.assertIn("1988", PANAS.citation)

    def test_prompt_states_the_time_frame(self):
        """The window is the instrument's one deliberate variable."""
        self.assertIn("past week", PANAS.item(1).prompt)

    def test_every_subscale_declares_direction(self):
        for subscale in PANAS.subscales:
            with self.subTest(subscale=subscale.name):
                self.assertTrue(subscale.higher_is)


if __name__ == "__main__":
    unittest.main()
