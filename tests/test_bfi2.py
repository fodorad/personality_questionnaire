"""Tests for the BFI-2, including the pre-2.0 compatibility surface."""

from __future__ import annotations

import unittest
import warnings

import numpy as np

from personality_questionnaire import get, scoring
from personality_questionnaire.bfi2 import (
    _R,
    ANSWER,
    BFI2_QUESTIONNAIRE,
    DOMAIN_SCALES,
    FACET_SCALES,
    bfi2,
    bfi2_trait,
    flip_trait_dimension,
)
from tests.fixtures import PUBLISHED_OCEAN, bfi2_answers, constant_answers

NEUROTICISM_FACET_COLUMNS = slice(9, 12)
"""Columns of Anxiety, Depression and Emotional Volatility in the FACET array."""

NEUROTICISM_DOMAIN_COLUMN = 4
"""Column of neuroticism in the OCEAN array."""


class TestPublishedValues(unittest.TestCase):
    """The numbers this package has returned since 1.0.0 must not drift."""

    def setUp(self):
        self.answers = bfi2_answers()

    def test_ocean_matches_published_values(self):
        result = bfi2(self.answers)
        np.testing.assert_allclose(np.round(result["OCEAN"], 3), PUBLISHED_OCEAN)

    def test_shapes(self):
        result = bfi2(self.answers)
        self.assertEqual(result["OCEAN"].shape, (2, 5))
        self.assertEqual(result["FACET"].shape, (2, 15))

    def test_scale_key_notation_is_preserved(self):
        self.assertEqual(DOMAIN_SCALES["openness"][:3], ["5R", "10", "15"])
        self.assertEqual(FACET_SCALES["Sociability"], ["1", "16R", "31R", "46"])

    def test_questionnaire_and_answer_tables(self):
        self.assertEqual(len(BFI2_QUESTIONNAIRE), 60)
        self.assertEqual(ANSWER["Disagree strongly"], 1)
        self.assertEqual(ANSWER["Agree strongly"], 5)

    def test_bfi2_trait_matches_the_domain_column(self):
        trait = bfi2_trait(self.answers, DOMAIN_SCALES["openness"])
        np.testing.assert_allclose(trait, bfi2(self.answers)["OCEAN"][:, 0])


# Transcribed verbatim from the published scoring key: Soto, C. J., & John, O. P.
# (2017), Big Five Inventory-2, APA PsycTESTS, doi:10.1037/t64008-000. False-keyed
# items are denoted "R". The key gives item membership only -- it prescribes no
# transformation after averaging, which is the basis for the 2.0 polarity fix.
OFFICIAL_DOMAIN_SCALES = {
    "extraversion": "1, 6, 11R, 16R, 21, 26R, 31R, 36R, 41, 46, 51R, 56",
    "agreeableness": "2, 7, 12R, 17R, 22R, 27, 32, 37R, 42R, 47R, 52, 57",
    "conscientiousness": "3R, 8R, 13, 18, 23R, 28R, 33, 38, 43, 48R, 53, 58R",
    "neuroticism": "4R, 9R, 14, 19, 24R, 29R, 34, 39, 44R, 49R, 54, 59",
    "openness": "5R, 10, 15, 20, 25R, 30R, 35, 40, 45R, 50R, 55R, 60",
}

OFFICIAL_FACET_SCALES = {
    "Sociability": "1, 16R, 31R, 46",
    "Assertiveness": "6, 21, 36R, 51R",
    "Energy Level": "11R, 26R, 41, 56",
    "Compassion": "2, 17R, 32, 47R",
    "Respectfulness": "7, 22R, 37R, 52",
    "Trust": "12R, 27, 42R, 57",
    "Organization": "3R, 18, 33, 48R",
    "Productiveness": "8R, 23R, 38, 53",
    "Responsibility": "13, 28R, 43, 58R",
    "Anxiety": "4R, 19, 34, 49R",
    "Depression": "9R, 24R, 39, 54",
    "Emotional Volatility": "14, 29R, 44R, 59",
    "Intellectual Curiosity": "10, 25R, 40, 55R",
    "Aesthetic Sensitivity": "5R, 20, 35, 50R",
    "Creative Imagination": "15, 30R, 45R, 60",
}


class TestAgainstPublishedScoringKey(unittest.TestCase):
    """Item membership must match Soto & John (2017) exactly.

    These scales are not ours to choose. Pinning them against the published key
    means a well-meaning edit to an item list fails here rather than silently
    producing scores that are no longer the BFI-2.
    """

    @staticmethod
    def _parse(spec: str) -> list[str]:
        """Split a published scale specification into item keys.

        Args:
            spec: The key as printed, e.g. ``"4R, 19, 34, 49R"``.

        Returns:
            The item keys.
        """
        return [token.strip() for token in spec.split(",")]

    def test_domain_scales_match_the_published_key(self):
        for name, spec in OFFICIAL_DOMAIN_SCALES.items():
            with self.subTest(domain=name):
                self.assertEqual(DOMAIN_SCALES[name], self._parse(spec))

    def test_facet_scales_match_the_published_key(self):
        for name, spec in OFFICIAL_FACET_SCALES.items():
            with self.subTest(facet=name):
                self.assertEqual(FACET_SCALES[name], self._parse(spec))

    def test_every_published_scale_is_present(self):
        self.assertEqual(set(DOMAIN_SCALES), set(OFFICIAL_DOMAIN_SCALES))
        self.assertEqual(set(FACET_SCALES), set(OFFICIAL_FACET_SCALES))


class TestNeuroticismPolarity(unittest.TestCase):
    """Domain and facet polarity must agree -- the bug fixed in 2.0."""

    def setUp(self):
        self.answers = bfi2_answers()

    def test_facets_agree_with_their_domain(self):
        result = bfi2(self.answers)
        np.testing.assert_allclose(
            result["FACET"][:, NEUROTICISM_FACET_COLUMNS].mean(axis=1),
            result["OCEAN"][:, NEUROTICISM_DOMAIN_COLUMN],
        )

    def test_flip_moves_both_levels_together(self):
        result = bfi2(self.answers, flip_neuroticism=True)
        np.testing.assert_allclose(
            result["FACET"][:, NEUROTICISM_FACET_COLUMNS].mean(axis=1),
            result["OCEAN"][:, NEUROTICISM_DOMAIN_COLUMN],
        )

    def test_flip_complements_the_unflipped_domain(self):
        plain = bfi2(self.answers)["OCEAN"][:, NEUROTICISM_DOMAIN_COLUMN]
        flipped = bfi2(self.answers, flip_neuroticism=True)["OCEAN"][:, NEUROTICISM_DOMAIN_COLUMN]
        np.testing.assert_allclose(flipped, 1 - plain)

    def test_legacy_switch_reproduces_pre_2_0_facets(self):
        plain = bfi2(self.answers)["OCEAN"][:, NEUROTICISM_DOMAIN_COLUMN]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            legacy = bfi2(self.answers, legacy_facet_polarity=True)
        np.testing.assert_allclose(
            legacy["FACET"][:, NEUROTICISM_FACET_COLUMNS].mean(axis=1), 1 - plain
        )

    def test_legacy_switch_warns(self):
        with self.assertWarns(DeprecationWarning):
            bfi2(self.answers, legacy_facet_polarity=True)

    def test_polarity_is_recorded_as_data(self):
        neuroticism = get("bfi2").subscale("neuroticism")
        self.assertEqual(neuroticism.higher_is, "more neurotic")
        self.assertEqual(get("bfi2").subscale("Anxiety").higher_is, "more anxious")


class TestHelpers(unittest.TestCase):
    """The small published helpers keep their contracts."""

    def test_reverse_endpoints_and_midpoint(self):
        self.assertEqual(_R(1), 5)
        self.assertEqual(_R(5), 1)
        self.assertEqual(_R(3), 3)

    def test_reverse_rejects_out_of_range(self):
        for value in (0, 6):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _R(value)

    def test_flip_trait_dimension(self):
        np.testing.assert_allclose(flip_trait_dimension(np.array([0.0, 0.3, 1.0])), [1.0, 0.7, 0.0])

    def test_flip_rejects_two_dimensional_input(self):
        with self.assertRaisesRegex(ValueError, r"\(N,\)"):
            flip_trait_dimension(np.zeros((2, 2)))

    def test_flip_rejects_unscaled_input(self):
        with self.assertRaisesRegex(ValueError, r"\[0\.\.1\]"):
            flip_trait_dimension(np.array([0.0, 4.0]))

    def test_bfi2_trait_rejects_wrong_width(self):
        with self.assertRaises(ValueError):
            bfi2_trait(constant_answers(18, 3), DOMAIN_SCALES["openness"])


class TestRegistryEquivalence(unittest.TestCase):
    """The shim and the registry must agree."""

    def test_domain_scores_match_the_registry(self):
        answers = bfi2_answers()
        legacy = bfi2(answers)["OCEAN"]
        modern = scoring.score(get("bfi2"), answers).by_level("domain")
        for index, name in enumerate(s.name for s in get("bfi2").subscales_at("domain")):
            with self.subTest(domain=name):
                np.testing.assert_allclose(legacy[:, index], modern[name])


if __name__ == "__main__":
    unittest.main()
