"""Tests for the BFI-2 instrument definition.

The legacy ``personality_questionnaire.bfi2`` shim is covered by
``tests/test_bfi2.py``; this module checks the instrument data itself.
"""

from __future__ import annotations

import unittest

from personality_questionnaire import get
from personality_questionnaire.instruments.bfi2 import (
    BFI2,
    BFI2_ITEM_TEXT,
    BFI2_LABELS,
)


class TestItems(unittest.TestCase):
    """The item pool matches the published instrument."""

    def test_sixty_items(self):
        self.assertEqual(BFI2.n_items, 60)
        self.assertEqual(len(BFI2_ITEM_TEXT), 60)

    def test_items_are_numbered_in_order(self):
        self.assertEqual([item.number for item in BFI2.items], list(range(1, 61)))

    def test_prompts_carry_the_shared_stem(self):
        for item in BFI2.items:
            with self.subTest(item=item.number):
                self.assertTrue(item.prompt.startswith("I am someone who..."))
                self.assertIn(item.text, item.prompt)

    def test_items_are_native_not_borrowed(self):
        self.assertTrue(all(item.source_number is None for item in BFI2.items))

    def test_first_and_last_item_text(self):
        self.assertEqual(BFI2.item(1).text, "Is outgoing, sociable.")
        self.assertEqual(BFI2.item(60).text, "Is original, comes up with new ideas.")


class TestResponseScale(unittest.TestCase):
    """The 1-5 agreement scale and its labels."""

    def test_range(self):
        self.assertEqual((BFI2.minimum, BFI2.maximum), (1, 5))

    def test_labels_cover_the_range(self):
        self.assertEqual(sorted(BFI2_LABELS.values()), [1, 2, 3, 4, 5])

    def test_label_endpoints(self):
        self.assertEqual(BFI2_LABELS["Disagree strongly"], 1)
        self.assertEqual(BFI2_LABELS["Agree strongly"], 5)


class TestStructure(unittest.TestCase):
    """Five domains, fifteen facets, every facet parented to a domain."""

    def test_counts(self):
        self.assertEqual(len(BFI2.subscales_at("domain")), 5)
        self.assertEqual(len(BFI2.subscales_at("facet")), 15)

    def test_domains_have_twelve_items_each(self):
        for domain in BFI2.subscales_at("domain"):
            with self.subTest(domain=domain.name):
                self.assertEqual(len(domain.items), 12)

    def test_facets_have_four_items_each(self):
        for facet in BFI2.subscales_at("facet"):
            with self.subTest(facet=facet.name):
                self.assertEqual(len(facet.items), 4)

    def test_every_facet_names_a_real_domain(self):
        domains = {d.name for d in BFI2.subscales_at("domain")}
        for facet in BFI2.subscales_at("facet"):
            with self.subTest(facet=facet.name):
                self.assertIn(facet.parent, domains)

    def test_each_domain_is_covered_by_exactly_three_facets(self):
        for domain in BFI2.subscales_at("domain"):
            facets = [f for f in BFI2.subscales_at("facet") if f.parent == domain.name]
            with self.subTest(domain=domain.name):
                self.assertEqual(len(facets), 3)
                covered = {n for f in facets for n in f.items}
                self.assertEqual(covered, set(domain.items))

    def test_every_subscale_declares_its_direction(self):
        for subscale in BFI2.subscales:
            with self.subTest(subscale=subscale.name):
                self.assertTrue(subscale.higher_is)

    def test_registered_under_its_key(self):
        self.assertIs(get("bfi2"), BFI2)


class TestMetadata(unittest.TestCase):
    """Provenance a researcher needs before using the instrument."""

    def test_cites_the_source_publication(self):
        self.assertIn("Soto", BFI2.citation)
        self.assertIn("2017", BFI2.citation)

    def test_records_the_licence_note(self):
        self.assertIn("research", BFI2.license_note)


if __name__ == "__main__":
    unittest.main()
