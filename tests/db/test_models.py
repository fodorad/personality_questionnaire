"""Tests for the record schema.

Constraints and cascades are asserted here rather than assumed: a foreign key that
silently does nothing is the kind of defect that only surfaces as orphaned rows
months later.
"""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from personality_questionnaire.db import (
    Participant,
    Response,
    Score,
    Session,
    create_engine_from_env,
    init_db,
    session_scope,
)


class DatabaseTestCase(unittest.TestCase):
    """Base for tests needing an empty in-memory database."""

    def setUp(self):
        self.engine = create_engine_from_env("sqlite://")
        init_db(self.engine)
        self.addCleanup(self.engine.dispose)

    def _participant(self, session, code: str = "P01") -> Participant:
        """Add and flush a participant."""
        participant = Participant(code=code)
        session.add(participant)
        session.flush()
        return participant

    def _session_row(self, session, participant: Participant, **overrides) -> Session:
        """Add and flush a session row."""
        fields = {
            "participant_id": participant.id,
            "questionnaire": "bfi10",
            "started_at": datetime.now(UTC),
        }
        fields.update(overrides)
        row = Session(**fields)
        session.add(row)
        session.flush()
        return row


class TestSchema(DatabaseTestCase):
    """The tables exist and carry the expected columns."""

    def test_creates_every_table(self):
        from personality_questionnaire.db.models import Base

        self.assertEqual(set(Base.metadata.tables), {"participant", "session", "response", "score"})

    def test_init_db_is_idempotent(self):
        init_db(self.engine)
        init_db(self.engine)

    def test_participant_code_is_unique(self):
        with self.assertRaises(IntegrityError), session_scope(self.engine) as session:
            session.add(Participant(code="P01"))
            session.add(Participant(code="P01"))

    def test_session_records_provenance(self):
        with session_scope(self.engine) as session:
            participant = self._participant(session)
            row = self._session_row(
                session, participant, package_version="2.2.0", git_sha="a" * 40, git_dirty=True
            )
            self.assertEqual(row.package_version, "2.2.0")
            self.assertTrue(row.git_dirty)


class TestConstraints(DatabaseTestCase):
    """Uniqueness rules protect against double-recording."""

    def test_one_response_per_item_per_session(self):
        with self.assertRaises(IntegrityError), session_scope(self.engine) as session:
            participant = self._participant(session)
            row = self._session_row(session, participant)
            session.add(Response(session_id=row.id, item_number=1, value=3))
            session.add(Response(session_id=row.id, item_number=1, value=4))

    def test_one_score_per_subscale_per_normalisation(self):
        with self.assertRaises(IntegrityError), session_scope(self.engine) as session:
            participant = self._participant(session)
            row = self._session_row(session, participant)
            session.add(Score(session_id=row.id, subscale="openness", value=0.5, normalized=True))
            session.add(Score(session_id=row.id, subscale="openness", value=0.6, normalized=True))

    def test_a_subscale_may_be_stored_both_normalised_and_raw(self):
        """The PANAS reports a mean and a published total for the same scale."""
        with session_scope(self.engine) as session:
            participant = self._participant(session)
            row = self._session_row(session, participant, questionnaire="panas")
            session.add(
                Score(session_id=row.id, subscale="Positive Affect", value=0.5, normalized=True)
            )
            session.add(
                Score(session_id=row.id, subscale="Positive Affect", value=30.0, normalized=False)
            )

        with session_scope(self.engine) as session:
            self.assertEqual(len(session.scalars(select(Score)).all()), 2)

    def test_the_same_instrument_can_be_administered_twice_with_tags(self):
        """A paired instrument records a pre and a post session."""
        with session_scope(self.engine) as session:
            participant = self._participant(session)
            self._session_row(session, participant, questionnaire="vasf", tag="pre")
            self._session_row(session, participant, questionnaire="vasf", tag="post")

        with session_scope(self.engine) as session:
            self.assertEqual(len(session.scalars(select(Session)).all()), 2)


class TestCascades(DatabaseTestCase):
    """Deleting a parent must not leave orphans."""

    def test_deleting_a_session_removes_its_children(self):
        with session_scope(self.engine) as session:
            participant = self._participant(session)
            row = self._session_row(session, participant)
            session.add(Response(session_id=row.id, item_number=1, value=3))
            session.add(Score(session_id=row.id, subscale="openness", value=0.5))
            session_id = row.id

        with session_scope(self.engine) as session:
            session.delete(session.get(Session, session_id))

        with session_scope(self.engine) as session:
            self.assertEqual(session.scalars(select(Response)).all(), [])
            self.assertEqual(session.scalars(select(Score)).all(), [])

    def test_deleting_a_participant_removes_their_sessions(self):
        with session_scope(self.engine) as session:
            participant = self._participant(session)
            self._session_row(session, participant)
            participant_id = participant.id

        with session_scope(self.engine) as session:
            session.delete(session.get(Participant, participant_id))

        with session_scope(self.engine) as session:
            self.assertEqual(session.scalars(select(Session)).all(), [])

    def test_sqlite_foreign_keys_are_enforced(self):
        """SQLite ignores foreign keys unless the pragma is set per connection."""
        with session_scope(self.engine) as session:
            enabled = session.connection().exec_driver_sql("PRAGMA foreign_keys").scalar()
        self.assertEqual(enabled, 1)


if __name__ == "__main__":
    unittest.main()
