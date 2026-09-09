"""Tests for the pure filesystem helpers behind the database picker."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from personality_questionnaire.core import dbpath


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


class TestScanDatabases(unittest.TestCase):
    """Listing a directory's subdirectories and database files."""

    def test_lists_database_files_by_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.db").touch()
            (root / "b.sqlite").touch()
            (root / "c.sqlite3").touch()
            (root / "notes.txt").touch()

            _, files = dbpath.scan_databases(root)
            self.assertEqual([f.name for f in files], ["a.db", "b.sqlite", "c.sqlite3"])

    def test_lists_subdirectories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "study-a").mkdir()
            (root / "study-b").mkdir()
            (root / "x.db").touch()

            subdirs, _ = dbpath.scan_databases(root)
            self.assertEqual([d.name for d in subdirs], ["study-a", "study-b"])

    def test_sorts_case_insensitively(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Zebra.db").touch()
            (root / "apple.db").touch()

            _, files = dbpath.scan_databases(root)
            self.assertEqual([f.name for f in files], ["apple.db", "Zebra.db"])

    def test_unreadable_directory_returns_empty_rather_than_raising(self):
        subdirs, files = dbpath.scan_databases(Path("/nonexistent/does/not/exist"))
        self.assertEqual((subdirs, files), ([], []))

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(dbpath.scan_databases(Path(directory)), ([], []))


class TestParentOf(unittest.TestCase):
    """Walking up the directory tree."""

    def test_returns_the_parent(self):
        self.assertEqual(dbpath.parent_of(Path("/a/b/c")), Path("/a/b"))

    def test_root_has_no_parent(self):
        self.assertIsNone(dbpath.parent_of(Path("/")))


class TestResolveStartDir(EnvironmentTestCase):
    """Choosing where the picker opens."""

    def test_no_current_url_falls_back_to_the_default(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ["PQ_HOME"] = directory
            self.assertEqual(dbpath.resolve_start_dir(None), Path(directory))

    def test_uses_the_current_database_directory_when_it_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "records.db").touch()
            url = f"sqlite:///{Path(directory) / 'records.db'}"
            self.assertEqual(dbpath.resolve_start_dir(url), Path(directory))

    def test_falls_back_when_the_current_directory_is_gone(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ["PQ_HOME"] = directory
            url = "sqlite:////nonexistent/gone/records.db"
            self.assertEqual(dbpath.resolve_start_dir(url), Path(directory))

    def test_in_memory_url_falls_back_to_the_default(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ["PQ_HOME"] = directory
            self.assertEqual(dbpath.resolve_start_dir("sqlite:///:memory:"), Path(directory))


class TestIsValidSqliteUrl(unittest.TestCase):
    """What the picker and the setup-page path field will accept."""

    def test_accepts_a_creatable_path(self):
        with tempfile.TemporaryDirectory() as directory:
            url = f"sqlite:///{Path(directory) / 'new.db'}"
            self.assertTrue(dbpath.is_valid_sqlite_url(url))

    def test_accepts_an_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing.db"
            target.touch()
            self.assertTrue(dbpath.is_valid_sqlite_url(f"sqlite:///{target}"))

    def test_rejects_a_directory_that_does_not_exist(self):
        self.assertFalse(dbpath.is_valid_sqlite_url("sqlite:////nonexistent/gone/x.db"))

    def test_rejects_a_non_sqlite_scheme(self):
        self.assertFalse(dbpath.is_valid_sqlite_url("mysql+pymysql://user@host/db"))

    def test_accepts_in_memory(self):
        self.assertTrue(dbpath.is_valid_sqlite_url("sqlite:///:memory:"))


if __name__ == "__main__":
    unittest.main()
