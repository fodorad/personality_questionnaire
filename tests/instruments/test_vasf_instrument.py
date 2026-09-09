"""Tests for the VAS-F instrument definition."""

from __future__ import annotations

import unittest

import numpy as np

from personality_questionnaire import get, scoring
from personality_questionnaire.vasf import ANSWER_DIMS, VASF_QUESTIONNAIRE, vasf
from tests.fixtures import constant_answers


class TestLegacySurface(unittest.TestCase):
    """The published API keeps its exact shape and values."""

    def test_delta_is_item_wise_post_minus_pre(self):
        pre = [1] * 18
        post = [4] * 18
        np.testing.assert_array_equal(vasf(pre, post), np.full(18, 3))

    def test_accepts_a_two_dimensional_pre(self):
        pre = np.full((1, 18), 2)
        result = vasf(pre, [5] * 18)
        self.assertEqual(result.shape, (1, 18))

    def test_tables_are_complete(self):
        self.assertEqual(len(VASF_QUESTIONNAIRE), 18)
        self.assertEqual(len(ANSWER_DIMS), 18)
        self.assertEqual(ANSWER_DIMS[1], ("not at all", "extremely"))
        self.assertEqual(ANSWER_DIMS[13], ("is no effort at all", "is a tremendous chore"))


class TestPrompts(unittest.TestCase):
    """Prompt assembly lives in the instrument, not the caller."""

    def setUp(self):
        self.vasf = get("vasf")

    def test_adjective_item_puts_the_anchor_first(self):
        self.assertEqual(
            self.vasf.item(1).prompt,
            '0 means "not at all tired", 10 means "extremely tired"',
        )

    def test_effort_item_puts_the_anchor_last(self):
        self.assertEqual(
            self.vasf.item(13).prompt,
            '0 means "keeping my eyes open is no effort at all", '
            '10 means "keeping my eyes open is a tremendous chore"',
        )

    def test_desire_item_puts_the_anchor_first(self):
        self.assertIn("I have absolutely no desire to close my eyes", self.vasf.item(17).prompt)


class TestSubscales(unittest.TestCase):
    """Fatigue and Energy are scored in their own directions."""

    def setUp(self):
        self.vasf = get("vasf")

    def test_membership(self):
        self.assertEqual(len(self.vasf.subscale("Fatigue").items), 13)
        self.assertEqual(self.vasf.subscale("Energy").items, (6, 7, 8, 9, 10))

    def test_energy_is_not_reverse_keyed_in_its_own_scale(self):
        self.assertEqual(self.vasf.subscale("Energy").reverse, frozenset())

    def test_composite_reverses_the_energy_items(self):
        composite = self.vasf.subscale("Fatigue (composite)")
        self.assertEqual(composite.reverse, frozenset({6, 7, 8, 9, 10}))
        self.assertEqual(len(composite.items), 18)

    def test_energy_reports_the_raw_response(self):
        scores = scoring.score(self.vasf, constant_answers(18, 3), normalize=False).as_dict()
        self.assertAlmostEqual(scores["Energy"], 3.0)
        self.assertAlmostEqual(scores["Fatigue"], 3.0)

    def test_composite_reflects_the_energy_items(self):
        scores = scoring.score(self.vasf, constant_answers(18, 3), normalize=False).as_dict()
        self.assertAlmostEqual(scores["Fatigue (composite)"], (13 * 3 + 5 * 7) / 18)

    def test_energy_and_fatigue_move_oppositely(self):
        tired = scoring.score(
            self.vasf, np.array([[9] * 5 + [1] * 5 + [9] * 8]), normalize=False
        ).as_dict()
        self.assertGreater(tired["Fatigue"], tired["Energy"])


if __name__ == "__main__":
    unittest.main()
