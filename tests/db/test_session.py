"""Tests for engine and session management."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from personality_questionnaire.db.session import (
    ENV_DATABASE_URL,
    ENV_HOME,
    create_engine_from_env,
    database_url,
    default_database_path,
    session_scope,
)


class EnvironmentTestCase(unittest.TestCase):
    """Base that restores the environment afterwards."""

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in (ENV_DATABASE_URL, ENV_HOME)}
        for key in self._saved:
            os.environ.pop(key, None)
        self.addCleanup(self._restore)

    def _restore(self):
        """Put the environment back."""
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class TestDatabaseUrl(EnvironmentTestCase):
    """Resolution order for the database location."""

    def test_defaults_to_a_sqlite_file(self):
        self.assertTrue(database_url().startswith("sqlite:///"))

    def test_environment_variable_wins(self):
        os.environ[ENV_DATABASE_URL] = "sqlite:///tmp/somewhere.db"
        self.assertEqual(database_url(), "sqlite:///tmp/somewhere.db")

    def test_home_override_moves_the_default(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ[ENV_HOME] = directory
            self.assertEqual(default_database_path().parent, Path(directory))

    def test_default_lives_under_a_dot_directory(self):
        self.assertEqual(default_database_path().name, "records.db")


class TestEngine(EnvironmentTestCase):
    """Engine construction."""

    def test_creates_the_parent_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "deeper" / "records.db"
            engine = create_engine_from_env(f"sqlite:///{target}")
            self.addCleanup(engine.dispose)
            self.assertTrue(target.parent.is_dir())

    def test_in_memory_needs_no_directory(self):
        engine = create_engine_from_env("sqlite://")
        self.addCleanup(engine.dispose)
        self.assertEqual(engine.dialect.name, "sqlite")

    def test_reads_the_environment_when_no_url_is_given(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ[ENV_DATABASE_URL] = f"sqlite:///{directory}/x.db"
            engine = create_engine_from_env()
            self.addCleanup(engine.dispose)
            self.assertIn(directory, str(engine.url))


class TestSessionScope(unittest.TestCase):
    """The transactional wrapper commits and rolls back."""

    def setUp(self):
        from personality_questionnaire.db import init_db

        self.engine = create_engine_from_env("sqlite://")
        init_db(self.engine)
        self.addCleanup(self.engine.dispose)

    def test_commits_on_success(self):
        from personality_questionnaire.db import Participant

        with session_scope(self.engine) as session:
            session.add(Participant(code="P01"))

        with session_scope(self.engine) as session:
            self.assertIsNotNone(session.query(Participant).filter_by(code="P01").one_or_none())

    def test_rolls_back_on_error(self):
        from personality_questionnaire.db import Participant

        with self.assertRaises(RuntimeError), session_scope(self.engine) as session:
            session.add(Participant(code="P02"))
            session.flush()
            raise RuntimeError("boom")

        with session_scope(self.engine) as session:
            self.assertIsNone(session.query(Participant).filter_by(code="P02").one_or_none())


if __name__ == "__main__":
    unittest.main()
