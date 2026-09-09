"""Tests for the ``records`` and ``export`` commands."""

from __future__ import annotations

import contextlib
import csv
import io as stdio
import json
import tempfile
import unittest
from pathlib import Path

import personality_questionnaire as pq
from personality_questionnaire.cli.main import EXIT_MISSING_INPUT, EXIT_OK, main
from personality_questionnaire.db import Record, Repository, create_engine_from_env


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    """Invoke the CLI and capture both streams."""
    out, err = stdio.StringIO(), stdio.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class CommandTestCase(unittest.TestCase):
    """Base with a temporary file-backed database holding two records.

    A file rather than ``sqlite://`` because each CLI invocation opens its own
    engine, and an in-memory database would not survive between them.
    """

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.url = f"sqlite:///{Path(self._dir.name) / 'records.db'}"

        repo = Repository(create_engine_from_env(self.url))
        self.addCleanup(repo.close)
        for code, key, experiment in (
            ("P01", "bfi10", "study-a"),
            ("P02", "panas", None),
        ):
            repo.save(
                Record(
                    participant_code=code,
                    questionnaire=key,
                    responses={n: 3 for n in range(1, pq.get(key).n_items + 1)},
                    experiment=experiment,
                )
            )


class TestRecords(CommandTestCase):
    """``pq records`` lists what is stored."""

    def test_lists_every_record(self):
        code, out, _ = run_cli(["records", "--db", self.url])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("P01", out)
        self.assertIn("P02", out)

    def test_filters_by_participant(self):
        _, out, _ = run_cli(["records", "--db", self.url, "--participant", "P01"])
        self.assertIn("P01", out)
        self.assertNotIn("P02", out)

    def test_filters_by_instrument(self):
        _, out, _ = run_cli(["records", "--db", self.url, "--questionnaire", "panas"])
        self.assertIn("panas", out)
        self.assertNotIn("bfi10", out)

    def test_reports_an_empty_store(self):
        with tempfile.TemporaryDirectory() as directory:
            url = f"sqlite:///{Path(directory) / 'empty.db'}"
            _, out, _ = run_cli(["records", "--db", url])
            self.assertIn("No records stored", out)


class TestExport(CommandTestCase):
    """``pq export`` renders records in each shape."""

    def test_long_shape_reaches_stdout(self):
        code, out, _ = run_cli(["export", "--db", self.url, "--shape", "long"])
        self.assertEqual(code, EXIT_OK)
        rows = list(csv.DictReader(stdio.StringIO(out)))
        self.assertTrue(rows)

    def test_wide_shape_needs_one_instrument(self):
        code, _, err = run_cli(["export", "--db", self.url, "--shape", "wide"])
        self.assertEqual(code, 2)
        self.assertIn("one instrument at a time", err)

    def test_wide_shape_works_when_filtered(self):
        code, out, _ = run_cli(
            ["export", "--db", self.url, "--shape", "wide", "--questionnaire", "bfi10"]
        )
        self.assertEqual(code, EXIT_OK)
        self.assertIn("item_1", out)

    def test_json_shape_is_parseable(self):
        code, out, _ = run_cli(["export", "--db", self.url, "--shape", "json"])
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(len(json.loads(out)), 2)

    def test_writes_to_a_file_when_asked(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "out.csv"
            code, out, _ = run_cli(
                ["export", "--db", self.url, "--shape", "long", "--output", str(target)]
            )
            self.assertEqual(code, EXIT_OK)
            self.assertTrue(target.exists())
            self.assertIn("Wrote 2 record(s)", out)

    def test_reports_an_empty_selection(self):
        code, _, err = run_cli(["export", "--db", self.url, "--participant", "nobody"])
        self.assertEqual(code, EXIT_MISSING_INPUT)
        self.assertIn("no complete records", err)

    def test_output_stays_pipeable(self):
        """Diagnostics must not contaminate the exported CSV on stdout."""
        _, out, _ = run_cli(["--verbose", "export", "--db", self.url, "--shape", "long"])
        rows = list(csv.DictReader(stdio.StringIO(out)))
        self.assertTrue(all(row["kind"] in {"response", "score"} for row in rows))


class TestRunPersistence(unittest.TestCase):
    """``pq run`` stores what it collects unless told otherwise."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.url = f"sqlite:///{Path(self._dir.name) / 'records.db'}"

    def _administer(self, extra: list[str]) -> tuple[int, str]:
        from personality_questionnaire.cli.main import build_parser

        answers = iter(["3"] * 10)
        args = build_parser().parse_args(
            ["run", "bfi10", "--participant", "P09", "--db", self.url, *extra]
        )
        args.read = lambda _: next(answers)
        args.write = lambda _: None
        out = stdio.StringIO()
        with contextlib.redirect_stdout(out):
            code = int(args.func(args))
        return code, out.getvalue()

    def test_saves_by_default(self):
        code, out = self._administer([])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Saved record", out)

        _, listing, _ = run_cli(["records", "--db", self.url])
        self.assertIn("P09", listing)

    def test_no_save_stores_nothing(self):
        code, out = self._administer(["--no-save"])
        self.assertEqual(code, EXIT_OK)
        self.assertNotIn("Saved record", out)

        _, listing, _ = run_cli(["records", "--db", self.url])
        self.assertIn("No records stored", listing)


if __name__ == "__main__":
    unittest.main()
