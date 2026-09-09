"""Tests for the Big Five Inventory-10.

Unlike the BFI-2-XS, the BFI-10 is not a subset of the BFI-2 -- its wording descends
from the BFI-44. These tests pin that distinction as well as the published key, so a
future refactor cannot quietly turn one form into the other.
"""

from __future__ import annotations

import unittest

import numpy as np

import personality_questionnaire as pq
from personality_questionnaire.instruments.bfi10 import BFI10, BFI10_ITEM_TEXT, BFI10_LABELS

PUBLISHED_KEY = {
    "extraversion": "1R, 6",
    "agreeableness": "2, 7R",
    "conscientiousness": "3R, 8",
    "neuroticism": "4R, 9",
    "openness": "5R, 10",
}
"""Scales as printed in Rammstedt & John (2007), Appendix A.

"Extraversion: 1R, 6; Agreeableness: 2, 7R; Conscientiousness: 3R, 8; Neuroticism:
4R, 9; Openness: 5R, 10 (R = item is reversed-scored)."
"""

PUBLISHED_ITEMS = {
    1: "is reserved",
    2: "is generally trusting",
    3: "tends to be lazy",
    4: "is relaxed, handles stress well",
    5: "has few artistic interests",
    6: "is outgoing, sociable",
    7: "tends to find fault with others",
    8: "does a thorough job",
    9: "gets nervous easily",
    10: "has an active imagination",
}
"""Item wording as printed in Appendix A, in administration order."""


def rendered(name: str) -> str:
    """Render a subscale in the published ``"1R, 6"`` notation.

    Args:
        name: The subscale name.

    Returns:
        The item keys as the paper writes them.
    """
    subscale = BFI10.subscale(name)
    return ", ".join(f"{n}R" if n in subscale.reverse else str(n) for n in subscale.items)


class TestPublishedKey(unittest.TestCase):
    """Membership, keying and wording must match the source publication."""

    def test_domain_scales_match(self):
        for domain, spec in PUBLISHED_KEY.items():
            with self.subTest(domain=domain):
                self.assertEqual(rendered(domain), spec)

    def test_item_text_matches(self):
        self.assertEqual(BFI10_ITEM_TEXT, PUBLISHED_ITEMS)

    def test_ten_items(self):
        self.assertEqual(BFI10.n_items, 10)

    def test_two_items_per_domain(self):
        for domain in BFI10.subscales_at("domain"):
            with self.subTest(domain=domain.name):
                self.assertEqual(len(domain.items), 2)

    def test_each_domain_pairs_one_keyed_each_way(self):
        """The design deliberately balances a positive and a negative item."""
        for domain in BFI10.subscales_at("domain"):
            with self.subTest(domain=domain.name):
                self.assertEqual(len(domain.reverse), 1)

    def test_exactly_five_items_are_reversed(self):
        reversed_items = {n for subscale in BFI10.subscales for n in subscale.reverse}
        self.assertEqual(reversed_items, {1, 3, 4, 5, 7})

    def test_declares_no_facets(self):
        self.assertEqual(BFI10.levels, ("domain",))


class TestDistinctFromBfi2(unittest.TestCase):
    """The BFI-10 descends from the BFI-44, not the BFI-2."""

    def test_items_are_native_not_borrowed(self):
        for item in BFI10.items:
            with self.subTest(item=item.number):
                self.assertIsNone(item.source_number)

    def test_wording_differs_from_the_bfi2(self):
        """Shared concepts are worded differently; none should match verbatim."""
        bfi2_text = {item.text for item in pq.get("bfi2").items}
        for item in BFI10.items:
            with self.subTest(item=item.number):
                self.assertNotIn(item.text, bfi2_text)

    def test_uses_its_own_stem(self):
        self.assertTrue(BFI10.item(1).prompt.startswith("I see myself as someone who..."))

    def test_uses_its_own_midpoint_label(self):
        """Published labels are reproduced per form, not harmonised across them."""
        self.assertIn("Neither agree nor disagree", BFI10_LABELS)
        self.assertNotIn("Neither agree nor disagree", pq.get("bfi2").labels)

    def test_shares_the_response_range(self):
        self.assertEqual((BFI10.minimum, BFI10.maximum), (1, 5))


class TestScoring(unittest.TestCase):
    """The shared scorer handles a two-item scale with no special casing."""

    def test_midpoint_answers_score_one_half(self):
        np.testing.assert_allclose(pq.score(BFI10, [[3] * 10]).values, 0.5)

    def test_balanced_keying_cancels_a_uniform_response(self):
        """One reversed of two items means any constant answer averages to the middle."""
        for response in (1, 2, 4, 5):
            with self.subTest(response=response):
                np.testing.assert_allclose(pq.score(BFI10, [[response] * 10]).values, 0.5)

    def test_domains_are_reported_in_ocean_order(self):
        self.assertEqual(
            [s.name for s in BFI10.subscales_at("domain")],
            ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"],
        )

    def test_scores_match_a_hand_computation(self):
        answers = np.array([[5, 4, 2, 1, 3, 5, 2, 4, 5, 4]])
        scores = pq.score(BFI10, answers).as_dict()
        # Extraversion: item 1 reversed (6-5=1), item 6 = 5 -> mean 3 -> 0.5
        self.assertAlmostEqual(scores["extraversion"], 0.5)
        # Neuroticism: item 4 reversed (6-1=5), item 9 = 5 -> mean 5 -> 1.0
        self.assertAlmostEqual(scores["neuroticism"], 1.0)

    def test_rejects_a_wrong_length_response(self):
        with self.assertRaisesRegex(ValueError, "bfi10 has 10 items"):
            pq.score(BFI10, [[3] * 15])


class TestRegistration(unittest.TestCase):
    """The instrument is discoverable and self-describing."""

    def test_registered_under_its_key(self):
        self.assertIs(pq.get("bfi10"), BFI10)

    def test_cites_rammstedt_and_john(self):
        self.assertIn("Rammstedt", BFI10.citation)
        self.assertIn("2007", BFI10.citation)

    def test_every_subscale_declares_direction(self):
        for subscale in BFI10.subscales:
            with self.subTest(subscale=subscale.name):
                self.assertTrue(subscale.higher_is)


if __name__ == "__main__":
    unittest.main()
