"""Tests for the most-recently-used database list."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from personality_questionnaire.core import recent_databases


class EnvironmentTestCase(unittest.TestCase):
    """Base that restores $PQ_HOME afterwards."""

    def setUp(self):
        self._saved = os.environ.get("PQ_HOME")
        self.addCleanup(self._restore)

    def _restore(self):
        """Put $PQ_HOME back."""
        if self._saved is None:
            os.environ.pop("PQ_HOME", None)
        else:
            os.environ["PQ_HOME"] = self._saved


class TestRecentDatabasesPath(EnvironmentTestCase):
    """Where the MRU file lives."""

    def test_follows_pq_home(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ["PQ_HOME"] = directory
            self.assertEqual(
                recent_databases.recent_databases_path(),
                Path(directory) / "recent_databases.json",
            )


class TestLoadRecent(unittest.TestCase):
    """Reading back the remembered list."""

    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recent_databases.json"
            self.assertEqual(recent_databases.load_recent(path), [])

    def test_corrupt_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recent_databases.json"
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(recent_databases.load_recent(path), [])

    def test_non_list_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recent_databases.json"
            path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
            self.assertEqual(recent_databases.load_recent(path), [])

    def test_non_string_entries_are_dropped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recent_databases.json"
            path.write_text(json.dumps(["sqlite:///a.db", 7, None]), encoding="utf-8")
            self.assertEqual(recent_databases.load_recent(path), ["sqlite:///a.db"])

    def test_returns_entries_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recent_databases.json"
            urls = ["sqlite:///a.db", "sqlite:///b.db"]
            path.write_text(json.dumps(urls), encoding="utf-8")
            self.assertEqual(recent_databases.load_recent(path), urls)


class TestRememberDatabase(unittest.TestCase):
    """Updating the remembered list."""

    def test_inserts_a_new_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recent_databases.json"
            result = recent_databases.remember_database("sqlite:///a.db", path)
            self.assertEqual(result, ["sqlite:///a.db"])
            self.assertEqual(recent_databases.load_recent(path), ["sqlite:///a.db"])

    def test_re_promotes_a_duplicate_to_the_front(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recent_databases.json"
            recent_databases.remember_database("sqlite:///a.db", path)
            recent_databases.remember_database("sqlite:///b.db", path)
            result = recent_databases.remember_database("sqlite:///a.db", path)
            self.assertEqual(result, ["sqlite:///a.db", "sqlite:///b.db"])

    def test_caps_at_max_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recent_databases.json"
            for n in range(recent_databases.MAX_ENTRIES + 3):
                result = recent_databases.remember_database(f"sqlite:///{n}.db", path)
            self.assertEqual(len(result), recent_databases.MAX_ENTRIES)
            self.assertEqual(result[0], f"sqlite:///{recent_databases.MAX_ENTRIES + 2}.db")

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "recent_databases.json"
            recent_databases.remember_database("sqlite:///a.db", path)
            self.assertTrue(path.exists())

    def test_write_failure_is_swallowed(self):
        """A read-only filesystem must not block a database switch."""
        with tempfile.TemporaryDirectory() as directory:
            # A file where a directory is expected makes mkdir raise OSError.
            blocker = Path(directory) / "blocker"
            blocker.touch()
            path = blocker / "recent_databases.json"
            result = recent_databases.remember_database("sqlite:///a.db", path)
            self.assertEqual(result, ["sqlite:///a.db"])


if __name__ == "__main__":
    unittest.main()
