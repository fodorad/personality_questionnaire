"""Tests for the pre-2.0 ``personality_questionnaire.vasf`` compatibility surface.

The instrument definition itself is covered by
``tests/instruments/test_vasf_instrument.py``.
"""

from __future__ import annotations

import unittest

import numpy as np

from personality_questionnaire.vasf import ANSWER_DIMS, VASF_QUESTIONNAIRE, vasf


class TestLegacyDelta(unittest.TestCase):
    """``vasf()`` keeps its published shape and values."""

    def test_delta_is_item_wise_post_minus_pre(self):
        np.testing.assert_array_equal(vasf([1] * 18, [4] * 18), np.full(18, 3))

    def test_accepts_a_two_dimensional_pre(self):
        self.assertEqual(vasf(np.full((1, 18), 2), [5] * 18).shape, (1, 18))

    def test_handles_a_negative_change(self):
        np.testing.assert_array_equal(vasf([8] * 18, [3] * 18), np.full(18, -5))

    def test_returns_integers(self):
        self.assertTrue(np.issubdtype(vasf([1] * 18, [4] * 18).dtype, np.integer))


class TestLegacyTables(unittest.TestCase):
    """The published item and anchor tables are intact."""

    def test_item_table(self):
        self.assertEqual(len(VASF_QUESTIONNAIRE), 18)
        self.assertEqual(VASF_QUESTIONNAIRE[1], "tired")
        self.assertEqual(VASF_QUESTIONNAIRE[18], "desire to lie down")

    def test_anchor_table(self):
        self.assertEqual(len(ANSWER_DIMS), 18)
        self.assertEqual(ANSWER_DIMS[1], ("not at all", "extremely"))
        self.assertEqual(ANSWER_DIMS[13], ("is no effort at all", "is a tremendous chore"))
        self.assertEqual(ANSWER_DIMS[17], ("I have absolutely no", "I have a tremendous"))


if __name__ == "__main__":
    unittest.main()
