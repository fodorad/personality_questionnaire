"""Tests for the pure form-description logic behind the demo."""

from __future__ import annotations

import unittest

import personality_questionnaire as pq
from demo import form


class TestFieldSpecs(unittest.TestCase):
    """Describing one form field per item."""

    def test_one_spec_per_item(self):
        bfi10 = pq.get("bfi10")
        specs = form.field_specs(bfi10)
        self.assertEqual(len(specs), bfi10.n_items)

    def test_likert_instrument_yields_radio_fields(self):
        bfi10 = pq.get("bfi10")
        specs = form.field_specs(bfi10)
        self.assertTrue(all(spec.kind == "radio" for spec in specs))

    def test_radio_choices_match_the_instrument_labels(self):
        bfi10 = pq.get("bfi10")
        specs = form.field_specs(bfi10)
        self.assertEqual(dict(specs[0].choices), bfi10.labels)

    def test_visual_analogue_instrument_yields_slider_fields(self):
        vasf = pq.get("vasf")
        specs = form.field_specs(vasf)
        self.assertTrue(all(spec.kind == "slider" for spec in specs))

    def test_slider_fields_carry_no_choices(self):
        vasf = pq.get("vasf")
        specs = form.field_specs(vasf)
        self.assertEqual(specs[0].choices, ())

    def test_slider_range_matches_the_instrument(self):
        vasf = pq.get("vasf")
        specs = form.field_specs(vasf)
        self.assertEqual((specs[0].minimum, specs[0].maximum), (vasf.minimum, vasf.maximum))

    def test_fields_are_in_administration_order(self):
        bfi2 = pq.get("bfi2")
        specs = form.field_specs(bfi2)
        self.assertEqual([spec.item.number for spec in specs], list(range(1, bfi2.n_items + 1)))

    def test_every_instrument_fits_within_max_items(self):
        for key in pq.keys():
            with self.subTest(instrument=key):
                self.assertLessEqual(pq.get(key).n_items, form.MAX_ITEMS)


class TestMissingItems(unittest.TestCase):
    """Reporting what has not been answered yet."""

    def test_empty_responses_reports_every_item(self):
        bfi10 = pq.get("bfi10")
        missing = form.missing_items(bfi10, {})
        self.assertEqual(missing, tuple(range(1, bfi10.n_items + 1)))

    def test_complete_responses_reports_nothing(self):
        bfi10 = pq.get("bfi10")
        responses = {n: 3 for n in range(1, bfi10.n_items + 1)}
        self.assertEqual(form.missing_items(bfi10, responses), ())

    def test_reports_only_the_gaps_in_order(self):
        bfi10 = pq.get("bfi10")
        responses = {n: 3 for n in range(1, bfi10.n_items + 1) if n not in (2, 7)}
        self.assertEqual(form.missing_items(bfi10, responses), (2, 7))


if __name__ == "__main__":
    unittest.main()
