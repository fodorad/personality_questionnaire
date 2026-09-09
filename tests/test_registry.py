"""Tests for the instrument registry and its validation."""

from __future__ import annotations

import unittest

from personality_questionnaire import registry
from personality_questionnaire.registry import Item, Questionnaire, ScaleType, Subscale


def make_item(number: int) -> Item:
    """Build a throwaway item.

    Args:
        number: The item number.

    Returns:
        An item suitable for a synthetic instrument.
    """
    return Item(
        number=number,
        text=f"item {number}",
        prompt=f"item {number}?",
        low_anchor="low",
        high_anchor="high",
    )


def make_questionnaire(**overrides) -> Questionnaire:
    """Build a valid two-item instrument, with overrides applied.

    Args:
        **overrides: Fields to replace.

    Returns:
        The constructed instrument.
    """
    base = {
        "key": "synthetic",
        "name": "Synthetic",
        "scale": ScaleType.LIKERT,
        "minimum": 1,
        "maximum": 5,
        "items": (make_item(1), make_item(2)),
        "subscales": (Subscale(name="Total", items=(1, 2)),),
        "citation": "None.",
        "labels": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
    }
    base.update(overrides)
    return Questionnaire(**base)


class TestRegisteredInstruments(unittest.TestCase):
    """Every shipped instrument must be internally consistent."""

    def test_registry_is_populated(self):
        self.assertEqual(set(registry.keys()), {"bfi2", "bfi2-xs", "bfi10", "vasf"})

    def test_every_big_five_form_reports_the_same_domains(self):
        """The three Big Five forms must be interchangeable at the domain level.

        Downstream code selects a form by key and reads its domains; a form that
        named or ordered them differently would silently misalign the columns.
        """
        expected = [
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
        ]
        for key in ("bfi2", "bfi2-xs", "bfi10"):
            with self.subTest(instrument=key):
                names = [s.name for s in registry.get(key).subscales_at("domain")]
                self.assertEqual(names, expected)

    def test_borrowed_items_reference_a_real_source(self):
        """Any item claiming a source must actually match it."""
        for key in registry.keys():
            instrument = registry.get(key)
            for item in instrument.items:
                if item.source_number is None:
                    continue
                with self.subTest(instrument=key, item=item.number):
                    parents = [
                        registry.get(other)
                        for other in registry.keys()
                        if other != key
                        and item.source_number in registry.get(other).item_numbers
                        and registry.get(other).item(item.source_number).text == item.text
                    ]
                    self.assertTrue(parents, "source_number matches no parent instrument")

    def test_every_instrument_validates(self):
        for key in registry.keys():
            with self.subTest(instrument=key):
                registry.get(key).validate()

    def test_every_item_belongs_to_a_subscale(self):
        for key in registry.keys():
            instrument = registry.get(key)
            covered = {n for s in instrument.subscales for n in s.items}
            with self.subTest(instrument=key):
                self.assertEqual(covered, instrument.item_numbers)

    def test_bfi2_shape(self):
        bfi2 = registry.get("bfi2")
        self.assertEqual(bfi2.n_items, 60)
        self.assertEqual(len(bfi2.subscales_at("domain")), 5)
        self.assertEqual(len(bfi2.subscales_at("facet")), 15)

    def test_bfi2_domain_order_is_ocean(self):
        names = [s.name for s in registry.get("bfi2").subscales_at("domain")]
        self.assertEqual(
            names,
            ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"],
        )

    def test_vasf_shape(self):
        vasf = registry.get("vasf")
        self.assertEqual(vasf.n_items, 18)
        self.assertTrue(vasf.paired)
        self.assertEqual(vasf.minimum, 0)
        self.assertEqual(vasf.maximum, 10)

    def test_vasf_prompts_embed_anchors(self):
        vasf = registry.get("vasf")
        self.assertEqual(
            vasf.item(1).prompt, '0 means "not at all tired", 10 means "extremely tired"'
        )
        self.assertIn("keeping my eyes open is no effort at all", vasf.item(13).prompt)

    def test_no_prompt_carries_the_legacy_typo(self):
        for key in registry.keys():
            for item in registry.get(key).items:
                with self.subTest(instrument=key, item=item.number):
                    self.assertNotIn("while and", item.prompt)

    def test_get_reports_available_keys(self):
        with self.assertRaises(KeyError) as caught:
            registry.get("nope")
        self.assertIn("bfi2", str(caught.exception))

    def test_items_are_immutable(self):
        with self.assertRaises(Exception):
            registry.get("bfi2").items[0].text = "changed"


class TestValidation(unittest.TestCase):
    """Malformed instruments must be rejected at construction."""

    def test_rejects_unknown_item_reference(self):
        bad = make_questionnaire(subscales=(Subscale(name="Total", items=(1, 99)),))
        with self.assertRaisesRegex(ValueError, "unknown items"):
            bad.validate()

    def test_rejects_orphan_reverse_key(self):
        bad = make_questionnaire(
            subscales=(Subscale(name="Total", items=(1, 2), reverse=frozenset({99})),)
        )
        with self.assertRaisesRegex(ValueError, "reverse-keys"):
            bad.validate()

    def test_rejects_unreachable_item(self):
        bad = make_questionnaire(subscales=(Subscale(name="Partial", items=(1,)),))
        with self.assertRaisesRegex(ValueError, "belong to no subscale"):
            bad.validate()

    def test_rejects_misnumbered_items(self):
        bad = make_questionnaire(items=(make_item(1), make_item(3)))
        with self.assertRaisesRegex(ValueError, "numbered 1..2"):
            bad.validate()

    def test_rejects_duplicate_subscale_names(self):
        bad = make_questionnaire(
            subscales=(Subscale(name="Total", items=(1,)), Subscale(name="Total", items=(2,)))
        )
        with self.assertRaisesRegex(ValueError, "duplicate subscale"):
            bad.validate()

    def test_rejects_missing_parent(self):
        bad = make_questionnaire(subscales=(Subscale(name="Total", items=(1, 2), parent="ghost"),))
        with self.assertRaisesRegex(ValueError, "missing parent"):
            bad.validate()

    def test_rejects_empty_range(self):
        bad = make_questionnaire(minimum=5, maximum=5)
        with self.assertRaisesRegex(ValueError, "range is empty"):
            bad.validate()

    def test_rejects_likert_without_labels(self):
        bad = make_questionnaire(labels={})
        with self.assertRaisesRegex(ValueError, "response labels"):
            bad.validate()

    def test_rejects_duplicate_registration(self):
        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(make_questionnaire(key="bfi2"))


if __name__ == "__main__":
    unittest.main()
