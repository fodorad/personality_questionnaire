"""Tests for the ``analyze`` command."""

from __future__ import annotations

import contextlib
import io as stdio
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
    """Base with a temporary file-backed database."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.url = f"sqlite:///{Path(self._dir.name) / 'records.db'}"

    def save_bfi10_records(self, n: int, *, seed_offset: int = 0) -> None:
        """Save ``n`` BFI-10 records with varied, non-degenerate responses."""
        repo = Repository(create_engine_from_env(self.url))
        self.addCleanup(repo.close)
        n_items = pq.get("bfi10").n_items
        for i in range(n):
            responses = {
                number: ((number + i + seed_offset) % 5) + 1 for number in range(1, n_items + 1)
            }
            repo.save(
                Record(participant_code=f"P{i:02d}", questionnaire="bfi10", responses=responses)
            )


class TestAnalyzeReliability(CommandTestCase):
    """``pq analyze`` reports Cronbach's alpha by default."""

    def test_requires_at_least_two_records(self):
        self.save_bfi10_records(1)
        code, _, err = run_cli(["analyze", "bfi10", "--db", self.url])
        self.assertEqual(code, EXIT_MISSING_INPUT)
        self.assertIn("at least 2", err)

    def test_empty_store_is_reported(self):
        code, _, err = run_cli(["analyze", "bfi10", "--db", self.url])
        self.assertEqual(code, EXIT_MISSING_INPUT)
        self.assertIn("found 0", err)

    def test_reports_alpha_per_domain(self):
        self.save_bfi10_records(5)
        code, out, _ = run_cli(["analyze", "bfi10", "--db", self.url])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("openness", out)
        self.assertIn("alpha=", out)

    def test_corr_metric_also_reports_reliability(self):
        self.save_bfi10_records(5)
        code, out, _ = run_cli(["analyze", "bfi10", "--metric", "corr", "--db", self.url])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("weakest_item_corr=", out)

    def test_only_complete_records_count(self):
        """An incomplete record is refused at save time, so never reaches analysis."""
        repo = Repository(create_engine_from_env(self.url))
        self.addCleanup(repo.close)
        with self.assertRaises(ValueError):
            repo.save(Record(participant_code="P00", questionnaire="bfi10", responses={1: 3}))
        code, _, err = run_cli(["analyze", "bfi10", "--db", self.url])
        self.assertEqual(code, EXIT_MISSING_INPUT)
        self.assertIn("found 0", err)


class TestAnalyzeDescribe(CommandTestCase):
    """``pq analyze --metric describe`` reports score statistics."""

    def test_reports_mean_and_range(self):
        self.save_bfi10_records(5)
        code, out, _ = run_cli(["analyze", "bfi10", "--metric", "describe", "--db", self.url])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("mean=", out)
        self.assertIn("n=5", out)

    def test_rejects_an_unknown_instrument(self):
        """argparse's ``choices=`` refuses an unregistered key before dispatch."""
        with self.assertRaises(SystemExit):
            run_cli(["analyze", "nope", "--db", self.url])


if __name__ == "__main__":
    unittest.main()
