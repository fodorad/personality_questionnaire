"""Tests for application state.

This is where the interface's logic lives -- progress, completeness, gating, the
conversion to a storable record. The page modules are excluded from coverage
precisely because these decisions were extracted here, so this module carries the
weight of testing them.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import personality_questionnaire as pq
from personality_questionnaire.core import recent_databases
from personality_questionnaire.core.state import AppState, DraftRecord
from personality_questionnaire.db import Record


def complete(draft: DraftRecord, value: int = 3) -> DraftRecord:
    """Answer every item of the draft's instrument.

    Args:
        draft: The draft to fill in.
        value: The response to give to each item.

    Returns:
        The same draft.
    """
    for number in range(1, draft.n_items + 1):
        draft.answer(number, value)
    return draft


class TestReadiness(unittest.TestCase):
    """Setup gating: what must be present before answering can begin."""

    def test_an_empty_draft_is_not_ready(self):
        self.assertFalse(DraftRecord().ready)

    def test_a_participant_alone_is_not_ready(self):
        self.assertFalse(DraftRecord(participant_code="P01").ready)

    def test_an_instrument_alone_is_not_ready(self):
        self.assertFalse(DraftRecord(questionnaire_key="bfi10").ready)

    def test_both_together_are_ready(self):
        self.assertTrue(DraftRecord(participant_code="P01", questionnaire_key="bfi10").ready)

    def test_whitespace_is_not_a_participant_code(self):
        self.assertFalse(DraftRecord(participant_code="   ", questionnaire_key="bfi10").ready)


class TestProgress(unittest.TestCase):
    """Progress reporting drives the bar and the counter."""

    def setUp(self):
        self.draft = DraftRecord(participant_code="P01", questionnaire_key="bfi10")

    def test_starts_empty(self):
        self.assertEqual(self.draft.answered, 0)
        self.assertEqual(self.draft.progress, 0.0)
        self.assertFalse(self.draft.complete)

    def test_counts_answers(self):
        self.draft.answer(1, 3)
        self.draft.answer(2, 4)
        self.assertEqual(self.draft.answered, 2)
        self.assertAlmostEqual(self.draft.progress, 0.2)

    def test_reports_what_is_missing(self):
        self.draft.answer(1, 3)
        self.assertEqual(self.draft.missing, tuple(range(2, 11)))

    def test_complete_when_every_item_is_answered(self):
        complete(self.draft)
        self.assertTrue(self.draft.complete)
        self.assertEqual(self.draft.missing, ())
        self.assertEqual(self.draft.progress, 1.0)

    def test_answering_twice_does_not_double_count(self):
        self.draft.answer(1, 3)
        self.draft.answer(1, 5)
        self.assertEqual(self.draft.answered, 1)
        self.assertEqual(self.draft.responses[1], 5)

    def test_progress_without_an_instrument_is_zero(self):
        """Guards a division by zero on the setup tab before anything is chosen."""
        empty = DraftRecord()
        self.assertEqual(empty.n_items, 0)
        self.assertEqual(empty.progress, 0.0)
        self.assertFalse(empty.complete)


class TestAnswerValidation(unittest.TestCase):
    """A draft refuses answers the instrument would not accept."""

    def setUp(self):
        self.draft = DraftRecord(participant_code="P01", questionnaire_key="bfi10")

    def test_requires_an_instrument(self):
        with self.assertRaisesRegex(ValueError, "choose an instrument"):
            DraftRecord().answer(1, 3)

    def test_rejects_an_unknown_item(self):
        with self.assertRaisesRegex(ValueError, "no item 99"):
            self.draft.answer(99, 3)

    def test_rejects_a_response_outside_the_range(self):
        for value in (0, 6):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, r"\[1\.\.5\]"):
                self.draft.answer(1, value)

    def test_accepts_the_range_endpoints(self):
        self.draft.answer(1, 1)
        self.draft.answer(2, 5)
        self.assertEqual(self.draft.answered, 2)

    def test_a_zero_based_instrument_accepts_zero(self):
        vas = DraftRecord(participant_code="P01", questionnaire_key="vasf")
        vas.answer(1, 0)
        self.assertEqual(vas.responses[1], 0)

    def test_the_first_answer_starts_the_clock(self):
        self.assertIsNone(self.draft.started_at)
        self.draft.answer(1, 3)
        self.assertIsNotNone(self.draft.started_at)
        self.assertLess((datetime.now(UTC) - self.draft.started_at).total_seconds(), 60)


class TestScoring(unittest.TestCase):
    """A complete draft scores through the shared scorer."""

    def test_scores_a_complete_draft(self):
        draft = complete(DraftRecord(participant_code="P01", questionnaire_key="bfi10"))
        self.assertAlmostEqual(draft.score().as_dict()["openness"], 0.5)

    def test_refuses_an_incomplete_draft(self):
        draft = DraftRecord(participant_code="P01", questionnaire_key="bfi10")
        draft.answer(1, 3)
        with self.assertRaisesRegex(ValueError, "not finished"):
            draft.score()

    def test_matches_scoring_the_answers_directly(self):
        draft = complete(DraftRecord(participant_code="P01", questionnaire_key="panas"), 4)
        direct = pq.score(pq.get("panas"), [[4] * 20]).as_dict()
        self.assertEqual(draft.score().as_dict(), direct)


class TestToRecord(unittest.TestCase):
    """Conversion to the storable form."""

    def setUp(self):
        self.draft = complete(
            DraftRecord(
                participant_code="  P01  ",
                participant_label=" pilot ",
                experiment=" study-a ",
                tag=" pre ",
                questionnaire_key="bfi10",
            )
        )

    def test_refuses_an_incomplete_draft(self):
        with self.assertRaisesRegex(ValueError, "not finished"):
            DraftRecord(participant_code="P01", questionnaire_key="bfi10").to_record()

    def test_trims_operator_typed_fields(self):
        record = self.draft.to_record()
        self.assertEqual(record.participant_code, "P01")
        self.assertEqual(record.participant_label, "pilot")
        self.assertEqual(record.experiment, "study-a")
        self.assertEqual(record.tag, "pre")

    def test_marks_the_source_as_the_interface(self):
        self.assertEqual(self.draft.to_record().source, "ui")

    def test_carries_the_responses(self):
        self.assertEqual(self.draft.to_record().responses, self.draft.responses)

    def test_stamps_completion(self):
        self.assertIsNotNone(self.draft.to_record().completed_at)

    def test_empty_optional_fields_become_none(self):
        draft = complete(DraftRecord(participant_code="P01", questionnaire_key="bfi10"))
        record = draft.to_record()
        self.assertIsNone(record.experiment)
        self.assertIsNone(record.participant_label)

    def test_notes_are_carried_only_when_present(self):
        self.assertEqual(self.draft.to_record().extra, {})
        self.draft.notes = "second attempt"
        self.assertEqual(self.draft.to_record().extra, {"notes": "second attempt"})


class TestReset(unittest.TestCase):
    """Clearing between participants."""

    def setUp(self):
        self.draft = complete(
            DraftRecord(participant_code="P01", experiment="study-a", questionnaire_key="bfi10")
        )

    def test_clear_responses_keeps_the_setup(self):
        self.draft.clear_responses()
        self.assertEqual(self.draft.answered, 0)
        self.assertIsNone(self.draft.started_at)
        self.assertEqual(self.draft.participant_code, "P01")
        self.assertEqual(self.draft.questionnaire_key, "bfi10")

    def test_reset_clears_everything(self):
        self.draft.reset()
        self.assertFalse(self.draft.ready)
        self.assertEqual(self.draft.answered, 0)
        self.assertEqual(self.draft.participant_code, "")
        self.assertIsNone(self.draft.questionnaire_key)

    def test_reset_clears_read_only_state(self):
        self.draft.read_only = True
        self.draft.loaded_session_id = 7
        self.draft.reset()
        self.assertFalse(self.draft.read_only)
        self.assertIsNone(self.draft.loaded_session_id)


def saved_record(**overrides) -> Record:
    """Build a plausible saved (has a session_id) record for load_from tests.

    Args:
        **overrides: Fields to replace.

    Returns:
        The constructed record.
    """
    fields = {
        "participant_code": "P07",
        "questionnaire": "panas",
        "responses": {n: 5 for n in range(1, 21)},
        "tag": "pre",
        "experiment": "study-a",
        "participant_label": "pilot",
        "extra": {"notes": "second attempt"},
        "session_id": 42,
    }
    fields.update(overrides)
    return Record(**fields)


class TestLoadFrom(unittest.TestCase):
    """Hydrating a draft from a stored record, for viewing or editing."""

    def test_populates_every_field(self):
        draft = DraftRecord()
        draft.load_from(saved_record())
        self.assertEqual(draft.participant_code, "P07")
        self.assertEqual(draft.participant_label, "pilot")
        self.assertEqual(draft.experiment, "study-a")
        self.assertEqual(draft.tag, "pre")
        self.assertEqual(draft.questionnaire_key, "panas")
        self.assertEqual(draft.responses, {n: 5 for n in range(1, 21)})
        self.assertEqual(draft.notes, "second attempt")

    def test_defaults_to_read_only(self):
        draft = DraftRecord()
        draft.load_from(saved_record())
        self.assertTrue(draft.read_only)

    def test_can_be_loaded_editable(self):
        draft = DraftRecord()
        draft.load_from(saved_record(), read_only=False)
        self.assertFalse(draft.read_only)

    def test_remembers_the_session_id(self):
        draft = DraftRecord()
        draft.load_from(saved_record(session_id=99))
        self.assertEqual(draft.loaded_session_id, 99)

    def test_missing_optional_fields_become_empty_strings(self):
        draft = DraftRecord()
        draft.load_from(saved_record(experiment=None, participant_label=None, extra={}))
        self.assertEqual(draft.experiment, "")
        self.assertEqual(draft.participant_label, "")
        self.assertEqual(draft.notes, "")

    def test_refuses_an_unsaved_record(self):
        with self.assertRaisesRegex(ValueError, "has not been saved"):
            DraftRecord().load_from(saved_record(session_id=None))

    def test_a_loaded_draft_is_complete_and_scoreable(self):
        draft = DraftRecord()
        draft.load_from(saved_record())
        self.assertTrue(draft.complete)
        self.assertAlmostEqual(draft.score().as_dict()["Positive Affect"], 1.0)


class TestUnlock(unittest.TestCase):
    """Moving a loaded draft from viewing to editing."""

    def test_unlock_clears_read_only(self):
        draft = DraftRecord()
        draft.load_from(saved_record())
        self.assertTrue(draft.read_only)
        draft.unlock()
        self.assertFalse(draft.read_only)

    def test_read_only_blocks_answer(self):
        draft = DraftRecord()
        draft.load_from(saved_record())
        with self.assertRaisesRegex(ValueError, "read-only"):
            draft.answer(1, 3)

    def test_unlocked_draft_accepts_answers(self):
        draft = DraftRecord()
        draft.load_from(saved_record())
        draft.unlock()
        draft.answer(1, 3)
        self.assertEqual(draft.responses[1], 3)

    def test_unlock_keeps_loaded_session_id(self):
        draft = DraftRecord()
        draft.load_from(saved_record(session_id=11))
        draft.unlock()
        self.assertEqual(draft.loaded_session_id, 11)


class TestAppState(unittest.TestCase):
    """The shared record store."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        url = f"sqlite:///{Path(self._dir.name) / 'records.db'}"
        self.state = AppState(database_url=url)
        self.addCleanup(self.state.close)

    def test_starts_empty(self):
        self.assertEqual(self.state.records(), [])

    def test_saving_makes_a_record_visible(self):
        draft = complete(DraftRecord(participant_code="P01", questionnaire_key="bfi10"))
        saved = self.state.save(draft.to_record())
        self.assertIsNotNone(saved.session_id)
        self.assertEqual(len(self.state.records()), 1)

    def test_sees_writes_from_another_connection(self):
        """The database is shared: the CLI and other machines write to it too.

        A cached listing would show an operator "no records yet" while the database
        held several, which is how this was found.
        """
        draft = complete(DraftRecord(participant_code="P02", questionnaire_key="bfi10"))
        self.state.records()  # prime any cache
        other = AppState(database_url=self.state.database_url)
        self.addCleanup(other.close)
        other.save(draft.to_record())

        self.assertEqual(len(self.state.records()), 1)

    def test_deleting_removes_a_record(self):
        draft = complete(DraftRecord(participant_code="P01", questionnaire_key="bfi10"))
        saved = self.state.save(draft.to_record())
        self.assertTrue(self.state.delete(saved.session_id))
        self.assertEqual(self.state.records(), [])

    def test_deleting_an_unknown_record_reports_failure(self):
        self.assertFalse(self.state.delete(9999))

    def test_close_is_repeatable(self):
        self.state.records()
        self.state.close()
        self.state.close()

    def test_update_overwrites_a_record_in_place(self):
        draft = complete(DraftRecord(participant_code="P01", questionnaire_key="bfi10"))
        saved = self.state.save(draft.to_record())

        edited = complete(DraftRecord(participant_code="P01", questionnaire_key="bfi10"), value=5)
        updated = self.state.update(saved.session_id, edited.to_record())

        self.assertEqual(updated.session_id, saved.session_id)
        self.assertEqual(len(self.state.records()), 1)


class TestSetDatabase(unittest.TestCase):
    """Switching the active database at runtime."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.state = AppState()
        self.addCleanup(self.state.close)

    def _url(self, name: str) -> str:
        """Build a database URL under the test's temp directory."""
        return f"sqlite:///{Path(self._dir.name) / name}"

    def test_switches_the_active_url(self):
        url = self._url("a.db")
        self.state.set_database(url)
        self.assertEqual(self.state.database_url, url)

    def test_records_are_isolated_per_database(self):
        self.state.set_database(self._url("a.db"))
        draft = complete(DraftRecord(participant_code="P01", questionnaire_key="bfi10"))
        self.state.save(draft.to_record())
        self.assertEqual(len(self.state.records()), 1)

        self.state.set_database(self._url("b.db"))
        self.assertEqual(len(self.state.records()), 0)

    def test_opens_the_new_database_eagerly(self):
        """A bad path must fail here, not on some unrelated later call."""
        self.state.set_database(self._url("eager.db"))
        self.assertTrue((Path(self._dir.name) / "eager.db").parent.exists())

    def test_remembers_the_switch(self):
        """set_database() records the switch at the real MRU path.

        core.dbpath.default_database_path() (and therefore
        recent_databases_path()) follows $PQ_HOME, so this test redirects that
        rather than patching -- the same technique tests/core/test_config.py
        already uses for environment-driven settings.
        """
        home = os.environ.get("PQ_HOME")
        os.environ["PQ_HOME"] = self._dir.name
        try:
            url = self._url("remembered.db")
            self.state.set_database(url)
            self.assertIn(url, recent_databases.load_recent())
        finally:
            if home is None:
                os.environ.pop("PQ_HOME", None)
            else:
                os.environ["PQ_HOME"] = home


if __name__ == "__main__":
    unittest.main()
