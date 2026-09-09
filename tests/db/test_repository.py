"""Tests for saving and retrieving records."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

import personality_questionnaire as pq
from personality_questionnaire.db import Record, Repository, create_engine_from_env


def answers_for(key: str, value: int = 3) -> dict[int, int]:
    """Build a complete response set for an instrument.

    Args:
        key: Registry key of the instrument.
        value: The response to repeat.

    Returns:
        Item number to response.
    """
    return {n: value for n in range(1, pq.get(key).n_items + 1)}


class RepositoryTestCase(unittest.TestCase):
    """Base providing an empty repository."""

    def setUp(self):
        self.engine = create_engine_from_env("sqlite://")
        self.repo = Repository(self.engine)
        self.addCleanup(self.repo.close)

    def save(self, code: str = "P01", key: str = "bfi10", **overrides) -> Record:
        """Save a complete record."""
        fields = {"participant_code": code, "questionnaire": key, "responses": answers_for(key)}
        fields.update(overrides)
        return self.repo.save(Record(**fields))


class TestRoundTrip(RepositoryTestCase):
    """A saved record comes back as it went in."""

    def test_save_returns_an_id(self):
        self.assertIsNotNone(self.save().session_id)

    def test_responses_survive(self):
        original = self.save(key="bfi2", responses=answers_for("bfi2", 4))
        self.assertEqual(self.repo.load(original.session_id).responses, original.responses)

    def test_metadata_survives(self):
        saved = self.save(tag="pre", experiment="fatigue-2026", participant_label="pilot")
        loaded = self.repo.load(saved.session_id)
        self.assertEqual(loaded.tag, "pre")
        self.assertEqual(loaded.experiment, "fatigue-2026")
        self.assertEqual(loaded.participant_label, "pilot")

    def test_timestamps_come_back_aware(self):
        """SQLite has no timezone type; a naive value would break comparisons."""
        loaded = self.repo.load(self.save().session_id)
        self.assertEqual(loaded.started_at.tzinfo, UTC)
        self.assertLess((datetime.now(UTC) - loaded.started_at).total_seconds(), 60)

    def test_extra_metadata_survives(self):
        saved = self.save(extra={"condition": "A", "block": 2})
        self.assertEqual(self.repo.load(saved.session_id).extra["condition"], "A")

    def test_loading_an_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            self.repo.load(9999)


class TestScores(RepositoryTestCase):
    """Scores are computed once, at save time, and stored."""

    def test_scores_are_stored(self):
        saved = self.save()
        stored = self.repo.scores(saved.session_id)
        self.assertEqual(set(stored), {s.name for s in pq.get("bfi10").subscales})

    def test_stored_scores_match_a_fresh_computation(self):
        saved = self.save(key="bfi2", responses=answers_for("bfi2", 4))
        stored = self.repo.scores(saved.session_id)
        fresh = pq.score(pq.get("bfi2"), [[4] * 60]).as_dict()
        for name, value in fresh.items():
            with self.subTest(subscale=name):
                self.assertAlmostEqual(stored[name], value)

    def test_published_totals_are_stored_unnormalised(self):
        """A PANAS total must keep the 10-50 scale its norms are stated in."""
        saved = self.save(key="panas", responses=answers_for("panas", 3))
        stored = self.repo.scores(saved.session_id)
        self.assertAlmostEqual(stored["Positive Affect"], 0.5)
        self.assertAlmostEqual(stored["Positive Affect (sum)"], 30.0)


class TestValidation(RepositoryTestCase):
    """Incomplete or unknown records are refused."""

    def test_refuses_an_incomplete_record(self):
        record = Record(participant_code="P01", questionnaire="bfi10", responses={1: 3})
        with self.assertRaisesRegex(ValueError, "missing items"):
            self.repo.save(record)

    def test_refuses_an_unknown_instrument(self):
        record = Record(participant_code="P01", questionnaire="nope", responses={1: 3})
        with self.assertRaises(KeyError):
            self.repo.save(record)


class TestListing(RepositoryTestCase):
    """Records can be found by participant, instrument and experiment."""

    def setUp(self):
        super().setUp()
        self.save("P01", "bfi10")
        self.save("P02", "bfi10", experiment="study-a")
        self.save("P02", "panas", responses=answers_for("panas"), experiment="study-a")

    def test_lists_everything(self):
        self.assertEqual(len(self.repo.list()), 3)

    def test_filters_by_participant(self):
        self.assertEqual(len(self.repo.list(participant="P02")), 2)

    def test_filters_by_instrument(self):
        self.assertEqual(len(self.repo.list(questionnaire="panas")), 1)

    def test_filters_by_experiment(self):
        self.assertEqual(len(self.repo.list(experiment="study-a")), 2)

    def test_reports_completeness(self):
        self.assertTrue(all(s.complete for s in self.repo.list()))

    def test_reuses_a_participant_across_sessions(self):
        self.assertEqual(self.repo.participants(), ["P01", "P02"])


class TestDeletion(RepositoryTestCase):
    """Deleting a record removes it and its children."""

    def test_delete_reports_success(self):
        saved = self.save()
        self.assertTrue(self.repo.delete(saved.session_id))
        self.assertEqual(self.repo.list(), [])

    def test_deleting_an_unknown_id_reports_failure(self):
        self.assertFalse(self.repo.delete(9999))

    def test_the_participant_survives_their_deleted_record(self):
        saved = self.save()
        self.repo.delete(saved.session_id)
        self.assertEqual(self.repo.participants(), ["P01"])


class TestResponsesFor(RepositoryTestCase):
    """The analysis-shaped read returns a rectangular matrix."""

    def test_returns_aligned_codes_and_answers(self):
        self.save("P01", "bfi10")
        self.save("P02", "bfi10", responses=answers_for("bfi10", 5))
        codes, answers = self.repo.responses_for("bfi10")
        self.assertEqual(codes, ["P01", "P02"])
        self.assertEqual([len(row) for row in answers], [10, 10])

    def test_ignores_other_instruments(self):
        self.save("P01", "bfi10")
        self.save("P02", "panas", responses=answers_for("panas"))
        codes, _ = self.repo.responses_for("bfi10")
        self.assertEqual(codes, ["P01"])

    def test_empty_when_nothing_matches(self):
        codes, answers = self.repo.responses_for("vasf")
        self.assertEqual((codes, answers), ([], []))


if __name__ == "__main__":
    unittest.main()
