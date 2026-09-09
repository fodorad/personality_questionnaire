"""Tests for terminal formatting of scores and instrument metadata."""

from __future__ import annotations

import unittest

from personality_questionnaire import get, scoring
from personality_questionnaire.cli import render
from tests.fixtures import constant_answers


class TestFormatScores(unittest.TestCase):
    """Scores render grouped by level, with direction and scale stated."""

    def setUp(self):
        self.result = scoring.score(get("bfi2"), constant_answers(60, 3))
        self.lines = render.format_scores(self.result)

    def test_names_the_instrument(self):
        self.assertIn("Big Five Inventory-2", self.lines[0])

    def test_states_the_output_scale(self):
        self.assertIn("[0..1]", self.lines[0])

    def test_states_the_raw_scale_when_unnormalised(self):
        raw = scoring.score(get("bfi2"), constant_answers(60, 3), normalize=False)
        self.assertIn("[1..5]", render.format_scores(raw)[0])

    def test_groups_by_level(self):
        text = "\n".join(self.lines)
        self.assertIn("Domain", text)
        self.assertIn("Facet", text)

    def test_lists_every_subscale(self):
        text = "\n".join(self.lines)
        for subscale in get("bfi2").subscales:
            with self.subTest(subscale=subscale.name):
                self.assertIn(subscale.name, text)

    def test_reports_direction(self):
        self.assertIn("higher is more neurotic", "\n".join(self.lines))

    def test_honours_the_decimals_argument(self):
        lines = render.format_scores(self.result, decimals=1)
        self.assertIn("0.5", "\n".join(lines))

    def test_selects_the_requested_participant(self):
        pair = scoring.score(get("bfi2"), constant_answers(60, 5, n_participants=2))
        self.assertEqual(render.format_scores(pair, row=0), render.format_scores(pair, row=1))


class TestFormatInstrument(unittest.TestCase):
    """Instrument metadata renders completely."""

    def setUp(self):
        self.lines = render.format_instrument(get("vasf"))
        self.text = "\n".join(self.lines)

    def test_names_the_instrument_and_key(self):
        self.assertIn("Visual Analogue Scale", self.text)
        self.assertIn("vasf", self.text)

    def test_reports_item_count_and_scale(self):
        self.assertIn("18", self.text)
        self.assertIn("[0..10]", self.text)

    def test_marks_a_paired_instrument(self):
        self.assertIn("pre/post", self.text)

    def test_marks_an_unpaired_instrument(self):
        self.assertIn("no", "\n".join(render.format_instrument(get("bfi2"))))

    def test_lists_subscales_with_reverse_counts(self):
        self.assertIn("Fatigue (composite)", self.text)
        self.assertIn("reverse-keyed", self.text)

    def test_includes_the_citation(self):
        self.assertIn("Lee", self.text)

    def test_includes_a_licence_note_when_present(self):
        self.assertIn("Licence", "\n".join(render.format_instrument(get("bfi2"))))


class TestFormatRegistry(unittest.TestCase):
    """The instrument table."""

    def test_lists_every_instrument(self):
        lines = render.format_registry([get(key) for key in ("bfi2", "vasf")])
        text = "\n".join(lines)
        self.assertIn("bfi2", text)
        self.assertIn("vasf", text)

    def test_has_a_header_row(self):
        lines = render.format_registry([get("bfi2")])
        self.assertIn("KEY", lines[0])
        self.assertIn("ITEMS", lines[0])

    def test_handles_an_empty_registry(self):
        self.assertEqual(render.format_registry([]), ["No instruments registered."])


if __name__ == "__main__":
    unittest.main()
