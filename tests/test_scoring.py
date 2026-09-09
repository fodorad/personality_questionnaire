"""Tests for the shared vectorised scorer."""

from __future__ import annotations

import unittest

import numpy as np

from personality_questionnaire import registry, scoring
from tests.fixtures import constant_answers


def naive_subscale_means(questionnaire, answers: np.ndarray) -> np.ndarray:
    """Score by an explicit per-participant, per-subscale loop.

    The obvious implementation, kept only as an oracle: the vectorised scorer must
    agree with it on random data, which is what makes the matmul trustworthy. It
    honours each subscale's declared aggregation, so a summed scale is summed here
    too rather than silently averaged.

    Args:
        questionnaire: The instrument to score.
        answers: Raw responses of shape ``(n_participants, n_items)``.

    Returns:
        Subscale scores of shape ``(n_participants, n_subscales)``.
    """
    low, high = questionnaire.minimum, questionnaire.maximum
    out = np.zeros((answers.shape[0], len(questionnaire.subscales)))
    for row in range(answers.shape[0]):
        for column, subscale in enumerate(questionnaire.subscales):
            total = 0.0
            for number in subscale.items:
                value = answers[row, number - 1]
                total += (low + high - value) if number in subscale.reverse else value
            summed = subscale.aggregation is registry.Aggregation.SUM
            out[row, column] = total if summed else total / len(subscale.items)
    return out


class TestReverse(unittest.TestCase):
    """Reverse-keying reflects a response about the scale midpoint."""

    def test_reflects_on_one_to_five(self):
        values = np.array([1, 2, 3, 4, 5])
        np.testing.assert_array_equal(scoring.reverse(values, 1, 5), [5, 4, 3, 2, 1])

    def test_reflects_on_zero_to_ten(self):
        values = np.array([0, 5, 10])
        np.testing.assert_array_equal(scoring.reverse(values, 0, 10), [10, 5, 0])

    def test_is_an_involution(self):
        values = np.array([1, 2, 3, 4, 5])
        np.testing.assert_array_equal(scoring.reverse(scoring.reverse(values, 1, 5), 1, 5), values)


class TestVectorisation(unittest.TestCase):
    """The vectorised path must equal the naive loop."""

    def test_matches_naive_loop_on_random_cohorts(self):
        rng = np.random.default_rng(20260908)
        for key in registry.keys():
            questionnaire = registry.get(key)
            with self.subTest(instrument=key):
                answers = rng.integers(
                    questionnaire.minimum,
                    questionnaire.maximum + 1,
                    size=(40, questionnaire.n_items),
                )
                result = scoring.score(questionnaire, answers, normalize=False)
                np.testing.assert_allclose(
                    result.values, naive_subscale_means(questionnaire, answers)
                )

    def test_empty_reverse_mask_is_a_no_op(self):
        vasf = registry.get("vasf")
        fatigue_only = registry.Questionnaire(
            key="no-reverse",
            name="No Reverse",
            abbreviation="NR",
            scale=vasf.scale,
            minimum=0,
            maximum=10,
            items=vasf.items,
            subscales=(registry.Subscale(name="All", items=tuple(range(1, 19))),),
            citation="None.",
        )
        answers = constant_answers(18, 7)
        np.testing.assert_array_equal(scoring.keyed_matrix(fatigue_only, answers), answers)


class TestScore(unittest.TestCase):
    """End-to-end scoring behaviour."""

    def test_promotes_a_single_participant(self):
        result = scoring.score(registry.get("bfi2"), [3] * 60)
        self.assertEqual(result.n_participants, 1)

    def test_normalisation_bounds(self):
        """A uniformly-keyed subscale reaches 0 and 1 at the ends of the scale.

        Only a subscale with no reverse keys can: on a mixed-key scale, answering
        every item ``1`` sends the forward items to 0 and the reverse-keyed ones to
        1, which averages to the middle. VAS-F Fatigue is the uniformly-keyed case.
        """
        vasf = registry.get("vasf")
        low = scoring.score(vasf, constant_answers(18, 0)).as_dict()
        high = scoring.score(vasf, constant_answers(18, 10)).as_dict()
        self.assertAlmostEqual(low["Fatigue"], 0.0)
        self.assertAlmostEqual(high["Fatigue"], 1.0)

    def test_mixed_key_subscale_centres_on_a_uniform_response(self):
        """Answering every BFI-2 item identically lands each domain at the midpoint.

        Each domain reverse-keys exactly half its twelve items, so the forward and
        reversed halves cancel whatever the response was.
        """
        for response in (1, 3, 5):
            with self.subTest(response=response):
                result = scoring.score(registry.get("bfi2"), constant_answers(60, response))
                np.testing.assert_allclose(list(result.by_level("domain").values()), 0.5)

    def test_midpoint_scores_one_half(self):
        result = scoring.score(registry.get("bfi2"), constant_answers(60, 3))
        np.testing.assert_allclose(result.values, 0.5)

    def test_unnormalised_stays_on_the_response_scale(self):
        result = scoring.score(registry.get("bfi2"), constant_answers(60, 4), normalize=False)
        self.assertGreaterEqual(result.values.min(), 1.0)
        self.assertLessEqual(result.values.max(), 5.0)

    def test_rejects_wrong_item_count(self):
        with self.assertRaisesRegex(ValueError, "bfi2 has 60 items"):
            scoring.score(registry.get("bfi2"), [[3] * 18])

    def test_rejects_out_of_range_response(self):
        answers = constant_answers(60, 3)
        answers[0, 0] = 9
        with self.assertRaisesRegex(ValueError, r"\[1\.\.5\]"):
            scoring.score(registry.get("bfi2"), answers)

    def test_rejects_ragged_input(self):
        with self.assertRaises(ValueError):
            scoring.score(registry.get("bfi2"), [[1, 2], [1, 2, 3]])

    def test_by_level_selects_the_right_columns(self):
        result = scoring.score(registry.get("bfi2"), constant_answers(60, 3))
        self.assertEqual(len(result.by_level("domain")), 5)
        self.assertEqual(len(result.by_level("facet")), 15)

    def test_to_records_covers_every_participant(self):
        result = scoring.score(registry.get("bfi2"), constant_answers(60, 3, n_participants=3))
        records = result.to_records()
        self.assertEqual(len(records), 3)
        self.assertIn("openness", records[0])


class TestAggregation(unittest.TestCase):
    """A subscale declares how it combines its items."""

    def setUp(self):
        self.panas = registry.get("panas")

    def test_sum_is_the_mean_times_the_item_count(self):
        rng = np.random.default_rng(7)
        answers = rng.integers(1, 6, size=(15, 20))
        result = scoring.score(self.panas, answers, normalize=False)
        by_name = dict(zip(result.names, result.values.T, strict=True))
        np.testing.assert_allclose(
            by_name["Positive Affect (sum)"], by_name["Positive Affect"] * 10
        )

    def test_sum_subscales_are_never_normalised(self):
        """Rescaling a published total would destroy the number it is stated in."""
        normalised = scoring.score(self.panas, constant_answers(20, 5))
        by_name = dict(zip(normalised.names, normalised.values.T, strict=True))
        self.assertAlmostEqual(float(by_name["Positive Affect"][0]), 1.0)
        self.assertAlmostEqual(float(by_name["Positive Affect (sum)"][0]), 50.0)

    def test_mean_remains_the_default(self):
        for key in ("bfi2", "bfi2-xs", "bfi10", "vasf"):
            instrument = registry.get(key)
            for subscale in instrument.subscales:
                with self.subTest(instrument=key, subscale=subscale.name):
                    self.assertIs(subscale.aggregation, registry.Aggregation.MEAN)

    def test_naive_loop_agrees_for_a_summed_scale(self):
        rng = np.random.default_rng(11)
        answers = rng.integers(1, 6, size=(10, 20))
        result = scoring.score(self.panas, answers, normalize=False)
        by_name = dict(zip(result.names, result.values.T, strict=True))
        expected = answers[:, [n - 1 for n in self.panas.subscale("Negative Affect").items]].sum(
            axis=1
        )
        np.testing.assert_allclose(by_name["Negative Affect (sum)"], expected)


class TestDelta(unittest.TestCase):
    """Paired scoring for pre/post instruments."""

    def test_item_delta_is_post_minus_pre(self):
        vasf = registry.get("vasf")
        paired = scoring.delta(vasf, constant_answers(18, 2), constant_answers(18, 7))
        np.testing.assert_array_equal(paired.item_delta, np.full((1, 18), 5))

    def test_subscale_delta_is_zero_when_unchanged(self):
        vasf = registry.get("vasf")
        answers = constant_answers(18, 4)
        paired = scoring.delta(vasf, answers, answers)
        np.testing.assert_allclose(paired.subscale_delta, 0.0)

    def test_rejects_mismatched_cohorts(self):
        vasf = registry.get("vasf")
        with self.assertRaisesRegex(ValueError, "same participants"):
            scoring.delta(vasf, constant_answers(18, 3, 2), constant_answers(18, 3, 3))


if __name__ == "__main__":
    unittest.main()
