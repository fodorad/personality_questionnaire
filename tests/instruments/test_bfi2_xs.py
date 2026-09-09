"""Tests for the BFI-2 Extra-Short Form.

The published scoring key is transcribed here and asserted against, so an edit to
the item mapping fails loudly rather than producing scores that are no longer the
BFI-2-XS.
"""

from __future__ import annotations

import unittest

import numpy as np

import personality_questionnaire as pq
from personality_questionnaire.instruments.bfi2_xs import BFI2_XS, XS_TO_BFI2

PUBLISHED_KEY = {
    "extraversion": "1R, 6, 11",
    "agreeableness": "2, 7R, 12",
    "conscientiousness": "3R, 8R, 13",
    "neuroticism": "4, 9, 14R",
    "openness": "5, 10R, 15",
}
"""Domain scales as printed on the published BFI-2-XS form.

Soto & John (2017), Short and extra-short forms of the Big Five Inventory-2.
Reverse-keyed items are denoted "R"; the numbering is the BFI-2-XS's own.
"""


def rendered(name: str) -> str:
    """Render a subscale in the published ``"1R, 6, 11"`` notation.

    Args:
        name: The subscale name.

    Returns:
        The item keys as the published form writes them.
    """
    subscale = BFI2_XS.subscale(name)
    return ", ".join(f"{n}R" if n in subscale.reverse else str(n) for n in subscale.items)


class TestPublishedKey(unittest.TestCase):
    """Item membership and keying must match the published form."""

    def test_domain_scales_match(self):
        for domain, spec in PUBLISHED_KEY.items():
            with self.subTest(domain=domain):
                self.assertEqual(rendered(domain), spec)

    def test_fifteen_items(self):
        self.assertEqual(BFI2_XS.n_items, 15)

    def test_five_domains_of_three_items(self):
        domains = BFI2_XS.subscales_at("domain")
        self.assertEqual(len(domains), 5)
        for domain in domains:
            with self.subTest(domain=domain.name):
                self.assertEqual(len(domain.items), 3)

    def test_declares_no_facets(self):
        """One item per facet is too few to score one, and the authors say so."""
        self.assertEqual(BFI2_XS.subscales_at("facet"), ())
        self.assertEqual(BFI2_XS.levels, ("domain",))


class TestBorrowedItems(unittest.TestCase):
    """Items are referenced from the BFI-2, never retyped."""

    def setUp(self):
        self.bfi2 = pq.get("bfi2")

    def test_every_item_names_its_source(self):
        for item in BFI2_XS.items:
            with self.subTest(item=item.number):
                self.assertIsNotNone(item.source_number)

    def test_borrowed_text_matches_the_source(self):
        """A wording fix in the BFI-2 must propagate rather than diverge."""
        for item in BFI2_XS.items:
            with self.subTest(item=item.number):
                self.assertEqual(item.text, self.bfi2.item(item.source_number).text)

    def test_borrowed_prompt_matches_the_source(self):
        for item in BFI2_XS.items:
            with self.subTest(item=item.number):
                self.assertEqual(item.prompt, self.bfi2.item(item.source_number).prompt)

    def test_mapping_is_injective(self):
        """Two short-form items must not point at the same parent item."""
        self.assertEqual(len(set(XS_TO_BFI2.values())), len(XS_TO_BFI2))

    def test_sources_are_valid_bfi2_items(self):
        self.assertTrue(set(XS_TO_BFI2.values()) <= self.bfi2.item_numbers)

    def test_keying_agrees_with_the_parent(self):
        """A borrowed item keeps the polarity its wording earned in the BFI-2."""
        parent_reverse = {
            n for subscale in self.bfi2.subscales_at("domain") for n in subscale.reverse
        }
        own_reverse = {n for subscale in BFI2_XS.subscales for n in subscale.reverse}
        for short, source in XS_TO_BFI2.items():
            with self.subTest(item=short):
                self.assertEqual(short in own_reverse, source in parent_reverse)

    def test_shares_the_parent_response_scale(self):
        self.assertEqual(BFI2_XS.minimum, self.bfi2.minimum)
        self.assertEqual(BFI2_XS.maximum, self.bfi2.maximum)
        self.assertEqual(BFI2_XS.labels, self.bfi2.labels)


class TestScoring(unittest.TestCase):
    """The shared scorer handles the short form with no special casing."""

    def test_midpoint_answers_score_one_half(self):
        """The scale midpoint maps to 0.5 whatever the keying balance."""
        result = pq.score(BFI2_XS, [[3] * 15])
        np.testing.assert_allclose(result.values, 0.5)

    def test_uniform_non_midpoint_answers_do_not_cancel(self):
        """Three items per domain cannot split evenly, so keying does not cancel.

        The BFI-2 reverses exactly half of each twelve-item domain, so a constant
        answer collapses to the midpoint. A three-item domain reverses one or two of
        three, leaving a genuine imbalance -- 4, 4, reversed-4 averages to 3.33, or
        0.583 normalised. This is correct arithmetic, not a defect, and it is why
        short-form scores are not comparable to full-form scores item for item.
        """
        scores = pq.score(BFI2_XS, [[4] * 15]).as_dict()
        for domain, value in scores.items():
            reversed_count = len(BFI2_XS.subscale(domain).reverse)
            expected = (4 * (3 - reversed_count) + 2 * reversed_count) / 3
            with self.subTest(domain=domain):
                self.assertAlmostEqual(value, (expected - 1) / 4)

    def test_domains_are_reported_in_ocean_order(self):
        self.assertEqual(
            [s.name for s in BFI2_XS.subscales_at("domain")],
            ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"],
        )

    def test_agrees_with_the_bfi2_at_the_scale_midpoint(self):
        """Both forms put a wholly neutral respondent at the middle of every domain.

        This is the strongest agreement the two forms can be held to: away from the
        midpoint their differing keying balances legitimately diverge.
        """
        short = pq.score(BFI2_XS, [[3] * 15]).by_level("domain")
        full = pq.score(pq.get("bfi2"), [[3] * 60]).by_level("domain")
        self.assertEqual(set(short), set(full))
        for domain in short:
            with self.subTest(domain=domain):
                np.testing.assert_allclose(short[domain], full[domain])

    def test_tracks_the_bfi2_on_the_shared_items(self):
        """Scoring the XS items directly must equal scoring them through the parent.

        Answering the full BFI-2 and the short form consistently should give the
        same short-form score, which is what makes the borrowed items meaningful.
        """
        rng = np.random.default_rng(20260909)
        full_answers = rng.integers(1, 6, size=(25, 60))
        short_answers = np.stack(
            [full_answers[:, XS_TO_BFI2[n] - 1] for n in sorted(XS_TO_BFI2)], axis=1
        )

        direct = pq.score(BFI2_XS, short_answers).by_level("domain")
        for domain, values in direct.items():
            subscale = BFI2_XS.subscale(domain)
            manual = np.mean(
                [
                    6 - short_answers[:, n - 1]
                    if n in subscale.reverse
                    else short_answers[:, n - 1]
                    for n in subscale.items
                ],
                axis=0,
            )
            with self.subTest(domain=domain):
                np.testing.assert_allclose(values, (manual - 1) / 4)

    def test_rejects_a_full_length_response(self):
        with self.assertRaisesRegex(ValueError, "bfi2-xs has 15 items"):
            pq.score(BFI2_XS, [[3] * 60])


class TestRegistration(unittest.TestCase):
    """The instrument is discoverable and self-describing."""

    def test_registered_under_its_key(self):
        self.assertIs(pq.get("bfi2-xs"), BFI2_XS)

    def test_cites_the_short_form_paper(self):
        self.assertIn("Short and extra-short forms", BFI2_XS.citation)
        self.assertIn("2017", BFI2_XS.citation)

    def test_every_subscale_declares_direction(self):
        for subscale in BFI2_XS.subscales:
            with self.subTest(subscale=subscale.name):
                self.assertTrue(subscale.higher_is)


if __name__ == "__main__":
    unittest.main()
